from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
import os
from io import BytesIO

app = Flask(__name__)

INVOICE_DIR = 'generated_invoices'
os.makedirs(INVOICE_DIR, exist_ok=True)

INK        = colors.HexColor('#0D0D0D')
ACCENT     = colors.HexColor('#1A3A5C')
ACCENT_LT  = colors.HexColor('#E8EFF6')
RULE       = colors.HexColor('#2E6DA4')
MID_GREY   = colors.HexColor('#6B7280')
LIGHT_GREY = colors.HexColor('#F3F4F6')
WHITE      = colors.white


def _styles():
    base = getSampleStyleSheet()
    def S(name, **kw):
        d = dict(fontName='Helvetica', fontSize=10, leading=14,
                 textColor=INK, spaceAfter=0, spaceBefore=0)
        d.update(kw)
        return ParagraphStyle(name, parent=base['Normal'], **d)
    return {
        'doc_type':    S('doc_type',  fontName='Helvetica-Bold', fontSize=28, textColor=ACCENT, leading=32),
        'meta_label':  S('meta_label', fontName='Helvetica-Bold', fontSize=7.5, textColor=MID_GREY, leading=10),
        'meta_value':  S('meta_value', fontSize=9.5, leading=13),
        'party_label': S('party_label', fontName='Helvetica-Bold', fontSize=7.5, textColor=RULE, leading=10),
        'party_name':  S('party_name', fontName='Helvetica-Bold', fontSize=11, leading=14),
        'party_body':  S('party_body', fontSize=9, textColor=MID_GREY, leading=13),
        'th':          S('th', fontName='Helvetica-Bold', fontSize=8.5, textColor=WHITE, leading=11),
        'td_main':     S('td_main', fontName='Helvetica-Bold', fontSize=9.5, leading=13),
        'td_desc':     S('td_desc', fontSize=8, textColor=MID_GREY, leading=11),
        'td_num':      S('td_num', fontSize=9.5, leading=13, alignment=TA_RIGHT),
        'total_label': S('total_label', fontSize=9.5, textColor=MID_GREY, leading=13, alignment=TA_RIGHT),
        'total_value': S('total_value', fontSize=9.5, leading=13, alignment=TA_RIGHT),
        'grand_label': S('grand_label', fontName='Helvetica-Bold', fontSize=11, textColor=WHITE, leading=14, alignment=TA_RIGHT),
        'grand_value': S('grand_value', fontName='Helvetica-Bold', fontSize=11, textColor=WHITE, leading=14, alignment=TA_RIGHT),
        'bank_label':  S('bank_label', fontName='Helvetica-Bold', fontSize=7.5, textColor=RULE, leading=10),
        'bank_body':   S('bank_body', fontSize=9, leading=14),
        'note_body':   S('note_body', fontName='Helvetica-Oblique', fontSize=9, textColor=MID_GREY, leading=13),
        'addon_label': S('addon_label', fontName='Helvetica-Bold', fontSize=7.5, textColor=RULE, leading=10),
        'addon_item':  S('addon_item', fontSize=9, textColor=MID_GREY, leading=13),
        'footer':      S('footer', fontSize=7.5, textColor=MID_GREY, leading=10, alignment=TA_CENTER),
    }


def _fmt_zar(amount):
    return f"R {amount:,.2f}"

def _fmt_hrs(h):
    return f"{h:.1f} hrs"


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, doc_type='INVOICE', doc_number='', **kwargs):
        super().__init__(*args, **kwargs)
        self._doc_type   = doc_type
        self._doc_number = doc_number
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._decorate(i + 1, n)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _decorate(self, page_num, total):
        w, h = A4
        self.setFillColor(ACCENT)
        self.rect(0, h - 6*mm, w, 6*mm, fill=1, stroke=0)
        self.setStrokeColor(ACCENT_LT)
        self.setLineWidth(0.5)
        self.line(15*mm, 14*mm, w - 15*mm, 14*mm)
        self.setFillColor(MID_GREY)
        self.setFont('Helvetica', 7)
        self.drawString(15*mm, 9*mm, f"{self._doc_type}  |  {self._doc_number}")
        self.drawRightString(w - 15*mm, 9*mm, f"Page {page_num} of {total}")


def generate_pdf(inv, is_quote=False, billing_mode='standard'):
    buf       = BytesIO()
    doc_type  = 'QUOTE' if is_quote else 'INVOICE'
    is_hourly = billing_mode == 'hourly'

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=18*mm, bottomMargin=22*mm,
        title=f"{doc_type} {inv['doc_number']}",
        author=inv['from'][0] if inv.get('from') else '',
    )

    st    = _styles()
    w     = A4[0] - 30*mm
    half  = w / 2
    story = []

    # Header
    meta_rows = [
        [Paragraph(f"<b>{'Quote' if is_quote else 'Invoice'} No.</b>", st['meta_label']),
         Paragraph(inv['doc_number'], st['meta_value'])],
        [Paragraph('<b>Issue Date</b>', st['meta_label']),
         Paragraph(inv['issue_date'], st['meta_value'])],
        [Paragraph('<b>Due Date</b>', st['meta_label']),
         Paragraph(inv['due_date'], st['meta_value'])],
    ]
    if inv.get('payment_terms'):
        meta_rows.append([Paragraph('<b>Payment Terms</b>', st['meta_label']),
                          Paragraph(inv['payment_terms'], st['meta_value'])])
    if is_hourly and inv.get('default_rate'):
        meta_rows.append([Paragraph('<b>Standard Rate</b>', st['meta_label']),
                          Paragraph(f"R {inv['default_rate']:.0f}/hr", st['meta_value'])])

    meta_tbl = Table(meta_rows, colWidths=[30*mm, 55*mm])
    meta_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    header_tbl = Table([[Paragraph(doc_type, st['doc_type']), meta_tbl]],
                       colWidths=[w - 90*mm, 90*mm])
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width='100%', thickness=2, color=RULE, spaceAfter=4*mm))

    # From / To
    def party_block(label, lines):
        parts = [Paragraph(label.upper(), st['party_label']), Spacer(1, 1*mm)]
        for i, line in enumerate(lines):
            parts.append(Paragraph(line, st['party_name'] if i == 0 else st['party_body']))
        return parts

    party_tbl = Table(
        [[party_block('From', inv.get('from', [])), party_block('Bill To', inv.get('to', []))]],
        colWidths=[half, half],
    )
    party_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LINEAFTER', (0,0), (0,-1), 0.5, ACCENT_LT),
        ('LEFTPADDING', (1,0), (1,-1), 12),
    ]))
    story.append(party_tbl)
    story.append(Spacer(1, 6*mm))

    # Services table
    has_tax = inv.get('tax', 0) > 0

    if is_hourly:
        if has_tax:
            col_w      = [w*0.38, w*0.10, w*0.13, w*0.13, w*0.13, w*0.13]
            header_row = [Paragraph('DESCRIPTION', st['th']), Paragraph('HOURS', st['th']),
                          Paragraph('RATE/HR', st['th']), Paragraph('EXCL. VAT', st['th']),
                          Paragraph('VAT', st['th']), Paragraph('TOTAL', st['th'])]
        else:
            col_w      = [w*0.40, w*0.12, w*0.16, w*0.16, w*0.16]
            header_row = [Paragraph('DESCRIPTION', st['th']), Paragraph('HOURS', st['th']),
                          Paragraph('RATE/HR', st['th']), Paragraph('SUBTOTAL', st['th']),
                          Paragraph('TOTAL', st['th'])]
    else:
        if has_tax:
            col_w      = [w*0.38, w*0.10, w*0.14, w*0.12, w*0.13, w*0.13]
            header_row = [Paragraph('DESCRIPTION', st['th']), Paragraph('QTY', st['th']),
                          Paragraph('UNIT PRICE', st['th']), Paragraph('EXCL. VAT', st['th']),
                          Paragraph('VAT', st['th']), Paragraph('TOTAL', st['th'])]
        else:
            col_w      = [w*0.42, w*0.12, w*0.23, w*0.23]
            header_row = [Paragraph('DESCRIPTION', st['th']), Paragraph('QTY', st['th']),
                          Paragraph('UNIT PRICE', st['th']), Paragraph('TOTAL', st['th'])]

    rows = [header_row]
    for svc in inv.get('services', []):
        desc_parts = [Paragraph(svc['name'], st['td_main'])]
        for d in (svc.get('description') or []):
            if d.strip():
                desc_parts.append(Paragraph(d, st['td_desc']))
        if is_hourly:
            hours    = svc.get('hours', 0)
            rate     = svc.get('rate', 0)
            excl_vat = hours * rate
            if has_tax:
                rows.append([desc_parts, Paragraph(_fmt_hrs(hours), st['td_num']),
                             Paragraph(_fmt_zar(rate), st['td_num']),
                             Paragraph(_fmt_zar(excl_vat), st['td_num']),
                             Paragraph(_fmt_zar(svc['tax']), st['td_num']),
                             Paragraph(_fmt_zar(svc['total']), st['td_num'])])
            else:
                rows.append([desc_parts, Paragraph(_fmt_hrs(hours), st['td_num']),
                             Paragraph(_fmt_zar(rate), st['td_num']),
                             Paragraph(_fmt_zar(excl_vat), st['td_num']),
                             Paragraph(_fmt_zar(svc['total']), st['td_num'])])
        else:
            excl_vat = svc['unit_price'] * svc['quantity']
            if has_tax:
                rows.append([desc_parts, Paragraph(str(svc['quantity']), st['td_num']),
                             Paragraph(_fmt_zar(svc['unit_price']), st['td_num']),
                             Paragraph(_fmt_zar(excl_vat), st['td_num']),
                             Paragraph(_fmt_zar(svc['tax']), st['td_num']),
                             Paragraph(_fmt_zar(svc['total']), st['td_num'])])
            else:
                rows.append([desc_parts, Paragraph(str(svc['quantity']), st['td_num']),
                             Paragraph(_fmt_zar(svc['unit_price']), st['td_num']),
                             Paragraph(_fmt_zar(svc['total']), st['td_num'])])

    svc_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    svc_tbl.setStyle(TableStyle([
        ('BACKGROUND',     (0,0),  (-1,0),           ACCENT),
        ('ROWBACKGROUNDS', (0,1),  (-1,len(rows)-1), [WHITE, LIGHT_GREY]),
        ('GRID',           (0,0),  (-1,-1),           0.4, colors.HexColor('#D1D5DB')),
        ('LINEBELOW',      (0,0),  (-1,0),            1.5, RULE),
        ('VALIGN',         (0,0),  (-1,-1),           'MIDDLE'),
        ('TOPPADDING',     (0,0),  (-1,-1),           5),
        ('BOTTOMPADDING',  (0,0),  (-1,-1),           5),
        ('LEFTPADDING',    (0,0),  (-1,-1),           6),
        ('RIGHTPADDING',   (0,0),  (-1,-1),           6),
    ]))
    story.append(svc_tbl)
    story.append(Spacer(1, 5*mm))

    # Totals
    totals_rows = []
    if is_hourly and inv.get('total_hours'):
        totals_rows.append([
            Paragraph(f"Total: {inv['total_hours']:.1f} hrs @ R{inv.get('default_rate',0):.0f}/hr", st['total_label']),
            Paragraph('', st['total_value']),
        ])
    if has_tax:
        totals_rows += [
            [Paragraph('Subtotal (Excl. VAT)', st['total_label']),
             Paragraph(_fmt_zar(inv['subtotal']), st['total_value'])],
            [Paragraph('VAT', st['total_label']),
             Paragraph(_fmt_zar(inv['tax']), st['total_value'])],
        ]
    else:
        totals_rows.append([
            Paragraph('Subtotal', st['total_label']),
            Paragraph(_fmt_zar(inv['subtotal']), st['total_value']),
        ])
    totals_inner = Table(totals_rows, colWidths=[50*mm, 35*mm])
    totals_inner.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    grand_inner = Table([[Paragraph('TOTAL DUE', st['grand_label']),
                          Paragraph(_fmt_zar(inv['total']), st['grand_value'])]],
                        colWidths=[50*mm, 35*mm])
    grand_inner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))

    totals_col = Table([[totals_inner], [Spacer(1, 2*mm)], [grand_inner]], colWidths=[85*mm])
    totals_col.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    left_parts = []
    if inv.get('bank_details'):
        left_parts.append(Paragraph('BANKING DETAILS', st['bank_label']))
        left_parts.append(Spacer(1, 1.5*mm))
        for line in inv['bank_details']:
            if line.strip():
                left_parts.append(Paragraph(line, st['bank_body']))
    if inv.get('notes'):
        if left_parts:
            left_parts.append(Spacer(1, 3*mm))
        left_parts.append(Paragraph('NOTES', st['bank_label']))
        left_parts.append(Spacer(1, 1.5*mm))
        left_parts.append(Paragraph(inv['notes'], st['note_body']))

    bottom_tbl = Table([[left_parts or [''], totals_col]], colWidths=[w - 90*mm, 90*mm])
    bottom_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(KeepTogether(bottom_tbl))

    # Optional add-ons
    if inv.get('addons', '').strip():
        story.append(Spacer(1, 6*mm))
        story.append(HRFlowable(width='100%', thickness=0.5, color=ACCENT_LT, spaceAfter=4*mm))
        story.append(Paragraph('OPTIONAL ADD-ONS / NOT INCLUDED', st['addon_label']))
        story.append(Spacer(1, 2*mm))
        for line in inv['addons'].split('\n'):
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", st['addon_item']))

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=ACCENT_LT))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        'Thank you for your business. Please reference the invoice number in your payment.',
        st['footer']
    ))

    def make_canvas(filename, **kwargs):
        return NumberedCanvas(filename, pagesize=A4,
                               doc_type=doc_type, doc_number=inv['doc_number'])

    doc.build(story, canvasmaker=make_canvas)
    buf.seek(0)
    return buf.read()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data         = request.json
        is_quote     = data.get('is_quote', False)
        billing_mode = data.get('billing_mode', 'standard')
        is_hourly    = billing_mode == 'hourly'

        services = []
        for svc in data['services']:
            if is_hourly:
                hours = float(svc.get('hours', 0))
                rate  = float(svc.get('rate', data.get('default_rate', 0)))
                tax   = float(svc.get('tax', 0))
                services.append({
                    'name':        svc['name'],
                    'description': svc.get('description', '').split('\n'),
                    'hours':       hours,
                    'rate':        rate,
                    'tax':         tax,
                    'total':       hours * rate + tax,
                })
            else:
                qty   = float(svc.get('quantity', 0))
                price = float(svc.get('unit_price', 0))
                tax   = float(svc.get('tax', 0))
                services.append({
                    'name':        svc['name'],
                    'description': svc.get('description', '').split('\n'),
                    'quantity':    qty,
                    'unit_price':  price,
                    'tax':         tax,
                    'total':       qty * price + tax,
                })

        if is_hourly:
            subtotal    = sum(s['hours'] * s['rate'] for s in services)
            total_hours = sum(s['hours'] for s in services)
        else:
            subtotal    = sum(s['quantity'] * s['unit_price'] for s in services)
            total_hours = None

        total_tax = sum(s['tax'] for s in services)

        inv = {
            'doc_number':    data['invoice_number'],
            'issue_date':    data['issue_date'],
            'due_date':      data['due_date'],
            'payment_terms': data.get('payment_terms', ''),
            'from':          [l for l in data['from_details'].split('\n') if l.strip()],
            'to':            [l for l in data['to_details'].split('\n') if l.strip()],
            'services':      services,
            'subtotal':      subtotal,
            'tax':           total_tax,
            'total':         subtotal + total_tax,
            'total_hours':   total_hours,
            'default_rate':  float(data.get('default_rate', 0)) if is_hourly else None,
            'bank_details':  [l for l in data.get('bank_details', '').split('\n') if l.strip()],
            'notes':         data.get('notes', ''),
            'addons':        data.get('addons', ''),
        }

        pdf_bytes = generate_pdf(inv, is_quote=is_quote, billing_mode=billing_mode)
        prefix    = 'Quote' if is_quote else 'Invoice'
        filename  = f"{prefix}-{inv['doc_number']}.pdf"

        with open(os.path.join(INVOICE_DIR, filename), 'wb') as f:
            f.write(pdf_bytes)

        return jsonify({
            'success':     True,
            'filename':    filename,
            'total_hours': total_hours,
            'subtotal':    subtotal,
            'tax':         total_tax,
            'total':       subtotal + total_tax,
        })

    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e),
                        'trace': traceback.format_exc()}), 400


@app.route('/download/<filename>')
def download(filename):
    filepath = os.path.join(INVOICE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True,
                     download_name=filename, mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)))