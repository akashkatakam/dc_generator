import streamlit as st
import pandas as pd
import gspread
from typing import Dict, Any, List, Tuple
import time

# --- CONSTANTS (Used by this module and others) ---
HP_FEE_DEFAULT = 2000.00
HP_FEE_BANK_QUOTATION = 500.00

# --- FINANCIAL CALCULATION FUNCTIONS ---

def calculate_finance_fees(financier_name: str, dd_amount: float, out_finance_flag: bool, incentive_rules: Dict[str, Any]) -> Tuple[float, float]:
    """Calculates the Hypothecation fee and incentive collected from the customer."""
    
    hp_fee_to_charge = 0.0
    incentive_earned = 0.0

    if out_finance_flag:
        # SCENARIO 2: Out Finance ($2000 HP Fee, No incentive)
        hp_fee_to_charge = HP_FEE_DEFAULT
        incentive_earned = 0.0 

    elif financier_name == 'Bank':
        # SCENARIO 1: Bank Quotation ($500 HP Fee, No incentive)
        hp_fee_to_charge = HP_FEE_BANK_QUOTATION
        incentive_earned = 0.0

    else:
        # SCENARIO 3: Other Financiers (Full HP + Incentive)
        hp_fee_to_charge = HP_FEE_DEFAULT
        
        if financier_name in incentive_rules:
            rule = incentive_rules[financier_name]
            if rule['type'] == 'percentage_dd':
                incentive_earned = dd_amount * rule['value']
            elif rule['type'] == 'fixed_file':
                incentive_earned = rule['value']
    
    return hp_fee_to_charge, incentive_earned

# --- DC NUMBER GENERATION (CONCURRENCY SAFE) ---

def get_next_dc_number(gspread_client: gspread.Client, spreadsheet_title: str) -> str:
    """Generates the next sequential DC number by reading the last one saved."""
    try:
        sh = gspread_client.open(spreadsheet_title['spreadsheet_title'])
        worksheet = sh.worksheet("Sales_Records")
        
        # Get all values from the 'DC_Number' column (assumed to be Column 2)
        dc_column = worksheet.col_values(2) 
        
        next_number = 1
        if len(dc_column) > 1:
            dc_numbers = dc_column[1:] 
            current_numbers = []

            for dc_str in dc_numbers:
                if dc_str:
                    try:
                        # Extract the numeric part (e.g., '0015')
                        current_numbers.append(int(dc_str))
                    except ValueError:
                        pass
            
            if current_numbers:
                next_number = max(current_numbers) + 1
            else:
                next_number = 1
        else:
            next_number = 1
        
        # Format as a sequential number (e.g., DC-0001)
        return f"{next_number:05d}"
        
    except Exception as e:
        st.error(f"Could not generate sequential DC number. Error: {e}")
        return f"DC-ERROR-{pd.Timestamp('now').strftime('%H%M')}"