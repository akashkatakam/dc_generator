import streamlit as st
import pandas as pd
from order import SalesOrder # Assumes order.py is still in place
import os # To check for file existence

# --- Initial Setup (Use Session State for Dynamic Lists) ---
# Initialize the list of financiers if it doesn't exist in the session state
if 'financiers' not in st.session_state:
    st.session_state['financiers'] = ['Bank A', 'Bank B', 'NBFC C', 'In-House Finance']

# Fixed list of sales staff for now (could also be dynamic)
SALES_STAFF_LIST = ['Alice', 'Bob', 'Charlie', 'Diana']


# --- Core Data Loading Function ---
def load_vehicle_data(file_path="price_list.csv"):
    """
    Loads vehicle data from a CSV file, calculates the tax component,
    and renames columns to match the application's SalesOrder requirements.
    """
    try:
        df = pd.read_csv(file_path)
        
        required_cols = ['MODEL', 'VARIANT', 'EX SHOWROOM', 'FINAL PRICE']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Error: Missing required columns in CSV. Check for: {required_cols}")
            return []

        df['tax'] = df['FINAL PRICE'] - df['EX SHOWROOM']
        
        df.rename(columns={
            'MODEL': 'model',
            'VARIANT': 'color',
            'EX SHOWROOM': 'ex_showroom_price',
            'FINAL PRICE': 'total_price'
        }, inplace=True)
        
        final_cols = ['model', 'color', 'ex_showroom_price', 'tax', 'total_price']
        df = df[final_cols]
        
        # Ensure prices are numerical
        for col in ['ex_showroom_price', 'tax', 'total_price']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df.to_dict('records')
        
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it's in the same directory.")
        return []
    except Exception as e:
        st.error(f"An error occurred while reading the CSV file: {e}")
        return []


# --- UI Application ---
def sales_app_ui():
    st.title("🚗 DC Generator / Vehicle Sales System")
    
    vehicles = load_vehicle_data()
    if not vehicles:
        return

    # --- 1. Customer Details (No Change) ---
    st.header("1. Customer Details")
    col_name, col_phone = st.columns(2)
    with col_name:
        name = st.text_input("Customer Name:")
    with col_phone:
        phone = st.text_input("Phone Number:")
    place = st.text_input("Place/City:")
    
    # --- NEW: Staff Name Selection ---
    st.header("2. Staff & Vehicle Selection")
    col_staff, col_vehicle = st.columns(2)
    with col_staff:
        # 3. To be able to select the sales staff name
        sales_staff = st.selectbox("Sales Staff:", SALES_STAFF_LIST)

    # --- Vehicle Selection ---
    with col_vehicle:
        vehicle_options = [f"{v['model']} - {v['color']}" for v in vehicles]
        selected_option = st.selectbox("Select Vehicle:", vehicle_options)
        
    selected_index = vehicle_options.index(selected_option)
    selected_vehicle = vehicles[selected_index]
    
    listed_price = selected_vehicle['total_price']
    st.info(f"CSV Listed Total Price: **${listed_price:,.2f}**")

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
        st.success(f"Discount Given: **${discount_amount:,.2f}**")
    elif discount_amount < 0:
        st.warning(f"Markup Applied: ${abs(discount_amount):,.2f}")
    else:
        st.markdown("No Discount applied.")


    # --- 4. Payment Details (Combined Finance & Down Payment) ---
    st.header("4. Payment Details")
    sale_type = st.radio("Sale Type:", ["Cash", "Finance"])
    
    financier_name = "N/A (Cash Sale)"
    dd_amount = 0.0
    down_payment = 0.0

    if sale_type == "Finance":
        
        # --- NEW: Financier Selection and Management ---
        st.subheader("Financier Details")
        col_select, col_new = st.columns([2, 1])

        with col_select:
            # 2. To be able to select the financier from the list of drop down
            financier_name = st.selectbox(
                "Select Existing Financier:", 
                st.session_state['financiers']
            )

        with col_new:
            # 4. & 5. If not in the list, enter the new financier name
            new_financier = st.text_input("Or Add New Financier:")
            if st.button("Add Financier"):
                if new_financier and new_financier not in st.session_state['financiers']:
                    st.session_state['financiers'].append(new_financier)
                    st.success(f"'{new_financier}' added! Please select it from the dropdown.")
                    # Rerun the app to update the dropdown list
                    st.rerun() 
                elif new_financier:
                    st.info("Financier already in the list.")


        # --- Down Payment Input ---
        col_dp, col_dd = st.columns(2)
        with col_dp:
            # 1. To be able to enter the down payment amount
            down_payment = st.number_input("Down Payment Amount:", min_value=0.0, step=1000.0)
        with col_dd:
            dd_amount = st.number_input("DD / Booking Amount:", min_value=0.0, step=1000.0)
        
        total_paid = dd_amount + down_payment
        
        # Validation check against the FINAL negotiated cost
        if total_paid > final_cost_by_staff:
             st.error(f"Total payments exceed the Final Negotiated Cost (${final_cost_by_staff:,.2f}).")
             return # Stop generation if invalid
        
        st.markdown(f"**Amount to be Financed:** **${final_cost_by_staff - total_paid:,.2f}**")
        
    
    # --- 5. Generate PDF Button ---
    st.markdown("---")
    if st.button("Generate and Download DC PDF", type="primary"):
        if not name or not phone:
            st.error("Please enter Customer Name and Phone Number.")
            return

        # Instantiate the order
        # NOTE: You will need to update your SalesOrder class in order.py to accept 
        # sales_staff and financier_name if you want them in the PDF.
        order = SalesOrder(name, place, phone, selected_vehicle, final_cost_by_staff,sales_staff,financier_name)
        
        if sale_type == "Finance":
            order.set_finance_details(dd_amount, down_payment)
        
        # ... (PDF generation and download logic remains the same)
        # For simplicity, we skip full PDF logic here but assume it's correctly linked
        # and would now require updating to include staff/financier names.
        st.success(f"DC Generated for {name} with Financier: {financier_name} (Staff: {sales_staff})")
        
        # --- Placeholder for PDF download (Keep your existing PDF code here) ---
        # pdf_filename = f"DC_{name.replace(' ', '_')}_{order.vehicle['model'].replace(' ', '_')}.pdf"
        # order.generate_pdf_challan(pdf_filename)
        # with open(pdf_filename, "rb") as file:
        #     st.download_button(...)
        # -----------------------------------------------------------------------


if __name__ == "__main__":
    sales_app_ui()