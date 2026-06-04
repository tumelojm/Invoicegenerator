from flask import Flask, render_template_string, request, send_file, jsonify
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

# ── HTML Template (embedded) ────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Invoice & Quote Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --navy:   #1A3A5C;
  --blue:   #2E6DA4;
  --blue-lt:#E8EFF6;
  --ink:    #0D0D0D;
  --mid:    #6B7280;
  --border: #E5E7EB;
  --surface:#F9FAFB;
  --white:  #FFFFFF;
  --green:  #059669;
  --red:    #DC2626;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.05);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'DM Sans', sans-serif;
  background: #F1F4F8;
  color: var(--ink);
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.6;
}

/* ── Layout ── */
.app-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: auto 1fr;
  min-height: 100vh;
}
.topbar {
  grid-column: 1 / -1;
  background: var(--navy);
  color: white;
  padding: 0 28px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.topbar-brand {
  display: flex; align-items: center; gap: 10px;
  font-weight: 600; font-size: 15px; letter-spacing: .02em;
}
.topbar-brand svg { opacity: .9; }
.topbar-actions { display: flex; gap: 10px; align-items: center; }

.sidebar {
  background: var(--white);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  position: sticky;
  top: 0;
  height: calc(100vh - 56px);
  overflow-y: auto;
}
.sidebar-section { padding: 0 16px 8px; }
.sidebar-label {
  font-size: 10px; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: var(--mid);
  padding: 8px 10px 4px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: 8px; cursor: pointer;
  font-size: 13.5px; color: var(--ink);
  transition: background .15s;
}
.nav-item:hover { background: var(--surface); }
.nav-item.active { background: var(--blue-lt); color: var(--blue); font-weight: 500; }
.nav-item svg { flex-shrink: 0; opacity: .7; }
.nav-item.active svg { opacity: 1; }

.main {
  padding: 32px 36px;
  overflow-y: auto;
}

/* ── Page header ── */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 28px;
}
.page-title { font-size: 22px; font-weight: 600; letter-spacing: -.02em; }
.page-subtitle { font-size: 13px; color: var(--mid); margin-top: 2px; }

/* ── Doc-type toggle ── */
.doc-toggle {
  display: inline-flex;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--white);
}
.doc-toggle input { display: none; }
.doc-toggle label {
  padding: 8px 22px;
  font-size: 13px; font-weight: 500;
  cursor: pointer; transition: background .15s, color .15s;
  color: var(--mid);
}
.doc-toggle input:checked + label {
  background: var(--navy); color: white;
}

/* ── Card sections ── */
.card {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.card-title {
  font-size: 13px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .08em; color: var(--navy);
  display: flex; align-items: center; gap: 8px;
}
.card-title svg { color: var(--blue); }

/* ── Form grid ── */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 20px; }
.form-grid.three { grid-template-columns: 1fr 1fr 1fr; }
.form-span2 { grid-column: span 2; }

.field { display: flex; flex-direction: column; gap: 5px; }
.field label {
  font-size: 11px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--mid);
}
.field input, .field textarea, .field select {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 12px;
  font-family: inherit; font-size: 13.5px;
  background: var(--white); color: var(--ink);
  transition: border-color .15s, box-shadow .15s;
  outline: none;
}
.field input:focus, .field textarea:focus, .field select:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(46,109,164,.12);
}
.field textarea { resize: vertical; min-height: 72px; }
.field-mono input { font-family: 'DM Mono', monospace; font-size: 13px; }

/* ── Services table ── */
.services-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 12px;
}
.services-table th {
  background: var(--navy); color: white;
  padding: 9px 10px; text-align: left;
  font-size: 10.5px; font-weight: 600;
  letter-spacing: .07em; text-transform: uppercase;
}
.services-table th:first-child { border-radius: 8px 0 0 8px; }
.services-table th:last-child  { border-radius: 0 8px 8px 0; }
.services-table td {
  padding: 0;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.services-table tr:last-child td { border-bottom: none; }
.services-table td input, .services-table td textarea {
  border: none; outline: none; width: 100%;
  padding: 9px 10px; font-family: inherit; font-size: 13px;
  background: transparent; color: var(--ink);
}
.services-table td textarea { resize: none; min-height: 36px; }
.services-table td input:focus, .services-table td textarea:focus {
  background: var(--blue-lt);
}
.services-table tr:hover td { background: #FAFBFF; }
.services-table tr:hover td input, .services-table tr:hover td textarea { background: #FAFBFF; }
.services-table .num-col { text-align: right; }
.services-table .num-col input { text-align: right; }
.services-table .del-col { width: 36px; text-align: center; }
.del-btn {
  background: none; border: none; cursor: pointer;
  color: #D1D5DB; padding: 8px 6px;
  transition: color .15s;
  display: flex; align-items: center;
}
.del-btn:hover { color: var(--red); }

/* ── Totals ── */
.totals-panel {
  display: flex; justify-content: flex-end;
}
.totals-box {
  width: 300px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.totals-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 13.5px;
}
.totals-row:last-child { border-bottom: none; }
.totals-row .lbl { color: var(--mid); }
.totals-row .val { font-family: 'DM Mono', monospace; font-size: 13px; }
.totals-row.grand {
  background: var(--navy); color: white;
  font-weight: 600;
}
.totals-row.grand .val { font-size: 14px; }

/* ── Buttons ── */
.btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 18px; border-radius: 8px;
  font-family: inherit; font-size: 13px; font-weight: 500;
  cursor: pointer; border: 1.5px solid transparent;
  transition: all .15s; white-space: nowrap;
}
.btn-primary { background: var(--navy); color: white; }
.btn-primary:hover { background: #142D4A; }
.btn-secondary { background: var(--white); color: var(--ink); border-color: var(--border); }
.btn-secondary:hover { background: var(--surface); }
.btn-blue { background: var(--blue); color: white; }
.btn-blue:hover { background: #265d8f; }
.btn-ghost { background: none; color: var(--blue); border-color: var(--blue-lt); }
.btn-ghost:hover { background: var(--blue-lt); }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-icon { padding: 8px; border-radius: 8px; }
.btn[disabled] { opacity: .5; cursor: not-allowed; }

/* ── Status badge ── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 600;
}
.badge-blue  { background: var(--blue-lt); color: var(--blue); }
.badge-green { background: #D1FAE5; color: #065F46; }
.badge-amber { background: #FEF3C7; color: #92400E; }

/* ── Toast ── */
.toast-wrap {
  position: fixed; bottom: 28px; right: 28px; z-index: 999;
  display: flex; flex-direction: column; gap: 8px;
  pointer-events: none;
}
.toast {
  background: var(--ink); color: white;
  padding: 12px 18px; border-radius: 10px;
  font-size: 13.5px; display: flex; align-items: center; gap: 10px;
  box-shadow: 0 4px 20px rgba(0,0,0,.25);
  pointer-events: auto;
  animation: toastIn .25s ease;
}
.toast.success { background: #064E3B; }
.toast.error   { background: #7F1D1D; }
@keyframes toastIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* ── Loading overlay ── */
.loading-overlay {
  display: none;
  position: fixed; inset: 0;
  background: rgba(255,255,255,.65);
  z-index: 500;
  align-items: center; justify-content: center;
  flex-direction: column; gap: 14px;
}
.loading-overlay.active { display: flex; }
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 13px; color: var(--mid); }

/* ── Misc ── */
.divider { height: 1px; background: var(--border); margin: 8px 0 20px; }
.vat-hint { font-size: 11px; color: var(--mid); margin-top: 3px; }
.add-row-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0;
}
.section-sep { margin: 0 0 20px; }
</style>
</head>
<body>

<div class="app-shell">

  <!-- Topbar -->
  <header class="topbar">
    <div class="topbar-brand">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
      </svg>
      InvoicePro
    </div>
    <div class="topbar-actions">
      <span class="badge badge-blue">South Africa · ZAR</span>
    </div>
  </header>

  <!-- Sidebar -->
  <nav class="sidebar">
    <div class="sidebar-label">Create</div>
    <div class="sidebar-section">
      <div class="nav-item active" onclick="showPage('create')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        New Document
      </div>
    </div>
    <div class="sidebar-label">History</div>
    <div class="sidebar-section">
      <div class="nav-item" id="nav-history" onclick="showPage('history')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Recent Documents
      </div>
    </div>
    <div class="sidebar-label" style="margin-top:16px">Saved Info</div>
    <div class="sidebar-section">
      <div class="nav-item" onclick="showPage('settings')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
        Business Profile
      </div>
    </div>
  </nav>

  <!-- Main -->
  <main class="main" id="page-create">

    <div class="page-header">
      <div>
        <div class="page-title">New Document</div>
        <div class="page-subtitle">Create a professional invoice or quote in seconds</div>
      </div>
      <div style="display:flex;gap:10px;align-items:center">
        <div class="doc-toggle">
          <input type="radio" name="doctype" id="dt-invoice" value="invoice" checked>
          <label for="dt-invoice">Invoice</label>
          <input type="radio" name="doctype" id="dt-quote" value="quote">
          <label for="dt-quote">Quote</label>
        </div>
        <button class="btn btn-primary" onclick="generateDoc()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Generate PDF
        </button>
      </div>
    </div>

    <!-- Doc Meta -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          Document Details
        </div>
      </div>
      <div class="form-grid three">
        <div class="field field-mono">
          <label>Document Number</label>
          <input type="text" id="doc_number" value="INV-2025-001" placeholder="INV-2025-001">
        </div>
        <div class="field">
          <label>Issue Date</label>
          <input type="date" id="issue_date">
        </div>
        <div class="field">
          <label>Due Date</label>
          <input type="date" id="due_date">
        </div>
        <div class="field">
          <label>Payment Terms</label>
          <select id="payment_terms">
            <option value="Net 30">Net 30 days</option>
            <option value="Net 14">Net 14 days</option>
            <option value="Net 7">Net 7 days</option>
            <option value="Due on receipt">Due on receipt</option>
            <option value="COD">COD</option>
          </select>
        </div>
        <div class="field">
          <label>VAT Rate</label>
          <select id="vat_rate" onchange="recalcAll()">
            <option value="0.15" selected>15% (Standard)</option>
            <option value="0">0% (Zero-rated)</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <div class="field field-mono" id="custom-vat-field" style="display:none">
          <label>Custom VAT %</label>
          <input type="number" id="custom_vat" value="15" min="0" max="100" step="0.5" onchange="recalcAll()">
        </div>
      </div>
    </div>

    <!-- From / To -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          Parties
        </div>
        <button class="btn btn-ghost btn-sm" onclick="loadProfile()">Load saved profile</button>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>From (Your Business)</label>
          <textarea id="from_details" rows="5" placeholder="Company Name&#10;123 Business Street&#10;Johannesburg, 2001&#10;VAT No: 4123456789&#10;info@company.co.za"></textarea>
        </div>
        <div class="field">
          <label>Bill To (Client)</label>
          <textarea id="to_details" rows="5" placeholder="Client Company&#10;456 Client Road&#10;Cape Town, 8001&#10;contact@client.co.za"></textarea>
        </div>
      </div>
    </div>

    <!-- Line Items -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          Line Items
        </div>
      </div>

      <table class="services-table" id="services-table">
        <thead>
          <tr>
            <th style="width:35%">Description</th>
            <th style="width:12%">Notes</th>
            <th style="width:7%" class="num-col">Qty</th>
            <th style="width:13%" class="num-col">Unit Price (R)</th>
            <th style="width:11%" class="num-col">Excl. VAT</th>
            <th style="width:10%" class="num-col">VAT (R)</th>
            <th style="width:11%" class="num-col">Total (R)</th>
            <th class="del-col"></th>
          </tr>
        </thead>
        <tbody id="services-body">
          <!-- rows injected by JS -->
        </tbody>
      </table>

      <div class="add-row-bar">
        <button class="btn btn-ghost btn-sm" onclick="addServiceRow()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Add Line Item
        </button>
        <button class="btn btn-ghost btn-sm" onclick="addServiceRow('heading')">
          + Section Heading
        </button>
      </div>

      <div class="totals-panel" style="margin-top:20px">
        <div class="totals-box">
          <div class="totals-row">
            <span class="lbl">Subtotal (Excl. VAT)</span>
            <span class="val" id="t-subtotal">R 0.00</span>
          </div>
          <div class="totals-row">
            <span class="lbl">VAT</span>
            <span class="val" id="t-vat">R 0.00</span>
          </div>
          <div class="totals-row grand">
            <span>Total Due</span>
            <span class="val" id="t-total">R 0.00</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bank Details + Notes -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
          Banking &amp; Notes
        </div>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>Banking Details</label>
          <textarea id="bank_details" rows="5" placeholder="Bank: First National Bank&#10;Account Name: Your Company (Pty) Ltd&#10;Account Number: 62001234567&#10;Branch Code: 250655&#10;Account Type: Business Cheque&#10;Reference: Invoice Number"></textarea>
        </div>
        <div class="field">
          <label>Notes / Payment Instructions</label>
          <textarea id="notes" rows="5" placeholder="Please quote the invoice number as your payment reference.&#10;&#10;This invoice is subject to our standard terms and conditions."></textarea>
        </div>
      </div>
    </div>

    <!-- Generate bar -->
    <div style="display:flex;justify-content:flex-end;gap:12px;margin-bottom:48px">
      <button class="btn btn-secondary" onclick="clearForm()">Clear Form</button>
      <button class="btn btn-primary" onclick="generateDoc()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Generate &amp; Download PDF
      </button>
    </div>

  </main><!-- /page-create -->

  <!-- History page (hidden) -->
  <main class="main" id="page-history" style="display:none">
    <div class="page-header">
      <div><div class="page-title">Recent Documents</div></div>
    </div>
    <div id="history-list">
      <div style="color:var(--mid);font-size:13px;padding:40px 0;text-align:center">
        No documents generated yet.
      </div>
    </div>
  </main>

  <!-- Settings page (hidden) -->
  <main class="main" id="page-settings" style="display:none">
    <div class="page-header">
      <div><div class="page-title">Business Profile</div><div class="page-subtitle">Saved automatically as you type</div></div>
      <button class="btn btn-primary btn-sm" onclick="saveProfile()">Save Profile</button>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Your Business Details</div></div>
      <div class="form-grid">
        <div class="field form-span2">
          <label>Business Info (paste into From field)</label>
          <textarea id="saved_from" rows="6" placeholder="Company Name&#10;Street Address&#10;City, Postal Code&#10;VAT No: xxxx&#10;email@company.co.za"></textarea>
        </div>
        <div class="field form-span2">
          <label>Default Banking Details</label>
          <textarea id="saved_bank" rows="5" placeholder="Bank: FNB&#10;Account: ..."></textarea>
        </div>
      </div>
    </div>
  </main>

</div><!-- /app-shell -->

<!-- Loading -->
<div class="loading-overlay" id="loading">
  <div class="spinner"></div>
  <div class="loading-text">Generating PDF…</div>
</div>

<!-- Toasts -->
<div class="toast-wrap" id="toast-wrap"></div>

<script>
// ── State ───────────────────────────────────────────────────────────────────
let rowCounter = 0;
const history  = JSON.parse(localStorage.getItem('inv_history') || '[]');
const profile  = JSON.parse(localStorage.getItem('inv_profile') || '{}');

// ── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const today = new Date();
  const due   = new Date(today); due.setDate(due.getDate() + 30);
  document.getElementById('issue_date').value = fmt(today);
  document.getElementById('due_date').value   = fmt(due);

  if (profile.from)  document.getElementById('saved_from').value = profile.from;
  if (profile.bank)  document.getElementById('saved_bank').value = profile.bank;

  addServiceRow();
  addServiceRow();

  document.getElementById('vat_rate').addEventListener('change', e => {
    document.getElementById('custom-vat-field').style.display =
      e.target.value === 'custom' ? 'flex' : 'none';
    recalcAll();
  });

  renderHistory();
});

function fmt(d) {
  return d.toISOString().split('T')[0];
}

function getVatRate() {
  const sel = document.getElementById('vat_rate').value;
  if (sel === 'custom') return parseFloat(document.getElementById('custom_vat').value || 15) / 100;
  return parseFloat(sel);
}

// ── Row management ──────────────────────────────────────────────────────────
function addServiceRow(type) {
  const tbody = document.getElementById('services-body');
  const id = ++rowCounter;

  if (type === 'heading') {
    const tr = document.createElement('tr');
    tr.id = `row-${id}`;
    tr.innerHTML = `
      <td colspan="7" style="background:#F3F4F6">
        <input type="text" placeholder="Section heading…" style="font-weight:600;font-size:13px;color:var(--navy);background:#F3F4F6">
      </td>
      <td class="del-col" style="background:#F3F4F6">
        <button class="del-btn" onclick="delRow(${id})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </button>
      </td>`;
    tbody.appendChild(tr);
    return;
  }

  const tr = document.createElement('tr');
  tr.id = `row-${id}`;
  tr.dataset.rowId = id;
  tr.innerHTML = `
    <td><input type="text" placeholder="Service or product name" oninput="rowChanged(${id})"></td>
    <td><textarea placeholder="Optional details…" rows="1" oninput="this.style.height='auto';this.style.height=this.scrollHeight+'px'"></textarea></td>
    <td class="num-col"><input type="number" value="1" min="0" step="1" style="width:56px" oninput="rowChanged(${id})"></td>
    <td class="num-col"><input type="number" value="0.00" min="0" step="0.01" style="width:90px" oninput="rowChanged(${id})"></td>
    <td class="num-col"><input type="number" readonly style="width:90px;color:var(--mid);background:var(--surface)" tabindex="-1"></td>
    <td class="num-col"><input type="number" readonly style="width:80px;color:var(--mid);background:var(--surface)" tabindex="-1"></td>
    <td class="num-col"><input type="number" readonly style="width:90px;font-weight:600;background:var(--surface)" tabindex="-1"></td>
    <td class="del-col">
      <button class="del-btn" onclick="delRow(${id})">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
      </button>
    </td>`;
  tbody.appendChild(tr);
}

function delRow(id) {
  const row = document.getElementById(`row-${id}`);
  if (row) row.remove();
  recalcAll();
}

function rowChanged(id) {
  const row = document.getElementById(`row-${id}`);
  if (!row || !row.dataset.rowId) return;
  const inputs = row.querySelectorAll('input[type=number]');
  const qty   = parseFloat(inputs[0].value) || 0;
  const price = parseFloat(inputs[1].value) || 0;
  const vat   = getVatRate();
  const excl  = qty * price;
  const vatAmt = excl * vat;
  const total = excl + vatAmt;
  inputs[2].value = excl.toFixed(2);
  inputs[3].value = vatAmt.toFixed(2);
  inputs[4].value = total.toFixed(2);
  recalcAll();
}

function recalcAll() {
  const rows = document.querySelectorAll('#services-body tr[data-row-id]');
  let subtotal = 0, vat = 0;
  rows.forEach(row => {
    const inputs = row.querySelectorAll('input[type=number]');
    const qty   = parseFloat(inputs[0].value) || 0;
    const price = parseFloat(inputs[1].value) || 0;
    const rate  = getVatRate();
    const excl  = qty * price;
    const vatAmt = excl * rate;
    inputs[2].value = excl.toFixed(2);
    inputs[3].value = vatAmt.toFixed(2);
    inputs[4].value = (excl + vatAmt).toFixed(2);
    subtotal += excl;
    vat      += vatAmt;
  });
  document.getElementById('t-subtotal').textContent = fmtR(subtotal);
  document.getElementById('t-vat').textContent      = fmtR(vat);
  document.getElementById('t-total').textContent    = fmtR(subtotal + vat);
}

function fmtR(n) {
  return 'R ' + n.toLocaleString('en-ZA', {minimumFractionDigits:2, maximumFractionDigits:2});
}

// ── Generate ─────────────────────────────────────────────────────────────────
async function generateDoc() {
  const docType = document.querySelector('input[name="doctype"]:checked').value;
  const isQuote = docType === 'quote';

  // Collect services
  const services = [];
  document.querySelectorAll('#services-body tr[data-row-id]').forEach(row => {
    const inputs = row.querySelectorAll('input[type=number]');
    const name = row.querySelector('input[type=text]')?.value?.trim();
    const desc = row.querySelector('textarea')?.value?.trim() || '';
    if (!name) return;
    services.push({
      name,
      description: desc,
      quantity:   parseFloat(inputs[0].value) || 0,
      unit_price: parseFloat(inputs[1].value) || 0,
      tax:        parseFloat(inputs[3].value) || 0,
      total:      parseFloat(inputs[4].value) || 0,
    });
  });

  if (!services.length) { toast('Add at least one line item.', 'error'); return; }

  const subtotal = services.reduce((s,r) => s + r.quantity * r.unit_price, 0);
  const taxTotal = services.reduce((s,r) => s + r.tax, 0);

  const payload = {
    is_quote:       isQuote,
    invoice_number: document.getElementById('doc_number').value,
    issue_date:     document.getElementById('issue_date').value,
    due_date:       document.getElementById('due_date').value,
    payment_terms:  document.getElementById('payment_terms').value,
    from_details:   document.getElementById('from_details').value,
    to_details:     document.getElementById('to_details').value,
    services,
    subtotal,
    tax:   taxTotal,
    total: subtotal + taxTotal,
    bank_details: document.getElementById('bank_details').value,
    notes:        document.getElementById('notes').value,
  };

  document.getElementById('loading').classList.add('active');

  try {
    const res  = await fetch('/generate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
      // Download
      const a = document.createElement('a');
      a.href = `/download/${data.filename}`;
      a.download = data.filename;
      a.click();
      toast(`${data.filename} downloaded!`, 'success');

      // Save to history
      const entry = {
        filename: data.filename,
        docType:  isQuote ? 'Quote' : 'Invoice',
        number:   payload.invoice_number,
        client:   payload.to_details.split('\n')[0] || '—',
        total:    fmtR(payload.total),
        date:     payload.issue_date,
        ts:       Date.now(),
      };
      history.unshift(entry);
      if (history.length > 50) history.length = 50;
      localStorage.setItem('inv_history', JSON.stringify(history));
      renderHistory();
    } else {
      toast(data.error || 'Generation failed', 'error');
    }
  } catch(e) {
    toast('Connection error: ' + e.message, 'error');
  } finally {
    document.getElementById('loading').classList.remove('active');
  }
}

// ── History ───────────────────────────────────────────────────────────────────
function renderHistory() {
  const el = document.getElementById('history-list');
  if (!history.length) {
    el.innerHTML = '<div style="color:var(--mid);font-size:13px;padding:40px 0;text-align:center">No documents generated yet.</div>';
    return;
  }
  el.innerHTML = history.map(h => `
    <div class="card" style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;margin-bottom:10px">
      <div style="display:flex;align-items:center;gap:14px">
        <div style="width:36px;height:36px;border-radius:8px;background:var(--blue-lt);display:flex;align-items:center;justify-content:center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div>
          <div style="font-weight:500;font-size:13.5px">${h.docType} ${h.number}</div>
          <div style="font-size:12px;color:var(--mid)">${h.client} · ${h.date}</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:14px">
        <span style="font-family:'DM Mono',monospace;font-size:13px">${h.total}</span>
        <a href="/download/${h.filename}" class="btn btn-ghost btn-sm">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Download
        </a>
      </div>
    </div>`).join('');
}

// ── Profile ──────────────────────────────────────────────────────────────────
function saveProfile() {
  const p = {
    from: document.getElementById('saved_from').value,
    bank: document.getElementById('saved_bank').value,
  };
  localStorage.setItem('inv_profile', JSON.stringify(p));
  toast('Profile saved!', 'success');
}

function loadProfile() {
  const p = JSON.parse(localStorage.getItem('inv_profile') || '{}');
  if (p.from) document.getElementById('from_details').value = p.from;
  if (p.bank) document.getElementById('bank_details').value = p.bank;
  if (p.from || p.bank) toast('Profile loaded.', 'success');
  else toast('No saved profile found. Go to Business Profile to set one.', 'error');
}

// ── Navigation ───────────────────────────────────────────────────────────────
function showPage(name) {
  ['create','history','settings'].forEach(p => {
    document.getElementById(`page-${p}`).style.display = p === name ? '' : 'none';
  });
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`nav-${name}`) &&
    document.getElementById(`nav-${name}`).classList.add('active');
  if (name === 'create') {
    document.querySelector('.nav-item.active') ||
      document.querySelectorAll('.nav-item')[0].classList.add('active');
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function clearForm() {
  if (!confirm('Clear the form? This cannot be undone.')) return;
  document.getElementById('services-body').innerHTML = '';
  rowCounter = 0;
  addServiceRow(); addServiceRow();
  document.getElementById('from_details').value = '';
  document.getElementById('to_details').value = '';
  document.getElementById('bank_details').value = '';
  document.getElementById('notes').value = '';
  recalcAll();
}

function toast(msg, type) {
  const wrap = document.getElementById('toast-wrap');
  const el   = document.createElement('div');
  el.className = `toast ${type || ''}`;
  el.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      ${type==='success'
        ? '<polyline points="20 6 9 17 4 12"/>'
        : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
    </svg>
    ${msg}`;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}
</script>
</body>
</html>"""

# ── PDF Generation ──────────────────────────────────────────────────────────

def generate_invoice_pdf(invoice_details, output_filename):
    """Generate PDF invoice/quote from invoice details"""
    filepath = os.path.join(INVOICE_DIR, output_filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()

    is_quote = invoice_details.get('is_quote', False)
    doc_title = "QUOTE" if is_quote else "INVOICE"

    # Page Margins
    left_margin = 50
    right_margin = 50
    table_width = width - left_margin - right_margin

    # ── Header ──
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, height - 50, doc_title)
    c.setFont("Helvetica", 12)
    c.drawString(left_margin, height - 70, f"Document Number: {invoice_details['invoice_number']}")
    c.drawString(left_margin, height - 90, f"Issued on: {invoice_details['issue_date']}")
    c.drawString(left_margin, height - 110, f"Due by: {invoice_details['due_date']}")
    if invoice_details.get('payment_terms'):
        c.drawString(left_margin, height - 130, f"Payment Terms: {invoice_details['payment_terms']}")

    # Divider Line
    y_divider = height - 140 if invoice_details.get('payment_terms') else height - 120
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.line(left_margin, y_divider, width - right_margin, y_divider)

    # From and To Sections
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y_divider - 30, "From:")
    c.drawString(width / 2, y_divider - 30, "To:")
    c.setFont("Helvetica", 12)

    y_from = y_divider - 50
    for line in invoice_details['from']:
        if line.strip():
            c.drawString(left_margin, y_from, line)
            y_from -= 15

    y_to = y_divider - 50
    for line in invoice_details['to']:
        if line.strip():
            c.drawString(width / 2, y_to, line)
            y_to -= 15

    # Services Table
    y_table_start = min(y_from, y_to) - 90
    data = [["Description", "Qty", "Unit Price", "VAT", "Total"]]

    for service in invoice_details['services']:
        desc = service['description'].replace('\n', '<br/>') if service.get('description') else ""
        name = service['name']
        display_desc = f"<b>{name}</b>"
        if desc:
            display_desc += f"<br/>{desc}"
        data.append([Paragraph(display_desc, styles["Normal"]),
                     str(service['quantity']),
                     f"R {service['unit_price']:.2f}",
                     f"R {service['tax']:.2f}",
                     f"R {service['total']:.2f}"])

    column_widths = [table_width * 0.4, table_width * 0.12, table_width * 0.16, table_width * 0.16, table_width * 0.16]

    row_heights = [None] + [max(40, 20 + 15 * (service.get('description', '').count('\n') + 1)) for service in invoice_details['services']]

    table = Table(data, colWidths=column_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A3A5C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, -1), 8),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 8),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, left_margin, y_table_start)

    table_height = sum(row_heights[1:]) if len(row_heights) > 1 else len(data) * 20

    # Totals Section
    y_totals = y_table_start - table_height - 40
    summary_width = 200
    summary_x = width - right_margin - summary_width

    c.setFillColor(colors.HexColor('#1A3A5C'))
    c.rect(summary_x - 10, y_totals - 65, summary_width + 20, 80, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(summary_x, y_totals + 5, "Document Summary")

    c.setFont("Helvetica", 12)
    c.drawString(summary_x, y_totals - 15, "Subtotal (Excl. VAT)")
    c.drawString(summary_x + 120, y_totals - 15, f"R {invoice_details['subtotal']:.2f}")

    c.drawString(summary_x, y_totals - 35, "VAT")
    c.drawString(summary_x + 120, y_totals - 35, f"R {invoice_details['tax']:.2f}")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(summary_x, y_totals - 55, "Total Due")
    c.drawString(summary_x + 120, y_totals - 55, f"R {invoice_details['total']:.2f}")

    # Bank Details
    y_bank = y_totals - 100
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y_bank, "Bank Details:")
    c.setFont("Helvetica", 12)
    y_bank -= 20

    for line in invoice_details['bank_details']:
        if line.strip():
            c.drawString(left_margin, y_bank, line)
            y_bank -= 15

    # Notes
    if invoice_details.get('notes'):
        y_notes = y_bank - 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y_notes, "Notes:")
        c.setFont("Helvetica", 11)
        y_notes -= 18
        for line in invoice_details['notes'].split('\n'):
            if line.strip():
                c.drawString(left_margin, y_notes, line)
                y_notes -= 14

    # Footer
    y_footer = 60
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawString(left_margin, y_footer, "Thank you for your business!")
    if is_quote:
        c.drawString(left_margin, y_footer - 15, "This quote is valid for 30 days from the date of issue.")

    c.save()
    return filepath

# ── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Display the invoice form"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate invoice from form data"""
    try:
        data = request.json

        # Parse services from new UI format
        services = []
        for service in data['services']:
            services.append({
                'name': service['name'],
                'description': service.get('description', ''),
                'quantity': int(service['quantity']),
                'unit_price': float(service['unit_price']),
                'tax': float(service['tax']),
                'total': float(service['total'])
            })

        invoice_details = {
            'is_quote': data.get('is_quote', False),
            'invoice_number': data['invoice_number'],
            'issue_date': data['issue_date'],
            'due_date': data['due_date'],
            'payment_terms': data.get('payment_terms', ''),
            'from': data['from_details'].split('\n'),
            'to': data['to_details'].split('\n'),
            'services': services,
            'subtotal': float(data['subtotal']),
            'tax': float(data['tax']),
            'total': float(data['total']),
            'bank_details': data['bank_details'].split('\n'),
            'notes': data.get('notes', '')
        }

        filename = f"{data['invoice_number']}.pdf"
        filepath = generate_invoice_pdf(invoice_details, filename)

        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 400

@app.route('/download/<filename>')
def download(filename):
    """Download generated invoice"""
    filepath = os.path.join(INVOICE_DIR, filename)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))