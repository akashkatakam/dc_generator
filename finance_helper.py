import streamlit as st
import pandas as pd
import gspread
from typing import Dict, Any, List, Tuple
import time

# --- CONSTANTS (Used by this module and others) ---
HP_FEE_DEFAULT = 2000.00
HP_FEE_BANK_QUOTATION = 500.00
INVOICE_PREFIXES = {1: "KM", 2: "VA"}
GST_RATE_CALC = 0.00
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
        sh = gspread_client.open(spreadsheet_title)
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
    
def get_max_accessory_invoice_number(df_sales_records: pd.DataFrame, firm_id: int) -> int:
    """Finds the maximum sequential invoice number used for a given firm ID from Sales_Records."""
    
    if firm_id == 1:
        inv_col = 'Acc_Inv_1_No'
        start_seq = 1000 # Base for KM series
    elif firm_id == 2:
        inv_col = 'Acc_Inv_2_No'
        start_seq = 2000 # Base for VA series
    else:
        return 0

    if inv_col not in df_sales_records.columns:
        return start_seq

    # Ensure column is numeric and find max
    df_sales_records[inv_col] = pd.to_numeric(df_sales_records[inv_col], errors='coerce')
    max_inv = df_sales_records[inv_col].max()
    
    # If no valid records found, return the base start sequence + 1
    return int(max_inv) if not pd.isna(max_inv) and max_inv >= start_seq else start_seq

def generate_accessory_invoice_number(df_sales_records: pd.DataFrame, firm_id: int) -> Tuple[str, int]:
    """
    Generates the next sequential accessory invoice number using the Sales_Records DF.
    """
    prefix = INVOICE_PREFIXES.get(firm_id, "UNK") 
    
    # Get the max number from the appropriate column
    max_inv_no = get_max_accessory_invoice_number(df_sales_records, firm_id)

    # Start sequence based on max number found
    sequential_part = max_inv_no + 1
    
    return f"{prefix}-{sequential_part}", sequential_part

def process_accessories_and_split(model_id: str, accessory_bom_df: pd.DataFrame, firm_master_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Performs VLOOKUP, splits accessories between two firms (1-4 vs 5+), 
    and calculates final bill structures for each firm.
    Returns: List of bill dictionaries
    """
    
    model_id = str(model_id).strip()
    package_row = accessory_bom_df[accessory_bom_df['Model_ID'] == model_id]

    if package_row.empty:
        return []

    accessories_list_firm_1 = [] 
    accessories_list_firm_2 = [] 
    subtotal_firm_1 = 0.0
    subtotal_firm_2 = 0.0

    for i in range(1, 11): 
        acc_name_col = str(i)
        acc_price_col = f'{i} PRICE'
        
        if acc_name_col in package_row.columns and acc_price_col in package_row.columns:
            acc_name_series = package_row[acc_name_col].iloc[0]
            acc_price_series = package_row[acc_price_col].iloc[0]
            
            if pd.isna(acc_name_series) or not str(acc_name_series).strip():
                continue 

            acc_name = str(acc_name_series).strip()
            
            try:
                # FIX: Ensure we are operating on a clean string before converting to float
                clean_price_str = str(acc_price_series).strip() 
                acc_price = float(clean_price_str) 
            except (ValueError, TypeError):
                # If conversion fails (e.g., blank cell, NaN), treat as 0.0
                acc_price = 0.0
                
                
            if acc_price > 0:
                acc_qty = 1 
                acc_total = acc_qty * acc_price
                
                accessory_data = {'name': acc_name, 'qty': acc_qty, 'price': acc_price, 'total': acc_total}

                if i <= 4:
                    accessories_list_firm_1.append(accessory_data)
                    subtotal_firm_1 += acc_total
                else: 
                    accessories_list_firm_2.append(accessory_data)
                    subtotal_firm_2 += acc_total

    # CALCULATE TAXES AND TOTALS
    tax_amount_1 = subtotal_firm_1 * GST_RATE_CALC
    grand_total_1 = subtotal_firm_1 + tax_amount_1
    tax_amount_2 = subtotal_firm_2 * GST_RATE_CALC
    grand_total_2 = subtotal_firm_2 + tax_amount_2
    
    bills_to_print = []

    # Prepare Firm 1 Bill
    if grand_total_1 > 0:
        firm_1_details = firm_master_df[firm_master_df['Firm_ID'] == '1'].iloc[0].to_dict()
        bills_to_print.append({
            'firm_id': 1,
            'firm_details': firm_1_details,
            'accessories': accessories_list_firm_1,
            'subtotal': subtotal_firm_1,
            'tax': tax_amount_1,
            'grand_total': grand_total_1
        })
    
    # Prepare Firm 2 Bill
    if grand_total_2 > 0:
        firm_2_details = firm_master_df[firm_master_df['Firm_ID'] == '2'].iloc[0].to_dict()
        bills_to_print.append({
            'firm_id': 2,
            'firm_details': firm_2_details,
            'accessories': accessories_list_firm_2,
            'subtotal': subtotal_firm_2,
            'tax': tax_amount_2,
            'grand_total': grand_total_2
        })

    return bills_to_print

def generate_accessory_bills(model_id: str, accessory_bom_df: pd.DataFrame, firm_master_df: pd.DataFrame, sales_records_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Orchestrates the accessory billing process: splits accessories, generates 
    sequential invoice numbers, and logs the sequence numbers to Sales_Records.
    
    Returns: A list of prepared bill dictionaries with final invoice numbers.
    """
    
    # 1. Split the accessories based on the Model ID
    bills_to_print = process_accessories_and_split(model_id, accessory_bom_df, firm_master_df)

    if not bills_to_print:
        return []

    # Prepare a list to hold the final sequential numbers (for saving to Sales_Records)
    new_log_entries = []
    
    # Determine the current max invoice number BEFORE processing the sale
    df_sales_records_copy = sales_records_df.copy()

    for bill in bills_to_print:
        firm_id = bill['firm_id']
        
        # 2. Generate the sequential invoice number based on current max log
        acc_inv_no_prefixed, acc_inv_seq = generate_accessory_invoice_number(df_sales_records_copy, firm_id)
        
        # Update the bill structure with the final number for the PDF
        bill['Invoice_No'] = acc_inv_no_prefixed
        bill['Acc_Inv_Seq'] = acc_inv_seq # Store the sequential part for final export

        # 3. Prepare the log entry for sequence update (needed for the next sale)
        # Note: Since the sequence numbers are only logged once the sale is confirmed,
        # we prepare the log data to be appended to the Sales_Records sheet later.
        
    return bills_to_print