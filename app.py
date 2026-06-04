from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import json
from datetime import datetime
from io import BytesIO

app = Flask(__name__)

INVOICE_DIR = 'generated_invoices'
os.makedirs(INVOICE_DIR, exist_ok=True)

# ─── Colour palette ───────────────────────────────────────────────────────────
INK        = colors.HexColor('#0D0D0D')
ACCENT     = colors.HexColor('#1A3A5C')   # deep navy
ACCENT_LT  = colors.HexColor('#E8EFF6')   # pale blue tint
RULE       = colors.HexColor('#2E6DA4')   # mid-blue rule
MID_GREY   = colors.HexColor('#6B7280')
LIGHT_GREY = colors.HexColor('#F3F4F6')
WHITE      = colors.white
RED_ACCENT = colors.HexColor('#C0392B')   # for "QUOTE" stamp on quotes


def _styles():
    base = getSampleStyleSheet()

    def S(name, **kw):
        defaults = dict(fontName='Helvetica', fontSize=10, leading=14,
                        textColor=INK, spaceAfter=0, spaceBefore=0)
        defaults.update(kw)
        return ParagraphStyle(name, parent=base['Normal'], **defaults)

    return {
        'doc_type':    S('doc_type',  fontName='Helvetica-Bold', fontSize=28,
                         textColor=ACCENT, leading=32),
        'meta_label':  S('meta_label', fontName='Helvetica-Bold', fontSize=7.5,
                         textColor=MID_GREY, leading=10),
        'meta_value':  S('meta_value', fontName='Helvetica', fontSize=9.5,
                         textColor=INK, leading=13),
        'party_label': S('party_label', fontName='Helvetica-Bold', fontSize=7.5,
                         textColor=RULE, leading=10),
        'party_name':  S('party_name', fontName='Helvetica-Bold', fontSize=11,
                         textColor=INK, leading=14),
        'party_body':  S('party_body', fontName='Helvetica', fontSize=9,
                         textColor=MID_GREY, leading=13),
        'th':          S('th', fontName='Helvetica-Bold', fontSize=8.5,
                         textColor=WHITE, leading=11),
        'td_main':     S('td_main', fontName='Helvetica-Bold', fontSize=9.5,
                         textColor=INK, leading=13),
        'td_desc':     S('td_desc', fontName='Helvetica', fontSize=8,
                         textColor=MID_GREY, leading=11),
        'td_num':      S('td_num', fontName='Helvetica', fontSize=9.5,
                         textColor=INK, leading=13, alignment=TA_RIGHT),
        'total_label': S('total_label', fontName='Helvetica', fontSize=9.5,
                         textColor=MID_GREY, leading=13, alignment=TA_RIGHT),
        'total_value': S('total_value', fontName='Helvetica', fontSize=9.5,
                         textColor=INK, leading=13, alignment=TA_RIGHT),
        'grand_label': S('grand_label', fontName='Helvetica-Bold', fontSize=11,
                         textColor=WHITE, leading=14, alignment=TA_RIGHT),
        'grand_value': S('grand_value', fontName='Helvetica-Bold', fontSize=11,
                         textColor=WHITE, leading=14, alignment=TA_RIGHT),
        'bank_label':  S('bank_label', fontName='Helvetica-Bold', fontSize=7.5,
                         textColor=RULE, leading=10),
        'bank_body':   S('bank_body', fontName='Helvetica', fontSize=9,
                         textColor=INK, leading=14),
        'note_body':   S('note_body', fontName='Helvetica-Oblique', fontSize=9,
                         textColor=MID_GREY, leading=13),
        'footer':      S('footer', fontName='Helvetica', fontSize=7.5,
                         textColor=MID_GREY, leading=10, alignment=TA_CENTER),
        'status_due':  S('status_due', fontName='Helvetica-Bold', fontSize=8,
                         textColor=WHITE, leading=10, alignment=TA_CENTER),
    }


def _fmt_zar(amount):
    """Format amount as South African Rand."""
    return f"R {amount:,.2f}"


class NumberedCanvas(canvas.Canvas):
    """Canvas that adds page numbers and a subtle header rule on every page."""

    def __init__(self, *args, doc_type="INVOICE", doc_number="", **kwargs):
        super().__init__(*args, **kwargs)
        self._doc_type   = doc_type
        self._doc_number = doc_number
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_page_decorations(i + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_page_decorations(self, page_num, total_pages):
        w, h = A4
        # Top accent bar
        self.setFillColor(ACCENT)
        self.rect(0, h - 6*mm, w, 6*mm, fill=1, stroke=0)

        # Bottom rule + footer text
        self.setStrokeColor(ACCENT_LT)
        self.setLineWidth(0.5)
        self.line(15*mm, 14*mm, w - 15*mm, 14*mm)

        self.setFillColor(MID_GREY)
        self.setFont('Helvetica', 7)
        footer_left = f"{self._doc_type}  |  {self._doc_number}"
        self.drawString(15*mm, 9*mm, footer_left)
        self.drawRightString(w - 15*mm, 9*mm,
                             f"Page {page_num} of {total_pages}")


def generate_pdf(inv, is_quote=False):
    """
    Build a professional invoice / quote PDF and return raw bytes.
    """
    buf = BytesIO()
    doc_type = "QUOTE" if is_quote else "INVOICE"

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=18*mm, bottomMargin=22*mm,
        title=f"{doc_type} {inv['doc_number']}",
        author=inv['from'][0] if inv.get('from') else '',
    )

    st   = _styles()
    w    = A4[0] - 30*mm      # usable width
    half = w / 2
    story = []

    # ── 1. HEADER ROW: doc-type  +  meta-info ────────────────────────────────
    meta_rows = [
        [Paragraph(f"<b>{'Quote' if is_quote else 'Invoice'} No.</b>", st['meta_label']),
         Paragraph(inv['doc_number'], st['meta_value'])],
        [Paragraph("<b>Issue Date</b>", st['meta_label']),
         Paragraph(inv['issue_date'], st['meta_value'])],
        [Paragraph("<b>Due Date</b>", st['meta_label']),
         Paragraph(inv['due_date'], st['meta_value'])],
    ]
    if inv.get('payment_terms'):
        meta_rows.append([
            Paragraph("<b>Payment Terms</b>", st['meta_label']),
            Paragraph(inv['payment_terms'], st['meta_value']),
        ])

    meta_tbl = Table(meta_rows, colWidths=[30*mm, 55*mm])
    meta_tbl.setStyle(TableStyle([
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING',(0,0), (-1,-1), 4),
        ('TOPPADDING',  (0,0), (-1,-1), 2),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
    ]))

    header_tbl = Table(
        [[Paragraph(doc_type, st['doc_type']), meta_tbl]],
        colWidths=[w - 90*mm, 90*mm],
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING',(0,0), (-1,-1), 0),
        ('TOPPADDING',  (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width='100%', thickness=2, color=RULE, spaceAfter=4*mm))

    # ── 2. FROM / TO ─────────────────────────────────────────────────────────
    def party_block(label, lines):
        parts = [Paragraph(label.upper(), st['party_label']),
                 Spacer(1, 1*mm)]
        for i, line in enumerate(lines):
            s = st['party_name'] if i == 0 else st['party_body']
            parts.append(Paragraph(line, s))
        return parts

    from_parts = party_block("From", inv.get('from', []))
    to_parts   = party_block("Bill To", inv.get('to', []))

    party_tbl = Table(
        [[from_parts, to_parts]],
        colWidths=[half, half],
    )
    party_tbl.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
        ('LINEAFTER',    (0,0), (0,-1),  0.5, ACCENT_LT),
        ('LEFTPADDING',  (1,0), (1,-1),  12),
    ]))
    story.append(party_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 3. SERVICES TABLE ────────────────────────────────────────────────────
    col_w = [w*0.40, w*0.10, w*0.14, w*0.12, w*0.12, w*0.12]

    header_row = [
        Paragraph("DESCRIPTION",  st['th']),
        Paragraph("QTY",          st['th']),
        Paragraph("UNIT PRICE",   st['th']),
        Paragraph("EXCL. VAT",    st['th']),
        Paragraph("VAT",          st['th']),
        Paragraph("TOTAL",        st['th']),
    ]

    rows = [header_row]
    for svc in inv.get('services', []):
        desc_parts = [Paragraph(svc['name'], st['td_main'])]
        for d in (svc.get('description') or []):
            if d.strip():
                desc_parts.append(Paragraph(d, st['td_desc']))
        excl_vat = svc['unit_price'] * svc['quantity']
        rows.append([
            desc_parts,
            Paragraph(str(svc['quantity']),            st['td_num']),
            Paragraph(_fmt_zar(svc['unit_price']),     st['td_num']),
            Paragraph(_fmt_zar(excl_vat),              st['td_num']),
            Paragraph(_fmt_zar(svc['tax']),            st['td_num']),
            Paragraph(_fmt_zar(svc['total']),          st['td_num']),
        ])

    svc_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    row_count = len(rows)
    svc_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),          ACCENT),
        ('ROWBACKGROUNDS',(0, 1), (-1, row_count-1), [WHITE, LIGHT_GREY]),
        ('GRID',          (0, 0), (-1, -1),          0.4, colors.HexColor('#D1D5DB')),
        ('LINEBELOW',     (0, 0), (-1, 0),           1.5, RULE),
        ('VALIGN',        (0, 0), (-1, -1),          'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, 0),           5),
        ('BOTTOMPADDING', (0, 0), (-1, 0),           5),
        ('TOPPADDING',    (0, 1), (-1, -1),          5),
        ('BOTTOMPADDING', (0, 1), (-1, -1),          5),
        ('LEFTPADDING',   (0, 0), (-1, -1),          6),
        ('RIGHTPADDING',  (0, 0), (-1, -1),          6),
    ]))
    story.append(svc_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 4. TOTALS + BANK DETAILS ─────────────────────────────────────────────
    totals_data = [
        [Paragraph("Subtotal (Excl. VAT)", st['total_label']),
         Paragraph(_fmt_zar(inv['subtotal']),  st['total_value'])],
        [Paragraph("VAT",                  st['total_label']),
         Paragraph(_fmt_zar(inv['tax']),       st['total_value'])],
    ]
    totals_inner = Table(totals_data, colWidths=[50*mm, 35*mm])
    totals_inner.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))

    grand_data = [[
        Paragraph("TOTAL DUE", st['grand_label']),
        Paragraph(_fmt_zar(inv['total']),   st['grand_value']),
    ]]
    grand_inner = Table(grand_data, colWidths=[50*mm, 35*mm])
    grand_inner.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), ACCENT),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [3]),
    ]))

    totals_stack = [[totals_inner], [Spacer(1, 2*mm)], [grand_inner]]
    totals_col   = Table(totals_stack, colWidths=[85*mm])
    totals_col.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
    ]))

    bank_parts = []
    if inv.get('bank_details'):
        bank_parts.append(Paragraph("BANKING DETAILS", st['bank_label']))
        bank_parts.append(Spacer(1, 1.5*mm))
        for line in inv['bank_details']:
            if line.strip():
                bank_parts.append(Paragraph(line, st['bank_body']))
    if inv.get('notes'):
        if bank_parts:
            bank_parts.append(Spacer(1, 3*mm))
        bank_parts.append(Paragraph("NOTES", st['bank_label']))
        bank_parts.append(Spacer(1, 1.5*mm))
        bank_parts.append(Paragraph(inv['notes'], st['note_body']))

    bottom_tbl = Table(
        [[bank_parts or [''], totals_col]],
        colWidths=[w - 90*mm, 90*mm],
    )
    bottom_tbl.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
        ('ALIGN',        (1,0), (1,-1),  'RIGHT'),
    ]))
    story.append(KeepTogether(bottom_tbl))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=ACCENT_LT))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Thank you for your business. Please reference the invoice number in your payment.",
        st['footer']
    ))

    # ── Build (Fixed signature with context forwarding) ─────────────────────
    def make_canvas(filename, **kwargs):
        kwargs.update({
            'doc_type': doc_type,
            'doc_number': inv['doc_number']
        })
        return NumberedCanvas(filename, **kwargs)

    doc.build(story, canvasmaker=make_canvas)
    buf.seek(0)
    return buf.read()


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        is_quote = data.get('is_quote', False)

        services = []
        for svc in data['services']:
            qty   = float(svc['quantity'])
            price = float(svc['unit_price'])
            tax   = float(svc.get('tax', 0))
            services.append({
                'name':        svc['name'],
                'description': svc.get('description', '').split('\n'),
                'quantity':    qty,
                'unit_price':  price,
                'tax':         tax,
                'total':       qty * price + tax,
            })

        subtotal = sum(s['quantity'] * s['unit_price'] for s in services)
        total_tax = sum(s['tax'] for s in services)
        total = subtotal + total_tax

        inv = {
            'doc_number':     data['invoice_number'],
            'issue_date':     data['issue_date'],
            'due_date':       data['due_date'],
            'payment_terms':  data.get('payment_terms', ''),
            'from':           [l for l in data['from_details'].split('\n') if l.strip()],
            'to':             [l for l in data['to_details'].split('\n') if l.strip()],
            'services':       services,
            'subtotal':       float(data.get('subtotal', subtotal)),
            'tax':            float(data.get('tax', total_tax)),
            'total':          float(data.get('total', total)),
            'bank_details':   [l for l in data.get('bank_details', '').split('\n') if l.strip()],
            'notes':          data.get('notes', ''),
        }

        pdf_bytes = generate_pdf(inv, is_quote=is_quote)
        prefix    = "Quote" if is_quote else "Invoice"
        filename  = f"{prefix}-{inv['doc_number']}.pdf"
        filepath  = os.path.join(INVOICE_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)

        return jsonify({'success': True, 'filename': filename})

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
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))