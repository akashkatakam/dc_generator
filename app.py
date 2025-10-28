import streamlit as st
from config import initialize_app_data # Initialize all data
from finance_helper import calculate_finance_fees, get_next_dc_number, HP_FEE_DEFAULT, HP_FEE_BANK_QUOTATION
from data_manager import save_record_to_sheet, GSPREAD_CLIENT # Data persistence
from order import SalesOrder # PDF generation class

# --- ENTRY POINT & UI ---

def sales_app_ui():
    
    # Load all data and global rules (cached)
     
    spreadsheet_title = st.secrets.get("spreadsheet_title") # Read once for persistence functions
    vehicles, color_map, incentive_rules = initialize_app_data(spreadsheet_title['spreadsheet_title'])

    st.title("🚗 Vehicle Sales System")
    
    if not vehicles:
        st.error("Application setup failed. Data could not be loaded from Google Sheets.")
        return

    # Initialize all financial variables needed later in the form
    financier_name = "N/A (Cash Sale)"
    executive_name = "N/A (Cash Sale)" 
    dd_amount = 0.0
    down_payment = 0.0
    hp_fee_to_charge = 0.0
    incentive_earned = 0.0
    banker_name = "" 
    
    # --- 1. CUSTOMER & STAFF CONTAINER ---
    with st.container(border=True):
        st.header("1. Customer & Staff Details")
        col_name, col_phone = st.columns(2)
        with col_name:
            name = st.text_input("Customer Name:")
        with col_phone:
            phone = st.text_input("Phone Number:")
        
        place = st.text_input("Place/City:")

    # --- 2. VEHICLE SELECTION & CONFIGURATION CONTAINER ---
    with st.container(border=True):
        st.header("2. Vehicle & Pricing")
        sales_staff = st.selectbox("Sales Staff:", st.session_state['sales_staff']) 
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

        # --- 2.4 Negotiation ---
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
                out_finance_flag = st.checkbox("Check if **Out Finance** (External):")
                
                col_comp_select, col_comp_add = st.columns([2, 1])

                with col_comp_select:
                    financier_name = st.selectbox(
                        "Financier Company:", 
                        st.session_state['financiers']
                    )

                # Add new company button/input (compact)
                with col_comp_add:
                    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True) # Spacer
                    new_financier = st.text_input("New Co.", label_visibility="collapsed", key="new_financier_input")
                    if st.button("Add Co.", key="add_finance_btn", use_container_width=True):
                        if new_financier and new_financier not in st.session_state['financiers']:
                            st.session_state['financiers'].append(new_financier)
                            st.rerun() 
                        elif new_financier:
                            st.info("Already in list.")

                # Conditional Banker Name Input
                if financier_name == 'Bank':
                    banker_name = st.text_input("Banker's Name (for tracking quote):", key="banker_name_input")
                
                # Executive Selection (Compact)
                col_exec_select, col_exec_add = st.columns([2, 1])
                with col_exec_select:
                    executive_name = st.selectbox("Executive Name:", st.session_state['executives'])

                with col_exec_add:
                    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True) # Spacer
                    new_executive = st.text_input("New Exec.", label_visibility="collapsed", key="new_exec_input")
                    if st.button("Add Exec", key="add_exec_btn", use_container_width=True):
                        if new_executive and new_executive not in st.session_state['executives']:
                            st.session_state['executives'].append(new_executive)
                            st.rerun()
                        elif new_executive:
                            st.info("Already in list.")
                
                # --- Payment Input ---
                st.subheader("Initial Payment & Calculation")
                dd_amount = st.number_input("DD / Booking Amount:", min_value=0.0, step=100.0, format="%.2f", key="dd_input")
            
                
                # --- CRITICAL: Determine HP Fee and Incentive (Must be calculated inside this block) ---
                hp_fee_to_charge, incentive_earned = calculate_finance_fees(
                    financier_name, dd_amount, out_finance_flag, incentive_rules
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
            down_payment = 0.0 # Set explicit zero for logging consistency
            hp_fee_to_charge = 0.0
            incentive_earned = 0.0


    # --- 5. Generate PDF Button (Action Block) ---
    st.markdown("---")
    if st.button("Generate and Download DC PDF", type="primary"):
        # ... (Validation checks remain the same) ...
        if not name or not phone:
            st.error("Please enter Customer Name and Phone Number.")
            return
        if sale_type == 'Finance' and financier_name == 'Bank' and not banker_name.strip():
            st.error("Please enter the Banker's Name for the 'Bank' quotation.")
            return

        # Generate DC Number
        dc_number = get_next_dc_number(GSPREAD_CLIENT, st.secrets.get("spreadsheet_title"))
        
        # Get the correct financier name for the record 
        final_financier_name = banker_name if financier_name == 'Bank' and banker_name else financier_name

        order = SalesOrder(
            name, place, phone, selected_vehicle, final_cost_by_staff, 
            sales_staff, final_financier_name, executive_name, selected_paint_color,
            hp_fee_to_charge,     
            incentive_earned,
            banker_name,
            dc_number
        )
        
        if sale_type == "Finance":
            order.set_finance_details(dd_amount, down_payment)
        
        # --- Save Data to Google Sheets ---
        try:
            save_record_to_sheet(order.get_data_for_export(), st.secrets.get("spreadsheet_title"))
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