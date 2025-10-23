import streamlit as st
import pandas as pd
import json
import os 
import gspread 
import numpy as np

from order import SalesOrder

# --- Data Constants and Definitions ---
HYPOTHECATION_FEE_DEFAULT = 2000 
HYPOTHECATION_FEE_BANK_QUOTATION = 500 

# Global variable to hold the opened spreadsheet client instance
GSPREAD_CLIENT = None
INCENTIVE_RULES = {}
SPREADSHEET_TITLE = "Sales Records DB" # Default title, used if not in secrets

# --- Core Data Loading Function (CACHED and Optimized) ---
@st.cache_data(ttl=3600) # Cache data for 1 hour (3600 seconds)
def load_and_cache_all_data():
    """
    Opens the Google Sheet once and fetches data from all required worksheets.
    Returns a dictionary of DataFrames.
    """
    global GSPREAD_CLIENT
    
    if GSPREAD_CLIENT is None:
        try:
            # Authentication block
            GSPREAD_CLIENT = gspread.service_account_from_dict(st.secrets["google_service_account"])
        except Exception as e:
            st.error(f"Authentication Error: Could not connect to Google Sheets. Check 'secrets.toml'. Error: {e}")
            return None

    try:
        spreadsheet_title = st.secrets.get("spreadsheet_title", SPREADSHEET_TITLE)
        # --- OPTIMIZATION: Open the entire workbook ONCE ---
        sh = GSPREAD_CLIENT.open(spreadsheet_title['spreadsheet_title']) 
        
        # List of worksheets to load
        worksheet_names = ["sales_staff", "finance_executives", "finance_companies", "price_list", "colors"]
        data_frames = {}

        for name in worksheet_names:
            try:
                worksheet = sh.worksheet(name)
                # Manually create DataFrame using all values for robustness (first row is header)
                data = worksheet.get_all_values() 
                if data:
                    data_frames[name] = pd.DataFrame(data[1:], columns=data[0])
                else:
                    data_frames[name] = pd.DataFrame() 
            except gspread.WorksheetNotFound:
                st.error(f"Worksheet '{name}' not found. Please check spelling in Google Sheet.")
                return None
        
        return data_frames
        
    except Exception as e:
        st.error(f"Error accessing Google Sheet '{spreadsheet_title}'. Error: {e}")
        return None

# --- Core Data Initialization Function (Processes Cached DataFrames) ---
def initialize_all_data():
    """Processes the cached DataFrames into the variables used by the UI."""
    global INCENTIVE_RULES

    all_dfs = load_and_cache_all_data()
    if all_dfs is None:
        return [], {}

    # --- 1. Process Lists (Staff, Executives, Financiers) ---
    staff_df = all_dfs.get("sales_staff")
    exec_df = all_dfs.get("finance_executives")
    financier_df = all_dfs.get("finance_companies")
    
    # Staff List
    initial_staff = staff_df['executive_name'].dropna().astype(str).tolist() if staff_df is not None and 'executive_name' in staff_df.columns else []
    # Executive List
    initial_executives = exec_df['finance_executives'].dropna().astype(str).tolist() if exec_df is not None and 'finance_executives' in exec_df.columns else []
    
    # Financiers and Incentives
    if financier_df is not None and 'finance_company' in financier_df.columns:
        initial_financiers = financier_df['finance_company'].dropna().astype(str).tolist()
        INCENTIVE_RULES = {}
        for index, row in financier_df.dropna(subset=['incentive_type', 'incentive_value']).iterrows():
            
            # CRITICAL CLEANING STEP: Remove commas from incentive_value string
            raw_value = str(row['incentive_value']).replace(',', '').strip()
            
            # Handle potential empty string after cleaning
            if raw_value:
                INCENTIVE_RULES[row['finance_company']] = {
                    'type': row['incentive_type'],
                    'value': float(raw_value)
                }
    else:
        initial_financiers = []
        INCENTIVE_RULES = {}
        
    # Store in Session State
    if 'sales_staff' not in st.session_state:
        st.session_state['sales_staff'] = initial_staff
    if 'financiers' not in st.session_state:
        st.session_state['financiers'] = initial_financiers
    if 'executives' not in st.session_state:
        st.session_state['executives'] = initial_executives
        
    # --- 2. Process Vehicle Pricing Data ---
    vehicle_df = all_dfs.get("price_list")
    vehicles = []
    if vehicle_df is not None and 'ORP' in vehicle_df.columns and 'FINAL PRICE' in vehicle_df.columns:
        vehicle_df['tax'] = pd.to_numeric(vehicle_df['FINAL PRICE'], errors='coerce') - pd.to_numeric(vehicle_df['ORP'], errors='coerce')
        vehicle_df.rename(columns={
            'MODEL': 'model', 'VARIANT': 'color', 'ORP': 'orp', 'FINAL PRICE': 'total_price'
        }, inplace=True)
        for col in ['orp', 'tax', 'total_price']:
            vehicle_df[col] = pd.to_numeric(vehicle_df[col], errors='coerce')
        vehicles = vehicle_df.dropna(subset=['orp', 'total_price']).to_dict('records')
    
    # --- 3. Process Color Data ---
    color_df = all_dfs.get("colors")
    color_map = {}
    if color_df is not None and 'MODEL' in color_df.columns and 'Color_List' in color_df.columns:
        color_map = {
            row['MODEL']: [c.strip() for c in str(row['Color_List']).split(',')]
            for index, row in color_df.iterrows()
        }
    
    return vehicles, color_map


# --- UI Application ---
def sales_app_ui():
    
    vehicles, color_map = initialize_all_data() 

    st.title("🚗 DC Generator / Vehicle Sales System")
    
    if not vehicles:
        st.error("Application setup failed. Data could not be loaded from Google Sheets.")
        return

    # --- 1. Customer Details ---
    st.header("1. Customer Details")
    col_name, col_phone = st.columns(2)
    with col_name:
        name = st.text_input("Customer Name:")
    with col_phone:
        phone = st.text_input("Phone Number:")
    place = st.text_input("Place/City:")

    # --- 2. Staff & Vehicle Selection ---
    st.header("2. Staff & Vehicle Selection")
    col_staff, col_model = st.columns(2)
    with col_staff:
        sales_staff = st.selectbox("Sales Staff:", st.session_state['sales_staff']) 

    # 2.1 Model Selection
    all_models = sorted(list(set([v['model'].strip() for v in vehicles])))
    with col_model:
        selected_model = st.selectbox("Select Vehicle Model:", all_models)

    # Filter by Model for Variant/Trim
    available_variants = [v for v in vehicles if v['model'].strip() == selected_model]
    variant_options = [v['color'] for v in available_variants]
    selected_variant = st.selectbox("Select Variant/Trim Level:", variant_options)

    # 2.3 Paint Color Selection
    model_colors = color_map.get(selected_model, ["No Colors Available"])
    selected_paint_color = st.selectbox("Select Paint Color:", model_colors)

    # Find the Final Selected Vehicle Data 
    selected_vehicle = next(
        (v for v in available_variants if v['color'] == selected_variant), 
        None
    )
    if selected_vehicle is None:
        st.error("Could not find price data for the selected combination.")
        return
    
    listed_price = selected_vehicle['total_price']
    st.info(f"Selected: **{selected_model} {selected_variant}** in **{selected_paint_color}**")
    st.info(f"Total Price: **{listed_price:,.2f}**")

    # --- 3. Negotiated Final Cost & Discount ---
    st.header("3. Negotiated Final Cost")
    
    final_cost_by_staff = st.number_input(
        "Enter Final Vehicle Cost (after discount):", 
        min_value=0.0, 
        value=float(listed_price),
        step=100.0,
        format="%.2f"
    )
    st.subheader("PR")
    pr_enabled_flag = st.checkbox("Check here to confirm PR applicable for this sale.")
    
    if pr_enabled_flag:
        st.info("PR will be done by the dealership")
    
    discount_amount = listed_price - final_cost_by_staff
    
    if discount_amount > 0:
        st.success(f"Discount Given: **{discount_amount:,.2f}**")
    elif discount_amount < 0:
        st.warning(f"Markup Applied: {abs(discount_amount):,.2f}")
    else:
        st.markdown("No Discount applied.")


    # --- 4. Payment Details (Finance Management) ---
    st.header("4. Payment Details")
    sale_type = st.radio("Sale Type:", ["Cash", "Finance"])
    
    financier_name = "N/A (Cash Sale)"
    executive_name = "N/A (Cash Sale)" 
    dd_amount = 0.0
    down_payment = 0.0
    
    hp_fee_to_charge = 0.0
    incentive_earned = 0.0
    banker_name = "" 

    if sale_type == "Finance":
        
        # --- Financier Company Selection and Management ---
        st.subheader("Financier Company Details")
        
        out_finance_flag = st.checkbox("Check here if this is **Out Finance** (Financing done externally).")
        
        col_comp_select, col_comp_new = st.columns([2, 1])

        with col_comp_select:
            financier_name = st.selectbox(
                "Select Existing Financier Company:", 
                st.session_state['financiers']
            )

        with col_comp_new:
            new_financier = st.text_input("Or Add New Company:")
            if st.button("Add Company"):
                if new_financier and new_financier not in st.session_state['financiers']:
                    st.session_state['financiers'].append(new_financier)
                    st.success(f"'{new_financier}' added! Please select it from the dropdown.")
                    st.rerun() 
                elif new_financier:
                    st.info("Financier already in the list.")

        # 4.3 Conditional Banker Name Input
        if financier_name == 'Bank':
            st.markdown("---")
            st.subheader("Bank Quotation Details")
            banker_name = st.text_input("Enter Banker's Name (for tracking quote):", key="banker_name_input")
            financier_name = banker_name
            st.markdown("---")


        # --- Finance Executive Selection and Management ---
        st.subheader("Finance Executive Details")
        col_exec_select, col_exec_new = st.columns([2, 1])

        with col_exec_select:
            executive_name = st.selectbox(
                "Select Executive Name:",
                st.session_state['executives']
            )

        with col_exec_new:
            new_executive = st.text_input("Or Add New Executive:")
            if st.button("Add Executive"):
                if new_executive and new_executive not in st.session_state['executives']:
                    st.session_state['executives'].append(new_executive)
                    st.success(f"'{new_executive}' added! Please select it from the dropdown.")
                    st.rerun()
                elif new_executive:
                    st.info("Executive already in the list.")


        # --- Down Payment and DD Input ---
        st.subheader("Payment Amounts")
        col_dd, col_dp_calc = st.columns(2)

        with col_dd:
            dd_amount = st.number_input("DD / Booking Amount:", min_value=0.0, step=100.0, format="%.2f", key="dd_input")
        
        
        # --- CRITICAL: Determine HP Fee and Incentive ---
        if out_finance_flag:
            # SCENARIO 2: Out Finance ($2000 HP Fee, No incentive)
            hp_fee_to_charge = HYPOTHECATION_FEE_DEFAULT
            incentive_earned = 0.0 

        elif financier_name == 'Bank':
            # SCENARIO 1: Bank Quotation ($500 HP Fee, No incentive)
            hp_fee_to_charge = HYPOTHECATION_FEE_BANK_QUOTATION
            incentive_earned = 0.0

        else:
            # SCENARIO 3: Other Financiers (Full HP + Incentive)
            hp_fee_to_charge = HYPOTHECATION_FEE_DEFAULT
            
            if financier_name in INCENTIVE_RULES:
                rule = INCENTIVE_RULES[financier_name]
                if rule['type'] == 'percentage_dd':
                    incentive_earned = dd_amount * rule['value']
                elif rule['type'] == 'fixed_file':
                    incentive_earned = rule['value']
        
        
        # 1. CALCULATE TOTAL CUSTOMER OBLIGATION
        total_customer_obligation = final_cost_by_staff + hp_fee_to_charge + incentive_earned
        
        # 2. CALCULATE REQUIRED DOWN PAYMENT
        remaining_upfront_needed = total_customer_obligation - dd_amount
        
        with col_dp_calc:
            if remaining_upfront_needed < 0:
                calculated_dp = 0.0
                st.info(f"Required Down Payment: 0.00")
                st.warning(f"DD amount covers all costs! Excess collected: {abs(remaining_upfront_needed):,.2f}")
            else:
                calculated_dp = remaining_upfront_needed
                st.info(f"Required Down Payment: **{calculated_dp:,.2f}**")
        
        # --- Final Assignment ---
        down_payment = calculated_dp
        total_paid = dd_amount + down_payment

        # 3. CALCULATE FINAL FINANCED AMOUNT
        financed_amount = total_customer_obligation - total_paid
        if financed_amount < 0:
            financed_amount = 0.0

        # Display fees and final financed amount
        st.markdown(f"**Hypothecation Fee Charged:** **{hp_fee_to_charge:,.2f}**")
        st.markdown(f"**Financier Incentive Collected:** **{incentive_earned:,.2f}**")
        st.markdown(f"**Total Customer Obligation:** **{total_customer_obligation:,.2f}**")
        
    
    # --- 5. Generate PDF Button ---
    st.markdown("---")
    if st.button("Generate and Download DC PDF", type="primary"):
        if not name or not phone:
            st.error("Please enter Customer Name and Phone Number.")
            return
        
        if financier_name == 'Bank' and not banker_name.strip():
            st.error("Please enter the Banker's Name for the 'Bank' quotation.")
            return

        order = SalesOrder(
            name, place, phone, selected_vehicle, final_cost_by_staff, 
            sales_staff, financier_name, executive_name, selected_paint_color,
            hp_fee_to_charge,     
            incentive_earned,
            banker_name
        )
        
        if sale_type == "Finance":
            order.set_finance_details(dd_amount, down_payment)
        
        # --- Save Data to Google Sheets (Sales Records) ---
        record_data = order.get_data_for_export()
        try:
            gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
            spreadsheet_title = st.secrets.get("spreadsheet_title", SPREADSHEET_TITLE)
        # --- OPTIMIZATION: Open the entire workbook ONCE ---
            sh = gc.open(spreadsheet_title['spreadsheet_title'])
            worksheet = sh.worksheet("sales_records")
            worksheet.append_row(list(record_data.values()))
            # Do NOT rerun or show success here to avoid premature script exit
        except Exception as e:
            st.error(f"Error saving data to Google Sheets. Error: {e}")
            
        # --- PDF Generation and Download ---
        pdf_filename = f"DC_{name.replace(' ', '_')}_{order.vehicle['model'].replace(' ', '_')}.pdf"
        
        try:
            order.generate_pdf_challan(pdf_filename)
            
            with open(pdf_filename, "rb") as file:
                st.download_button(
                    label="Download Official DC Form",
                    data=file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
            
            st.success(f"Delivery Challan generated for {name}! Click the button to download.")
            st.balloons()
            
        except Exception as e:
            st.error(f"An error occurred during PDF generation. Error: {e}")


if __name__ == "__main__":
    sales_app_ui()