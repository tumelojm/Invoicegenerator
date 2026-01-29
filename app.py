from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
import os
from datetime import datetime

app = Flask(__name__)

# Create a directory for generated invoices
INVOICE_DIR = 'generated_invoices'
if not os.path.exists(INVOICE_DIR):
    os.makedirs(INVOICE_DIR)

def generate_corrected_invoice(invoice_details, output_filename):
    """Generate PDF invoice from invoice details"""
    filepath = os.path.join(INVOICE_DIR, output_filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()

    # Page Margins
    left_margin = 50
    right_margin = 50
    table_width = width - left_margin - right_margin

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, height - 50, "INVOICE")
    c.setFont("Helvetica", 12)
    c.drawString(left_margin, height - 70, f"Invoice Number: {invoice_details['invoice_number']}")
    c.drawString(left_margin, height - 90, f"Issued on: {invoice_details['issue_date']}")
    c.drawString(left_margin, height - 110, f"Due by: {invoice_details['due_date']}")

    # Divider Line
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.line(left_margin, height - 120, width - right_margin, height - 120)

    # From and To Sections
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, height - 150, "From:")
    c.drawString(width / 2, height - 150, "To:")
    c.setFont("Helvetica", 12)

    y_from = height - 170
    for line in invoice_details['from']:
        c.drawString(left_margin, y_from, line)
        y_from -= 15

    y_to = height - 170
    for line in invoice_details['to']:
        c.drawString(width / 2, y_to, line)
        y_to -= 15

    # Services Table
    y_table_start = min(y_from, y_to) - 90
    data = [["Product", "Qty", "Unit Price", "Tax", "Total"]]

    for service, details in invoice_details['services'].items():
        description = "<br/>".join(details['description'])
        data.append([Paragraph(f"<b>{service}</b><br/>{description}", styles["Normal"]),
                     details['quantity'],
                     f"R {details['unit_price']:.2f}",
                     f"R {details['tax']:.2f}",
                     f"R {details['total']:.2f}"])

    column_widths = [table_width * 0.4, table_width * 0.12, table_width * 0.16, table_width * 0.16, table_width * 0.16]

    table = Table(data, colWidths=column_widths, rowHeights=[None] + [40] * (len(data) - 1))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, left_margin, y_table_start)

    # Totals Section
    y_totals = y_table_start - (len(data) * 20) - 40
    summary_width = 200
    summary_x = width - right_margin - summary_width

    c.setFillColor(colors.lightgrey)
    c.rect(350, y_totals - 60, 180, 75, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(summary_x + 10, y_totals + 20, "Invoice Summary")

    c.setFont("Helvetica", 12)
    c.drawString(summary_x + 10, y_totals, "Subtotal")
    c.drawString(summary_x + 120, y_totals, f"R {invoice_details['subtotal']:.2f}")

    c.drawString(summary_x + 10, y_totals - 20, "Tax")
    c.drawString(summary_x + 120, y_totals - 20, f"R {invoice_details['tax']:.2f}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(summary_x + 10, y_totals - 40, "Total")
    c.drawString(summary_x + 120, y_totals - 40, f"R {invoice_details['total']:.2f}")

    # Bank Details
    y_bank = y_totals - 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y_bank, "Bank Details:")
    c.setFont("Helvetica", 12)
    y_bank -= 20

    for line in invoice_details['bank_details']:
        c.drawString(left_margin, y_bank, line)
        y_bank -= 15

    # Footer
    y_bank -= 30
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(left_margin, y_bank, "Thank you for your business!")

    c.save()
    return filepath

@app.route('/')
def index():
    """Display the invoice form"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate invoice from form data"""
    try:
        data = request.json
        
        # Parse services
        services = {}
        for service in data['services']:
            services[service['name']] = {
                'description': service['description'].split('\n'),
                'quantity': int(service['quantity']),
                'unit_price': float(service['unit_price']),
                'tax': float(service['tax']),
                'total': float(service['total'])
            }
        
        invoice_details = {
            'invoice_number': data['invoice_number'],
            'issue_date': data['issue_date'],
            'due_date': data['due_date'],
            'from': data['from_details'].split('\n'),
            'to': data['to_details'].split('\n'),
            'services': services,
            'subtotal': float(data['subtotal']),
            'tax': float(data['tax']),
            'total': float(data['total']),
            'bank_details': data['bank_details'].split('\n')
        }
        
        filename = f"Invoice-{data['invoice_number']}.pdf"
        filepath = generate_corrected_invoice(invoice_details, filename)
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/download/<filename>')
def download(filename):
    """Download generated invoice"""
    filepath = os.path.join(INVOICE_DIR, filename)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
