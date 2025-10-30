# order.py

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.colors import red, black, green
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime
import pytz

# --- CONFIGURATION (Assumed to be available via import or scope) ---
GST_RATE_DISPLAY = 18 
LINE_HEIGHT = 13 # Standard line height for accessory bill PDF
IST_TIMEZONE = pytz.timezone('Asia/Kolkata')

# --- SalesOrder Class ---

class SalesOrder:
    def __init__(self, customer_name, place, phone, vehicle_details, final_cost_by_staff, 
                 sales_staff, financier_name, executive_name, vehicle_color_name, 
                 hp_fee_to_charge, incentive_earned, banker_name="", dc_number="N/A",
                 accessory_bills: List[Dict[str, Any]] = None, bill_1_inv_seq: int = 0, bill_2_inv_seq: int = 0):
        
        # Customer and Staff Details
        self.customer_name = customer_name
        self.place = place
        self.phone = phone
        self.sales_staff = sales_staff
        self.banker_name = banker_name
        self.dc_number = dc_number
        
        # Vehicle Pricing Details 
        self.vehicle = vehicle_details
        self.listed_price = vehicle_details["total_price"]
        self.orp_price = vehicle_details["orp"] 
        self.tax_component = vehicle_details["tax"] 

        # Negotiated Details
        self.final_cost = final_cost_by_staff
        self.discount = self.listed_price - final_cost_by_staff
        self.vehicle_color_name = vehicle_color_name
        
        # Finance Details
        self.sale_type = "Cash"
        self.financier_name = financier_name
        self.executive_name = executive_name
        self.incentive_earned = incentive_earned 
        self.hp_fee = hp_fee_to_charge          
        self.dd_amount = 0.0
        self.down_payment = 0.0
        self.remaining_finance_amount = 0.0
        
        # Accessory Billing Data
        self.accessory_bills = accessory_bills if accessory_bills is not None else []
        self.bill_1_inv_seq = bill_1_inv_seq
        self.bill_2_inv_seq = bill_2_inv_seq
        
    def set_finance_details(self, dd_amount, down_payment):
        """Sets the details for a financed vehicle."""
        self.sale_type = "Finance"
        self.dd_amount = dd_amount
        self.down_payment = down_payment
        
        total_customer_cost = self.final_cost + self.hp_fee + self.incentive_earned
        
        self.remaining_finance_amount = total_customer_cost - dd_amount - down_payment

    def get_data_for_export(self, bill_1_inv_seq: int, bill_2_inv_seq: int) -> Dict[str, Any]:
        """Returns a flat dictionary of all transaction data for storage."""
        now_ist = datetime.now(IST_TIMEZONE)
        
        # 2. Format the IST time for the log
        ist_timestamp_str = now_ist.strftime('%Y-%m-%d')
        data = {
            # --- Transaction Metadata ---
            'Timestamp': ist_timestamp_str,
            'DC_Number': self.dc_number,
            'Sales_Staff': self.sales_staff,
            'Financier_Company': self.financier_name,
            'Finance_Executive': self.executive_name,
            'Banker_Name': self.banker_name if self.banker_name else '',
            'Sale_Type': self.sale_type,
            
            # --- Customer Data ---
            'Customer_Name': self.customer_name,
            'Phone_Number': self.phone,
            'Place': self.place,
            
            # --- Vehicle Data ---
            'Model': self.vehicle.get('model'),
            'Variant': self.vehicle.get('color'),
            'Paint_Color': self.vehicle_color_name,
            
            # --- Financials ---
            'Price_ORP': self.orp_price,
            'Price_Listed_Total': self.listed_price,
            'Price_Negotiated_Final': self.final_cost,
            'Discount_Given': self.discount,
            'Charge_HP_Fee': self.hp_fee,
            'Charge_Incentive': self.incentive_earned,
            'Payment_DD': self.dd_amount,
            'Payment_DownPayment': self.down_payment,
            
            # --- Accessory Invoice Numbers (For Auditing) ---
            'Acc_Inv_1_No': bill_1_inv_seq,
            'Acc_Inv_2_No': bill_2_inv_seq
        }
        return data

    def generate_pdf_challan(self, filename="Order_Bill_Combined.pdf"):
        """Generates a single PDF file containing the DC Order (Page 1) and Accessory Bills (Page 2+)."""
        
        # Use letter size for the primary DC page, but A4 for general use
        current_date = datetime.now(IST_TIMEZONE).strftime("%d-%m-%Y")
        c = canvas.Canvas(filename, pagesize=letter) 
        width_l, height_l = letter
        A4_W, A4_H = A4
        MARGIN = 50

        # =========================================================================
        # PAGE 1: PRIMARY DELIVERY CHALLAN (VEHICLE & FINANCE SUMMARY)
        # =========================================================================
        
        x_margin = inch
        x_center = width_l / 2.0
        x_col_split = x_margin + 3.5 * inch
        y_cursor = height_l - inch
        row_height = 0.2 * inch
        
        # --- Title and Header ---
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x_margin, y_cursor, "DELIVERY CHALLAN")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(width_l - x_margin - 2*inch , y_cursor, f"DATE: {current_date}")
        y_cursor -= 0.3 * inch
        c.line(x_margin, y_cursor, width_l - x_margin, y_cursor)
        y_cursor -= 0.3 * inch
        
        # --- 1. General & Vehicle Details (Merged Two-Column Block) ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "1. GENERAL & VEHICLE DETAILS")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(width_l - x_margin - 2*inch, y_cursor, f"DC NO: {self.dc_number}")
        
        y_cursor -= 0.25 * inch

        c.setFont("Helvetica", 10)
        
        # Left Column (Customer/Staff)
        y_col_start = y_cursor
        c.drawString(x_margin, y_cursor, f"Customer: {self.customer_name}")
        y_cursor -= row_height
        c.drawString(x_margin, y_cursor, f"Phone: {self.phone} (Place: {self.place})")
        y_cursor -= row_height
        c.drawString(x_margin, y_cursor, f"Sales Staff: {self.sales_staff}")
        
        # Right Column (Vehicle Specifics)
        y_cursor = y_col_start # Reset cursor for right column
        c.drawString(x_col_split, y_cursor, f"Model: {self.vehicle.get('model', 'N/A')}")
        y_cursor -= row_height
        c.drawString(x_col_split, y_cursor, f"Variant/Trim: {self.vehicle.get('color', 'N/A')}")
        y_cursor -= row_height
        c.drawString(x_col_split, y_cursor, f"Paint Color: {self.vehicle_color_name}")
        
        y_cursor -= 0.5 * inch # Advance cursor past the tallest column

        # --- 2. Pricing Breakdown ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "2. PRICING BREAKDOWN")
        y_cursor -= 0.2 * inch
        
        c.setFont("Helvetica", 10)
        x_price_col = x_margin + 3.5 * inch
        
        c.drawString(x_margin, y_cursor, "On-Road Price (ORP):")
        c.drawString(x_price_col, y_cursor, f"Rs.{self.orp_price:,.2f}")
        y_cursor -= row_height
        
        c.drawString(x_margin, y_cursor, "ACC and others:")
        c.drawString(x_price_col, y_cursor, f"Rs.{self.tax_component:,.2f}")
        y_cursor -= row_height
        
        c.line(x_price_col, y_cursor + 0.05 * inch, x_price_col + 1.5 * inch, y_cursor + 0.05 * inch)
        y_cursor -= 0.1 * inch
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y_cursor, "TOTAL PRICE:")
        c.drawString(x_price_col, y_cursor, f"Rs.{self.listed_price:,.2f}")
        y_cursor -= 0.3 * inch

        # Discount Line
        c.setFillColor(red)
        c.drawString(x_margin, y_cursor, "Discount / Adjustment:")
        c.drawString(x_price_col, y_cursor, f"- Rs.{self.discount:,.2f}")
        c.setFillColor(black)
        y_cursor -= 0.3 * inch
        
        # Final Negotiated Cost
        c.line(x_margin, y_cursor + 0.05 * inch, width_l - x_margin, y_cursor + 0.05 * inch) 
        y_cursor -= 0.3 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "FINAL VEHICLE COST:")
        c.drawString(x_price_col, y_cursor, f"Rs.{self.final_cost:,.2f}")
        y_cursor -= 0.5 * inch

        # --- 3. ADDITIONAL CHARGES & FINANCE BREAKDOWN ---
        total_additional_finance_charges = self.hp_fee + self.incentive_earned
        charge_index = 3 

        # A. Additional Charges
        if total_additional_finance_charges > 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_cursor, f"{charge_index}. ADDITIONAL FINANCE PROCESSING CHARGES")
            y_cursor -= 0.2 * inch
            
            c.setFont("Helvetica", 10)
            c.drawString(x_margin, y_cursor, "Total Finance Processing Charges:")
            c.drawString(x_price_col, y_cursor, f"Rs.{total_additional_finance_charges:,.2f}")
            y_cursor -= 0.3 * inch
            charge_index += 1
        
        # B. Payment & Finance Breakdown
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, f"{charge_index}. PAYMENT & FINANCE BREAKDOWN")
        y_cursor -= 0.2 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"Sale Type: {self.sale_type}")
        y_cursor -= row_height

        if self.sale_type == "Finance":
            c.drawString(x_margin, y_cursor, f"Financier Company: {self.financier_name}")
            
            if self.banker_name:
                c.drawString(x_col_split, y_cursor, f"Banker (Quote): {self.banker_name}")
            else:
                c.drawString(x_col_split, y_cursor, f"Finance Executive: {self.executive_name}")
            
            y_cursor -= row_height
            
            c.drawString(x_margin, y_cursor, f"DD / Booking Amount Paid:")
            c.drawString(x_price_col, y_cursor, f"Rs.{self.dd_amount:,.2f}")
            y_cursor -= row_height

            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_cursor, "Down Payment Amount Paid:")
            c.drawString(x_price_col, y_cursor, f"Rs.{self.down_payment:,.2f}")
        
        else: # Cash Sale
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_cursor, f"Total Cash Payment Received:")
            c.drawString(x_price_col, y_cursor, f"Rs.{self.final_cost:,.2f}")
            y_cursor -= 0.3 * inch

        # --- Summary Block ---
        y_cursor = 4 * inch 
        c.line(x_margin, y_cursor, width_l - x_margin, y_cursor) 
        y_cursor -= 0.2 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "Delivery challan (CUSTOMER COPY)")
        y_cursor -= 0.2 * inch

        # Left Column (Vehicle Summary)
        c.setFont("Helvetica", 12)
        c.drawString(x_margin, y_cursor, f"Customer Name: {self.customer_name}")
        y_cursor -= row_height
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"DC No.: {self.dc_number}")
        y_cursor -= row_height
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y_cursor, f"Model/Color: {self.vehicle.get('model')} {self.vehicle.get('color')} ({self.vehicle_color_name})")
        y_cursor -= row_height
        
        # Right Column (Payment Summary)
        summary_y_cursor = 3.6 * inch 
        c.setFont("Helvetica", 10)
        c.drawString(x_col_split, summary_y_cursor, f"Sale Type: {self.sale_type}")
        summary_y_cursor -= row_height
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_col_split, summary_y_cursor, f"Finance name: Rs.{self.financier_name:,.2f}")
        summary_y_cursor -= row_height



        # --- Footer Signatures ---
        y_cursor = 2 * inch 
        c.line(x_margin, y_cursor, x_margin + 2 * inch, y_cursor)
        c.drawCentredString(x_margin + inch, y_cursor - 0.2 * inch, "Customer Signature")

        c.line(width_l - x_margin - 2 * inch, y_cursor, width_l - x_margin, y_cursor)
        c.drawCentredString(width_l - x_margin - inch, y_cursor - 0.2 * inch, "Staff Signature")


        # =========================================================================
        # PAGE 2 onwards: ACCESSORY BILLS (DUAL COPIES)
        # =========================================================================

        for bill in self.accessory_bills:
            c.showPage() # Start a new page for each accessory firm
            
            # --- Set Page Size to A4 for the Accessory Bill Layout ---
            c.setPageSize(A4) 
            
            A4_H = A4[1]
            
            # 1. Compile final invoice data dictionary for accessory bill
            # Determine invoice number based on stored sequential part
            if bill['firm_id'] == 1:
                acc_inv_seq = self.bill_1_inv_seq
            else:
                acc_inv_seq = self.bill_2_inv_seq
            
            
            invoice_data = {
                'Invoice_No': f"{acc_inv_seq}", 
                'Date': current_date,
                'Customer_Name': self.customer_name,
                'Customer_Phone': self.phone, 
                'Accessories': bill['accessories'],
                'Grand_Total': bill['grand_total'],
            }

            # Draw Original Copy (Top Half)
            draw_bill_content(c, invoice_data, bill['firm_details'], A4_H - MARGIN, "ORIGINAL (Customer Copy)",self.vehicle.get('model'))
            
            # Draw Duplicate Copy (Bottom Half)
            draw_bill_content(c, invoice_data, bill['firm_details'], (A4_H / 2) - 30, "DUPLICATE (Office Copy)",self.vehicle.get('model'))
            
            # Add Cut Line
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.setDash(3, 3) 
            c.line(MARGIN, A4_H / 2, A4_W - MARGIN, A4_H / 2)


        c.save()
        return filename

# --- UTILITY FUNCTION FOR PDF DRAWING (Accessory Bill) ---
def draw_bill_content(c, invoice_data, firm_details, y_start, copy_text, model_name="N/A",LINE_HEIGHT=13):
    """Draws the entire bill content relative to the y_start position."""
    width, height = A4
    MARGIN = 50
    y_pos = y_start

    # 0. COPY LABEL
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 150, y_pos, copy_text)
    y_pos -= LINE_HEIGHT

    # 1. FIRM HEADER
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, y_pos, firm_details.get('Firm_Name', 'N/A'))
    y_pos -= LINE_HEIGHT
    
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, y_pos, firm_details.get('Firm_Address', 'N/A'))
    y_pos -= LINE_HEIGHT
    c.drawString(MARGIN, y_pos, f"GSTIN: {firm_details.get('Firm_GSTIN', 'N/A')}")

    # 2. INVOICE HEADER 
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 150, y_pos + (2 * LINE_HEIGHT), "TAX INVOICE")
    c.drawString(width - 150, y_pos + LINE_HEIGHT, f"INVOICE NO: {invoice_data['Invoice_No']}")
    c.drawString(width - 150, y_pos, f"DATE: {invoice_data['Date']}")
    
    # 3. Customer Info 
    y_pos -= (3 * LINE_HEIGHT)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN, y_pos, f"Customer Name: {invoice_data['Customer_Name']}")
    y_pos -= LINE_HEIGHT
    c.drawString(MARGIN, y_pos, f"Customer Phone: {invoice_data['Customer_Phone']}")
    y_pos -= LINE_HEIGHT
    c.drawString(MARGIN, y_pos, f"Vehicle Model: {model_name}")
    
    # 4. ITEM TABLE HEADER
    y_pos -= (2 * LINE_HEIGHT)
    c.setFont("Helvetica-Bold", 10)
    col_x = [MARGIN, MARGIN + 50, MARGIN + 300, MARGIN + 400, width - 100]
    c.drawString(col_x[0], y_pos, "S.No.")
    c.drawString(col_x[1], y_pos, "ACCESSORY NAME")
    c.drawString(col_x[3], y_pos, "QTY") 
    c.drawString(col_x[4], y_pos, "PRICE")

    # Draw a line below header
    c.line(MARGIN, y_pos - 3, width - MARGIN, y_pos - 3)

    # 5. ITEM LIST
    c.setFont("Helvetica", 9)
    y_pos -= (1.5 * LINE_HEIGHT)
    
    for i, item in enumerate(invoice_data['Accessories']):
        if not item.get('name') or item.get('price', 0) == 0:
            continue
            
        c.drawString(col_x[0], y_pos, str(i + 1))
        c.drawString(col_x[1], y_pos, str(item['name']))
        c.drawString(col_x[3], y_pos, f"1")
        c.drawString(col_x[4], y_pos, f"Rs.{item['price']:.2f}")
        y_pos -= LINE_HEIGHT

    # 6. SUMMARY & SIGNATURE BLOCK
    y_summary_start = y_start - 300 
    
    # GRAND TOTAL
    c.setFont("Helvetica-Bold", 12)
    c.drawString(width - 200, y_summary_start - LINE_HEIGHT, "GRAND TOTAL:")
    c.drawString(width - 100, y_summary_start - LINE_HEIGHT, f"Rs.{invoice_data['Grand_Total']:.2f}")

    # GST TEXT 
    c.setFont("Helvetica", 8)
    c.drawString(width - 200, y_summary_start - (2.5 * LINE_HEIGHT), f"GST @ {GST_RATE_DISPLAY}% is included in the price.")