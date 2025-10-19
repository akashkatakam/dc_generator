# In order.py

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

class SalesOrder:
    # (The existing __init__ and set_finance_details methods remain here)

    def __init__(self, customer_name, place, phone, vehicle_details, final_cost_by_staff, sales_staff, financier_name):
        # ... (Existing code) ...
        
        # New fields:
        self.sales_staff = sales_staff
        self.financier_name = financier_name    
        self.customer_name = customer_name
        self.place = place
        self.phone = phone
        
        # Vehicle Details
        self.vehicle = vehicle_details
        self.sale_price = vehicle_details["ex_showroom_price"] + vehicle_details["tax"]
        
        # Finance Details (Initialized to None)
        self.sale_type = "Cash"
        self.dd_amount = None
        self.down_payment = None
        self.remaining_finance_amount = 0

    def set_finance_details(self, dd_amount, down_payment):
        """Sets the details for a financed vehicle."""
        self.sale_type = "Finance"
        self.dd_amount = dd_amount
        self.down_payment = down_payment
        # Ensure remaining_finance_amount is calculated
        self.remaining_finance_amount = self.sale_price - dd_amount - down_payment
    
    # --- NEW PDF GENERATION METHOD ---
    def generate_pdf_challan(self, filename="Delivery_Challan.pdf"):
        """Generates the Delivery Challan as a PDF file."""
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter # Standard 8.5 x 11 inches
        
        x_margin = inch
        y_cursor = height - inch

        # --- Title and Header ---
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x_margin, y_cursor, "DELIVERY CHALLAN / ORDER FORM")
        y_cursor -= 0.5 * inch
        
        c.line(x_margin, y_cursor, width - x_margin, y_cursor)
        y_cursor -= 0.25 * inch

        # --- Customer Details ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "CUSTOMER DETAILS")
        y_cursor -= 0.25 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"Name: {self.customer_name}")
        c.drawString(x_margin + 3.5*inch, y_cursor, f"Phone: {self.phone}")
        y_cursor -= 0.2 * inch
        c.drawString(x_margin, y_cursor, f"Place: {self.place}")
        y_cursor -= 0.5 * inch

        # --- Vehicle Details (Using a simple table structure) ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "VEHICLE AND PRICING DETAILS")
        y_cursor -= 0.25 * inch

        c.setFont("Helvetica", 10)
        
        # Define columns: Label, Value
        data = [
            ("Model:", self.vehicle.get('model', 'N/A')),
            ("Color:", self.vehicle.get('color', 'N/A')),
            ("Ex-Showroom Price:", f"${self.vehicle.get('ex_showroom_price', 0):,.2f}"),
            ("Taxes/RTO:", f"${self.vehicle.get('tax', 0):,.2f}"),
        ]
        
        # Draw the table details
        row_height = 0.2 * inch
        for label, value in data:
            c.drawString(x_margin, y_cursor, label)
            c.drawString(x_margin + 1.5 * inch, y_cursor, value)
            y_cursor -= row_height

        # --- Total Price ---
        y_cursor -= 0.1 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "TOTAL PRICE:")
        c.drawString(x_margin + 1.5 * inch, y_cursor, f"${self.sale_price:,.2f}")
        y_cursor -= 0.5 * inch
        
        # --- Payment Details ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_cursor, "PAYMENT METHOD & BREAKDOWN")
        y_cursor -= 0.25 * inch
        
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y_cursor, f"Sale Type: {self.sale_type}")
        y_cursor -= 0.2 * inch

        if self.sale_type == "Finance":
            c.drawString(x_margin, y_cursor, f"DD Amount: ${self.dd_amount:,.2f}")
            y_cursor -= 0.2 * inch
            c.drawString(x_margin, y_cursor, f"Down Payment: ${self.down_payment:,.2f}")
            y_cursor -= 0.2 * inch
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_margin, y_cursor, f"Financed Amount:")
            c.drawString(x_margin + 1.5 * inch, y_cursor, f"${self.remaining_finance_amount:,.2f}")
        else:
            c.drawString(x_margin, y_cursor, f"Full Cash Payment Received: ${self.sale_price:,.2f}")


        # --- Save the PDF ---
        c.showPage()
        c.save()
        return filename