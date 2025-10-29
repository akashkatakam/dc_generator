import streamlit as st
import pandas as pd
import gspread 
from typing import Dict, Any, List, Tuple
from datetime import datetime

from config import initialize_app_data 
from finance_helper import calculate_finance_fees, generate_accessory_bills, get_next_dc_number, generate_accessory_invoice_number, HP_FEE_DEFAULT, HP_FEE_BANK_QUOTATION
from data_manager import save_record_to_sheet, GSPREAD_CLIENT
from order import SalesOrder

# --- GLOBAL DATA INITIALIZATION ---
SPREADSHEET_TITLE_FALLBACK = "Sales Records DB" 
SPREADSHEET_TITLE = st.secrets.get("spreadsheet_title")['spreadsheet_title']

# Execute Data Loading at the Global Scope (Cached)
results = initialize_app_data(SPREADSHEET_TITLE) 

# Unpack results for direct use in the UI function
vehicles, color_map, incentive_rules, firm_master_df, accessory_bom_df, sales_records_df, \
STAFF_LIST, EXECUTIVE_LIST, FINANCIER_LIST = results


# --- UI Application ---
def sales_app_ui():
    
    st.title("🚗 DC Generator / Vehicle Sales System")
    st.caption("Organized for efficient data entry.")
    
    # Check for fatal data loading error
    if not vehicles:
        st.error("Application setup failed. Data could not be loaded from Google Sheets.")
        return

    # Initialize variables
    financier_name = "N/A (Cash Sale)"
    executive_name = "N/A (Cash Sale)" 
    dd_amount = 0.0
    down_payment = 0.0
    hp_fee_to_charge = 0.0
    incentive_earned = 0.0
    banker_name = "" 
    
    # --- 1. CUSTOMER & STAFF CONTAINER ---
    with st.container(border=True):
        st.header("1. Customer Details")
        col_name, col_phone = st.columns(2)
        with col_name:
            name = st.text_input("Customer Name:")
        with col_phone:
            phone = st.text_input("Customer Phone Number:")
        
        place = st.text_input("Place/City:")
        sales_staff = st.selectbox("Sales Staff:", STAFF_LIST) 

    # --- 2. VEHICLE SELECTION & CONFIGURATION CONTAINER ---
    with st.container(border=True):
        st.header("2. Vehicle Configuration & Pricing")
        
        # 2.1 Model Selection
        all_models = sorted(list(set([v['model'].strip() for v in vehicles])))
        col_model, col_variant = st.columns(2)
        with col_model:
            selected_model = st.selectbox("Vehicle Model:", all_models)

        # Filter by Model for Variant/Trim
        available_variants = [v for v in vehicles if v['model'].strip() == selected_model]
        variant_options = [v['color'] for v in available_variants]
        with col_variant:
            selected_variant = st.selectbox("Variant/Trim Level:", variant_options)

        # 2.3 Paint Color Selection
        model_colors = color_map.get(selected_model, ["No Colors Available"])
        selected_paint_color = st.selectbox("Paint Color:", model_colors)

        # Find the Final Selected Vehicle Data (Price/Tax data is based on Model & Variant)
        selected_vehicle = next(
            (v for v in available_variants if v['color'] == selected_variant), 
            None
        )
        if selected_vehicle is None:
            st.error("Could not find price data for the selected combination.")
            listed_price = 0.0
        else:
            listed_price = selected_vehicle['total_price']
            st.markdown("---")
            st.info(f"Listed Price: **₹{listed_price:,.2f}**")

        # 2.4 Negotiation
        col_final_cost, col_discount_info = st.columns(2)
        with col_final_cost:
            final_cost_by_staff = st.number_input(
                "Final Vehicle Cost (after discount):", 
                min_value=0.0, 
                value=float(listed_price),
                step=100.0,
                format="%.2f"
            )
        
        discount_amount = listed_price - final_cost_by_staff
        with col_discount_info:
            if discount_amount > 0:
                st.success(f"Discount: **₹{discount_amount:,.2f}**")
            elif discount_amount < 0:
                st.warning(f"Markup: ₹{abs(discount_amount):,.2f}")
            else:
                st.markdown("Discount: **₹0.00**")
        st.markdown("---")


    # --- 3. PAYMENT & FINANCE CONTAINER ---
    with st.container(border=True):
        st.header("3. Payment & Financing")
        
        col_sale_type, col_filler = st.columns([1, 2])
        with col_sale_type:
            sale_type = st.radio("Sale Type:", ["Cash", "Finance"])

        if sale_type == "Finance":
            
            # --- Finance Configuration Expander ---
            with st.expander("Financing Source & Executive", expanded=True):
                
                # 4.1 Flags and Company Selection
                st.subheader("Financier Source")
                out_finance_flag = st.checkbox("Check if **Out Finance** (External):")
                
                col_comp_select, col_comp_new = st.columns([2, 1])

                with col_comp_select:
                    financier_name = st.selectbox(
                        "Financier Company:", 
                        FINANCIER_LIST
                    )

                with col_comp_new:
                    new_financier = st.text_input("New Co.")
                    if st.button("Add Company"):
                        if new_financier and new_financier not in FINANCIER_LIST:
                            st.error("Contact administrator to update list.")
                        elif new_financier:
                            st.info("Financier already in the list.")

                # 4.3 Conditional Banker Name Input
                if financier_name == 'Bank':
                    st.markdown("---")
                    banker_name = st.text_input("Banker's Name (for tracking quote):", key="banker_name_input")
                    st.markdown("---")

                # --- Finance Executive Selection and Management ---
                st.subheader("Finance Executive")
                executive_name = st.selectbox(
                    "Executive Name:",
                    EXECUTIVE_LIST
                )
                
                st.markdown("###### Add New Executive:")
                col_new_exec_input, col_new_exec_button = st.columns([3, 1])
                with col_new_exec_input:
                    new_executive = st.text_input("New Exec.", label_visibility="collapsed")
                with col_new_exec_button:
                    if st.button("Add Exec"):
                        if new_executive and new_executive not in EXECUTIVE_LIST:
                            st.error("Contact administrator to update list.")
                        elif new_executive:
                            st.info("Executive already in the list.")


                # --- Payment Input ---
                st.subheader("Payment Amounts")
                dd_amount = st.number_input("DD / Booking Amount:", min_value=0.0, step=100.0, format="%.2f", key="dd_input")
            
                
                # --- CRITICAL: Determine HP Fee and Incentive ---
                hp_fee_to_charge, incentive_earned = calculate_finance_fees(
                    financier_name, 
                    dd_amount, 
                    out_finance_flag, 
                    incentive_rules
                )
                
                
                # 1. CALCULATE TOTAL CUSTOMER OBLIGATION
                total_customer_obligation = final_cost_by_staff + hp_fee_to_charge + incentive_earned
                
                # 2. CALCULATE REQUIRED DOWN PAYMENT
                remaining_upfront_needed = total_customer_obligation - dd_amount
                calculated_dp = max(0.0, remaining_upfront_needed)

                # Final Assignment
                down_payment = calculated_dp
                total_paid = dd_amount + down_payment
                financed_amount = total_customer_obligation - total_paid
                if financed_amount < 0:
                    financed_amount = 0.0

            # --- Final Summary of Charges (Outside Expander, prominent) ---
            st.markdown("### Final Figures")
            
            col_hp, col_incentive, col_financed = st.columns(3)
            col_hp.metric("HP Fee Charged", f"₹{hp_fee_to_charge:,.2f}")
            col_incentive.metric("Incentive Collected", f"₹{incentive_earned:,.2f}")
            col_financed.metric("TOTAL FINANCED", f"₹{financed_amount:,.2f}")
            
            st.markdown(f"**Total Customer Obligation (Vehicle + Fees):** **₹{total_customer_obligation:,.2f}**")
            st.success(f"**Required Down Payment:** **₹{calculated_dp:,.2f}**")
            
        
        # --- CASH SALE FINAL DISPLAY ---
        else:
            total_customer_obligation = final_cost_by_staff
            st.success(f"Total Cash Amount Due: **₹{total_customer_obligation:,.2f}**")
            down_payment = 0.0
            hp_fee_to_charge = 0.0
            incentive_earned = 0.0


    # --- 5. Generate PDF Button ---
    st.markdown("---")
    if st.button("GENERATE DUAL-FIRM BILLS", type="primary"):
        if not name or not phone:
            st.error("Please enter Customer Name and Phone Number.")
            return
        
        if sale_type == 'Finance' and financier_name == 'Bank' and not banker_name.strip():
            st.error("Please enter the Banker's Name for the 'Bank' quotation.")
            return

        # Generate DC Number
        dc_number = get_next_dc_number(GSPREAD_CLIENT, SPREADSHEET_TITLE)
        
        # Get the correct financier name for the record 
        final_financier_name = banker_name if financier_name == 'Bank' and banker_name else financier_name

        # --- ACCESSORY INVOICE NUMBER GENERATION ---
        acc_bills_data = generate_accessory_bills(selected_model, accessory_bom_df, firm_master_df, sales_records_df)
        
        bill_1_inv_seq = acc_bills_data[0].get('Invoice_No', 0) if len(acc_bills_data) > 0 and acc_bills_data[0].get('firm_id') == 1 else 0
        bill_2_inv_seq = acc_bills_data[1].get('Invoice_No', 0) if len(acc_bills_data) > 1 and acc_bills_data[1].get('firm_id') == 2 else 0


        order = SalesOrder(
            name, place, phone, selected_vehicle, final_cost_by_staff, 
            sales_staff, final_financier_name, executive_name, selected_paint_color,
            hp_fee_to_charge,     
            incentive_earned,
            banker_name,
            dc_number,
            [bill for bill in acc_bills_data if bill['grand_total'] > 0],
            bill_1_inv_seq,
            bill_2_inv_seq
        )
        
        if sale_type == "Finance":
            order.set_finance_details(dd_amount, down_payment)
        
        # --- Save Data to Google Sheets ---
        try:
            save_record_to_sheet(order.get_data_for_export(bill_1_inv_seq, bill_2_inv_seq), "Sales_Records", SPREADSHEET_TITLE)
        except Exception as e:
            st.error(f"Error saving data to Google Sheets. Error: {e}")
            
        # --- PDF Generation and Download ---
        pdf_filename = f"DC_{dc_number}_{name.replace(' ', '_')}.pdf"
        
        try:
            order.generate_pdf_challan(pdf_filename)
            
            with open(pdf_filename, "rb") as file:
                st.download_button(
                    label="Download Official DC Form",
                    data=file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
            
            st.success(f"DC generated and saved successfully!")
            st.balloons()
            
        except Exception as e:
            st.error(f"An error occurred during PDF generation. Error: {e}")


if __name__ == "__main__":
    sales_app_ui()