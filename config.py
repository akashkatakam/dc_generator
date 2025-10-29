import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Tuple
from data_manager import load_and_cache_all_data

@st.cache_data(ttl=3600)
def initialize_app_data(spreadsheet_title: str) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str], List[str], List[str]]:
    """
    Loads all configuration data and sales records from Google Sheets (cached), 
    processes it, and returns the variables required by app.py.
    """
    
    # 1. Load all raw DataFrames from Google Sheets (cached call)
    all_dfs = load_and_cache_all_data(spreadsheet_title) 
    
    # Handle fatal error during caching/loading
    if all_dfs is None:
        return [], {}, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], [], []

    # --- 2. Process Lists (Staff, Executives, Financiers) ---
    staff_df = all_dfs.get("Sales_Staff", pd.DataFrame())
    exec_df = all_dfs.get("Finance_Executives", pd.DataFrame())
    financier_df = all_dfs.get("Financiers", pd.DataFrame())
    
    # Process Staff/Executive Lists
    initial_staff = staff_df['executive_name'].dropna().astype(str).tolist() if 'executive_name' in staff_df.columns else []
    initial_executives = exec_df['finance_exectives'].dropna().astype(str).tolist() if 'finance_exectives' in exec_df.columns else []
    
    # Process Financiers and Incentives
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

    # --- 3. Process Vehicle Pricing Data ---
    vehicle_df = all_dfs.get("Price_List", pd.DataFrame())
    vehicles = []
    if vehicle_df is not None and 'ORP' in vehicle_df.columns and 'FINAL PRICE' in vehicle_df.columns:
        # Columns are already cleaned of commas in data_manager
        vehicle_df['tax'] = pd.to_numeric(vehicle_df['FINAL PRICE'], errors='coerce') - pd.to_numeric(vehicle_df['ORP'], errors='coerce')
        vehicle_df.rename(columns={
            'MODEL': 'model', 'VARIANT': 'color', 'ORP': 'orp', 'FINAL PRICE': 'total_price'
        }, inplace=True)
        for col in ['orp', 'tax', 'total_price']:
            vehicle_df[col] = pd.to_numeric(vehicle_df[col], errors='coerce')
        vehicles = vehicle_df.dropna(subset=['orp', 'total_price']).to_dict('records')
    
    # --- 4. Process Color Data ---
    color_df = all_dfs.get("Colors", pd.DataFrame())
    color_map = {}
    if color_df is not None and 'MODEL' in color_df.columns and 'Color_List' in color_df.columns:
        color_map = {
            row['MODEL']: [c.strip() for c in str(row['Color_List']).split('.')]
            for index, row in color_df.iterrows()
        }
    
    # --- 5. Prepare Accessory Data DFs (Passed directly to order logic) ---
    accessory_bom_df = all_dfs.get("Accessory_BOM", pd.DataFrame())
    firm_master_df = all_dfs.get("Firm_Master", pd.DataFrame())
    sales_records_df = all_dfs.get("Sales_Records", pd.DataFrame()) # Used for DC number generation

    # --- 6. Return all 9 processed items ---
    return vehicles, color_map, incentive_rules, firm_master_df, accessory_bom_df, sales_records_df, initial_staff, initial_executives, initial_financiers