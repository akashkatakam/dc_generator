# In order.py

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import red, black, green
import pandas as pd

class SalesOrder:
    def __init__(self, customer_name, place, phone, vehicle_details, final_cost_by_staff, 
                 sales_staff, financier_name, executive_name, vehicle_color_name, 
                 hp_fee_to_charge, incentive_earned, banker_name=""):
        
        # Customer and Staff Details
        self.customer_name = customer_name
        self.place = place
        self.phone = phone
        self.sales_staff = sales_staff
        self.banker_name = banker_name
        
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

    def set_finance_details(self, dd_amount, down_payment):
        """Sets the details for a financed vehicle."""
        self.sale_type = "Finance"
        self.dd_amount = dd_amount
        self.down_payment = down_payment
        
        # Total cost includes Vehicle Cost + HP Fee + Incentive (if collected)
        total_customer_cost = self.final_cost + self.hp_fee + self.incentive_earned
        
        self.remaining_finance_amount = total_customer_cost - dd_amount - down_payment

    def get_data_for_export(self):
        """Returns a flat dictionary of all transaction data for storage."""
        data = {
            # --- Transaction Metadata ---
            'Timestamp': pd.Timestamp('now').strftime('%Y-%m-%d %H:%M:%S'),
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
            'Amount_Financed': self.remaining_finance_amount
        }
        return data

    def generate_pdf_challan(self, filename="Delivery_Challan.pdf"):
        """Generates the Delivery Challan as a PDF file."""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        x_margin = inch
        x_center = width / 2.0
        y_cursor = height - inch
        row_height = 0.2 * inch

        # --- Title and Header ---
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(x_center, y_cursor, "DELIVERY CHALLAN / ORDER FORM")
        y_cursor -= 0.3 * inch
        c.line(x_margin, y_cursor, width - x_margin, y_cursor)
        y_cursor -= 0.3 * inch

        # --- 1. General Details Block ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "1. GENERAL DETAILS")
        y_cursor -= 0.2 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"Order Date: {pd.Timestamp('today').strftime('%Y-%m-%d')}")
        c.drawString(x_margin + 3.5*inch, y_cursor, f"Sales Staff: {self.sales_staff}")
        y_cursor -= row_height
        c.drawString(x_margin, y_cursor, f"Customer Name: {self.customer_name}")
        c.drawString(x_margin + 3.5*inch, y_cursor, f"Phone: {self.phone}")
        y_cursor -= row_height
        c.drawString(x_margin, y_cursor, f"Place/City: {self.place}")
        y_cursor -= 0.5 * inch

        # --- 2. Vehicle Details Block ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "2. VEHICLE & SPECIFICATION DETAILS")
        y_cursor -= 0.2 * inch

        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, "Model:")
        c.drawString(x_margin + 1.5 * inch, y_cursor, self.vehicle.get('model', 'N/A'))
        y_cursor -= row_height
        
        c.drawString(x_margin, y_cursor, "Variant/Trim:")
        c.drawString(x_margin + 1.5 * inch, y_cursor, self.vehicle.get('color', 'N/A'))
        y_cursor -= row_height
        
        c.drawString(x_margin, y_cursor, "Paint Color:")
        c.drawString(x_margin + 1.5 * inch, y_cursor, self.vehicle_color_name)
        y_cursor -= 0.5 * inch

        # --- 3. Pricing Breakdown ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "3. PRICING BREAKDOWN")
        y_cursor -= 0.2 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, "On-Road Price (ORP) Component:")
        c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.orp_price:,.2f}")
        y_cursor -= row_height
        
        c.drawString(x_margin, y_cursor, "Additional Fees/Taxes Component:")
        c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.tax_component:,.2f}")
        y_cursor -= row_height
        
        c.line(x_margin + 2.5 * inch, y_cursor + 0.05 * inch, x_margin + 4 * inch, y_cursor + 0.05 * inch)
        y_cursor -= 0.1 * inch
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y_cursor, "TOTAL PRICE:")
        c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.listed_price:,.2f}")
        y_cursor -= 0.3 * inch

        # Discount Line
        c.setFillColor(red)
        c.drawString(x_margin, y_cursor, "Discount / Adjustment:")
        c.drawString(x_margin + 2.5 * inch, y_cursor, f"- {self.discount:,.2f}")
        c.setFillColor(black)
        y_cursor -= 0.3 * inch
        
        # Final Negotiated Cost
        c.line(x_margin, y_cursor + 0.05 * inch, width - x_margin, y_cursor + 0.05 * inch) 
        y_cursor -= 0.1 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "FINAL VEHICLE COST:")
        c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.final_cost:,.2f}")
        y_cursor -= 0.5 * inch

        # --- 4. ADDITIONAL CHARGES (CONSOLIDATED) ---
        charge_index = 4
        total_additional_finance_charges = self.hp_fee + self.incentive_earned
        
        if total_additional_finance_charges > 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_cursor, f"{charge_index}. ADDITIONAL FINANCE PROCESSING CHARGES")
            y_cursor -= 0.2 * inch
            
            c.setFont("Helvetica", 10)
            c.drawString(x_margin, y_cursor, "Total Finance Processing Charges:")
            c.drawString(x_margin + 2.5 * inch, y_cursor, f"{total_additional_finance_charges:,.2f}")
            y_cursor -= 0.3 * inch
            
            charge_index += 1
        
        # --- 5. PAYMENT & FINANCE BREAKDOWN ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, f"{charge_index}. PAYMENT & FINANCE BREAKDOWN")
        y_cursor -= 0.2 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"Sale Type: {self.sale_type}")
        y_cursor -= row_height

        if self.sale_type == "Finance":
            c.drawString(x_margin, y_cursor, f"Financier Company: {self.financier_name}")
            
            if self.banker_name:
                c.drawString(x_margin + 3.5*inch, y_cursor, f"Banker (Quote): {self.banker_name}")
            else:
                c.drawString(x_margin + 3.5*inch, y_cursor, f"Finance Executive: {self.executive_name}")
            
            y_cursor -= row_height
            
            c.drawString(x_margin, y_cursor, f"DD / Booking Amount Paid:")
            c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.dd_amount:,.2f}")
            y_cursor -= row_height

            c.drawString(x_margin, y_cursor, f"Down Payment Amount to be Paid:")
            c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.down_payment:,.2f}")
            y_cursor -= 0.3 * inch
            
            
            # --- INTERNAL NOTE: DEALERSHIP EARNINGS ---
            if self.incentive_earned > 0 and self.financier_name != 'Bank':
                y_cursor -= 0.5 * inch
                c.setFont("Helvetica-Bold", 10)
                c.setFillColor(green)
                c.drawString(x_margin, y_cursor, f"*** DEALERSHIP EARNINGS (Internal Note): ***")
                y_cursor -= row_height
                c.drawString(x_margin, y_cursor, f"Finance Incentive Earned:")
                c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.incentive_earned:,.2f}")
                c.setFillColor(black)
                y_cursor -= 0.3 * inch
            
        else: # Cash Sale
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_cursor, f"Total Cash Payment Received:")
            c.drawString(x_margin + 2.5 * inch, y_cursor, f"{self.final_cost:,.2f}")

        # --- Footer Signatures ---
        y_cursor = 2 * inch 
        c.line(x_margin, y_cursor, x_margin + 2 * inch, y_cursor)
        c.drawCentredString(x_margin + inch, y_cursor - 0.2 * inch, "Customer Signature")

        c.line(width - x_margin - 2 * inch, y_cursor, width - x_margin, y_cursor)
        c.drawCentredString(width - x_margin - inch, y_cursor - 0.2 * inch, "Staff Signature")

        c.save()
        return filename