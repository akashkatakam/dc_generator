import streamlit as st
import pandas as pd
import json
from order import SalesOrder 
import os 
import numpy as np 

# --- Data Constants and Definitions ---
HYPOTHECATION_FEE_DEFAULT = 2000 
HYPOTHECATION_FEE_BANK_QUOTATION = 500 

# --- Core List Loading Function ---
def load_list_from_csv(file_path, column_name):
    """
    Loads a single list from a CSV file. Special case: loads incentive rules 
    and company names from 'finance_companies.csv'.
    """
    try:
        df = pd.read_csv(file_path)
        
        # Standard List Loading
        if column_name in df.columns:
            name_list = df[column_name].dropna().astype(str).tolist()
        else:
            st.error(f"Error: Column '{column_name}' not found in {file_path}. Check CSV header.")
            name_list = []

        # Incentive Loading (Special Logic for Financiers)
        incentive_rules = {}
        if file_path == "finance_companies.csv" and 'incentive_type' in df.columns and 'incentive_value' in df.columns:
            incentive_df = df.dropna(subset=['incentive_type', 'incentive_value'])
            
            for index, row in incentive_df.iterrows():
                incentive_rules[row['finance_company']] = { 
                    'type': row['incentive_type'],
                    'value': float(row['incentive_value']) 
                }
            return name_list, incentive_rules
        
        return name_list

    except FileNotFoundError:
        st.warning(f"Configuration file {file_path} not found. Using empty list.")
        return ([], {}) if file_path == "finance_companies.csv" else []
    except Exception as e:
        st.error(f"Error loading list from {file_path}: {e}")
        return ([], {}) if file_path == "finance_companies.csv" else []

# --- Core Color Data Loading Function ---
def load_color_data(file_path="colors.json"):
    """Loads a dictionary of {Model: [Colors]} from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"Configuration file {file_path} not found. Color options will be unavailable.")
        return {}
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from {file_path}. Check file format.")
        return {}
    except Exception as e:
        st.error(f"Error loading color data: {e}")
        return {}

# --- Core Vehicle Data Loading Function ---
def load_vehicle_data(file_path="price_list.csv"):
    """
    Loads vehicle data from a CSV file, calculates the tax component,
    and renames columns to match the application's SalesOrder requirements,
    using ORP as the base price component.
    """
    try:
        df = pd.read_csv(file_path)
        
        required_cols = ['MODEL', 'VARIANT', 'ORP', 'FINAL PRICE'] 
        if not all(col in df.columns for col in required_cols):
            st.error(f"Error: Missing required columns in price_list.csv. Check for: {required_cols}")
            return []

        df['tax'] = df['FINAL PRICE'] - df['ORP']
        
        df.rename(columns={
            'MODEL': 'model',
            'VARIANT': 'color',
            'ORP': 'orp',
            'FINAL PRICE': 'total_price'
        }, inplace=True)
        
        final_cols = ['model', 'color', 'orp', 'tax', 'total_price']
        df = df[final_cols]
        
        for col in ['orp', 'tax', 'total_price']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(subset=['orp', 'total_price'], inplace=True)
        return df.to_dict('records')
        
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it's in the same directory.")
        return []
    except Exception as e:
        st.error(f"An error occurred while reading the CSV file: {e}")
        return []


# --- Initial Setup (Load lists and use Session State) ---
INITIAL_STAFF_LIST = load_list_from_csv("staff_list.csv", "executive_name")
INITIAL_FINANCIER_LIST, INCENTIVE_RULES = load_list_from_csv("finance_companies.csv", "finance_company")
INITIAL_EXECUTIVE_LIST = load_list_from_csv("finance_executives.csv", "finance_exectives")

if 'sales_staff' not in st.session_state:
    st.session_state['sales_staff'] = INITIAL_STAFF_LIST

if 'financiers' not in st.session_state:
    st.session_state['financiers'] = INITIAL_FINANCIER_LIST

if 'executives' not in st.session_state:
    st.session_state['executives'] = INITIAL_EXECUTIVE_LIST


# --- UI Application ---
def sales_app_ui():
    st.title("🚗 DC Generator / Vehicle Sales System")
    
    vehicles = load_vehicle_data()
    color_map = load_color_data()
    if not vehicles:
        return

    # --- 1. Customer Details ---
    st.header("1. Customer Details")
    col_name, col_phone = st.columns(2)
    with col_name:
        name = st.text_input("Customer Name:")
    with col_phone:
        phone = st.text_input("Phone Number:")
    place = st.text_input("Place/City:")

    # --- 2. Staff & Vehicle Selection (Cascading Dropdowns) ---
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

    # Find the Final Selected Vehicle Data (Price/Tax data is based on Model & Variant)
    selected_vehicle = next(
        (v for v in available_variants if v['color'] == selected_variant), 
        None
    )
    if selected_vehicle is None:
        st.error("Could not find price data for the selected combination.")
        return
    
    listed_price = selected_vehicle['total_price']
    st.info(f"Selected: **{selected_model} {selected_variant}** in **{selected_paint_color}**")
    st.info(f"CSV Listed Total Price: **{listed_price:,.2f}**")

    # --- 3. Negotiated Final Cost & Discount ---
    st.header("3. Negotiated Final Cost")
    
    final_cost_by_staff = st.number_input(
        "Enter Final Vehicle Cost (after discount):", 
        min_value=0.0, 
        value=float(listed_price),
        step=100.0,
        format="%.2f"
    )
    
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
    
    # New variables for finance calculation
    hp_fee_to_charge = 0.0
    incentive_earned = 0.0
    banker_name = "" # Initialize banker name

    if sale_type == "Finance":
        
        # --- Financier Company Selection and Management ---
        st.subheader("Financier Company Details")
        
        # 4.1 Out Finance Flag
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

        # 4.2 Conditional Banker Name Input
        if financier_name == 'Bank':
            st.markdown("---")
            st.subheader("Bank Quotation Details")
            banker_name = st.text_input("Enter Banker's Name (for tracking quote):", key="banker_name_input")
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
            # SCENARIO 2: Out Finance
            hp_fee_to_charge = HYPOTHECATION_FEE_DEFAULT # $2000 HP Fee
            incentive_earned = 0.0 # No incentive collected

        elif financier_name == 'Bank':
            # SCENARIO 1: Bank Quotation (Low HP)
            hp_fee_to_charge = HYPOTHECATION_FEE_BANK_QUOTATION # $500 HP Fee
            incentive_earned = 0.0 # No incentive collected

        else:
            # SCENARIO 3: Other Financiers (Full HP + Incentive)
            hp_fee_to_charge = HYPOTHECATION_FEE_DEFAULT # $2000 HP Fee
            
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
        st.markdown(f"**Final Amount to be Financed:** **{financed_amount:,.2f}**")
        
    
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