import streamlit as st
import pandas as pd
import gspread
from typing import Dict, Any, List, Tuple

# Global variable to hold the opened spreadsheet client instance
GSPREAD_CLIENT = None

import streamlit as st
import pandas as pd
import gspread
from typing import Dict, Any, List, Tuple

# Global variable to hold the opened spreadsheet client instance
GSPREAD_CLIENT = None
@st.cache(ttl=3600)
def load_and_cache_all_data(_spreadsheet_title: str) -> Dict[str, pd.DataFrame]:
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

        sh = GSPREAD_CLIENT.open(_spreadsheet_title) 
        
        worksheet_names = ["Sales_Staff", "Finance_Executives", "Financiers", "Price_List", "Colors", "Sales_Records"]
        data_frames = {}

        for name in worksheet_names:
            try:
                worksheet = sh.worksheet(name)
                data = worksheet.get_all_values() 
                
                if data and len(data) > 1:
                    df = pd.DataFrame(data[1:], columns=data[0])
                    for col in df.columns:
                        
                        # --- CRITICAL FIX: Use robust type checking function instead of .dtype ---
                        # Use is_string_dtype() to safely check if the column holds text, 
                        # which avoids the internal Pandas AttributeError conflict.
                        if pd.api.types.is_string_dtype(df[col]):
                            # This applies cleaning only if the column is detected as string-like.
                            df[col] = df[col].str.replace(',', '', regex=False).str.strip()
                        elif df[col].dtype == 'object':
                            # Fallback for generic object types
                            df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.strip()
                        # --- END CRITICAL FIX ---

                    data_frames[name] = df
                else:
                    data_frames[name] = pd.DataFrame() 
            except gspread.WorksheetNotFound:
                st.error(f"Worksheet '{name}' not found. Check spelling in Google Sheet.")
                return None
        
        return data_frames
         

def save_record_to_sheet(record_data: Dict[str, Any], spreadsheet_title: str):
    """Appends a new sales record to the Sales_Records worksheet."""
    global GSPREAD_CLIENT
    
    if GSPREAD_CLIENT is None:
        GSPREAD_CLIENT = gspread.service_account_from_dict(st.secrets["google_service_account"])

    try:
        sh = GSPREAD_CLIENT.open(spreadsheet_title['spreadsheet_title'])
        worksheet = sh.worksheet("Sales_Records")
        worksheet.append_row(list(record_data.values()))
    except Exception as e:
        st.error(f"Error saving data to Google Sheets. Error: {e}")