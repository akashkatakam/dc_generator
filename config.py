import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Tuple
from data_manager import load_and_cache_all_data

# NOTE: INCENTIVE_RULES is a global dictionary in data_manager.py
# We will use it directly but access the data via a processing layer.

def initialize_app_data(spreadsheet_title: str) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any]]:
    """Loads and processes all data into variables and session state."""
    
    all_dfs = load_and_cache_all_data(spreadsheet_title)
    if all_dfs is None:
        return [], {}, {}

    # --- Process Lists (Staff, Executives, Financiers) ---
    staff_df = all_dfs.get("Sales_Staff", pd.DataFrame())
    exec_df = all_dfs.get("Finance_Executives", pd.DataFrame())
    financier_df = all_dfs.get("Financiers", pd.DataFrame())
    
    # Standardize column access names based on previous requirements/logs
    initial_staff = staff_df['executive_name'].dropna().astype(str).tolist() if 'executive_name' in staff_df.columns else []
    initial_executives = exec_df['finance_exectives'].dropna().astype(str).tolist() if 'finance_exectives' in exec_df.columns else []
    
    incentive_rules = {}
    if 'finance_company' in financier_df.columns:
        initial_financiers = financier_df['finance_company'].dropna().astype(str).tolist()
        
        for index, row in financier_df.dropna(subset=['incentive_type', 'incentive_value']).iterrows():
            raw_value = str(row['incentive_value']).strip()
            if raw_value:
                incentive_rules[row['finance_company']] = {
                    'type': row['incentive_type'],
                    'value': float(raw_value)
                }
    else:
        initial_financiers = []

    # Store in Session State
    if 'sales_staff' not in st.session_state:
        st.session_state['sales_staff'] = initial_staff
    if 'financiers' not in st.session_state:
        st.session_state['financiers'] = initial_financiers
    if 'executives' not in st.session_state:
        st.session_state['executives'] = initial_executives
        
    # --- Process Vehicle Pricing Data ---
    vehicle_df = all_dfs.get("Price_List", pd.DataFrame())
    vehicles = []
    if 'ORP' in vehicle_df.columns and 'FINAL PRICE' in vehicle_df.columns:
        vehicle_df['tax'] = pd.to_numeric(vehicle_df['FINAL PRICE'], errors='coerce') - pd.to_numeric(vehicle_df['ORP'], errors='coerce')
        vehicle_df.rename(columns={
            'MODEL': 'model', 'VARIANT': 'color', 'ORP': 'orp', 'FINAL PRICE': 'total_price'
        }, inplace=True)
        for col in ['orp', 'tax', 'total_price']:
            vehicle_df[col] = pd.to_numeric(vehicle_df[col], errors='coerce')
        vehicles = vehicle_df.dropna(subset=['orp', 'total_price']).to_dict('records')
    
    # --- Process Color Data ---
    color_df = all_dfs.get("Colors", pd.DataFrame())
    color_map = {}
    if 'MODEL' in color_df.columns and 'Color_List' in color_df.columns:
        color_map = {
            row['MODEL']: [c.strip() for c in str(row['Color_List']).split('.')]
            for index, row in color_df.iterrows()
        }
    
    return vehicles, color_map, incentive_rules