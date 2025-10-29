import streamlit as st
import pandas as pd
import gspread
from typing import Dict, Any

# Global variable to hold the opened spreadsheet client instance
GSPREAD_CLIENT = None

# @st.cache_data(ttl=3600) # Cache data for 1 hour
def load_and_cache_all_data(spreadsheet_title: str) -> Dict[str, pd.DataFrame]:
    """
    Opens the Google Sheet once and fetches data from all required worksheets.
    Returns a dictionary of DataFrames.
    """
    global GSPREAD_CLIENT
    
    if GSPREAD_CLIENT is None:
        try:
            GSPREAD_CLIENT = gspread.service_account_from_dict(st.secrets["google_service_account"])
        except Exception as e:
            st.error(f"Authentication Error: Could not connect to Google Sheets. Check 'secrets.toml'. Error: {e}")
            return None

    try:
        sh = GSPREAD_CLIENT.open(spreadsheet_title) 
        
        # NOTE: Added all required worksheets, including accessory data and logs
        worksheet_names = ["Sales_Staff", "Finance_Executives", "Financiers", "Price_List", "Colors", "Sales_Records", 
                           "Accessory_BOM", "Firm_Master"]
        data_frames = {}

        for name in worksheet_names:
            try:
                worksheet = sh.worksheet(name)
                data = worksheet.get_all_values() 
                
                if data and len(data) > 1:
                    df = pd.DataFrame(data[1:], columns=data[0])
                    for col in df.columns:
                        if df[col].dtype == 'object':
                            # Remove commas and clean strings for safe numeric conversion later
                            df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.strip()
                    data_frames[name] = df
                else:
                    data_frames[name] = pd.DataFrame() 
            except gspread.WorksheetNotFound:
                st.error(f"Worksheet '{name}' not found. Check spelling in Google Sheet.")
                return None
        
        return data_frames
        
    except Exception as e:
        st.error(f"Error accessing Google Sheet '{spreadsheet_title}'. Error: {e}")
        return None

def save_record_to_sheet(record_data: Dict[str, Any], worksheet_name: str, spreadsheet_title: str):
    """Appends a new record to the specified worksheet."""
    global GSPREAD_CLIENT
    
    if GSPREAD_CLIENT is None:
        GSPREAD_CLIENT = gspread.service_account_from_dict(st.secrets["google_service_account"])

    try:
        sh = GSPREAD_CLIENT.open(spreadsheet_title)
        worksheet = sh.worksheet(worksheet_name)
        
        # Append the row
        worksheet.append_row(list(record_data.values()))
            
    except Exception as e:
        st.error(f"Error saving data to worksheet '{worksheet_name}'. Error: {e}")