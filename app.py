import io
import html
import json
import hashlib
import re
import unicodedata
import urllib.request
import urllib.error
import time
from datetime import datetime
from pathlib import Path
from functools import lru_cache
from decimal import Decimal, ROUND_HALF_UP

import pdfplumber
from pypdf import PdfReader, PdfWriter
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

# OCR de secours pour les PDF scannés (ex. Salica Anconetti).
try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image, ImageOps
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

st.set_page_config(page_title="PriceFlow", page_icon="📄", layout="wide")

# Session navigateur PriceFlow : survit aux F5, expire après 1 heure.
cookie_controller = CookieController(key="priceflow_auth_cookie")
PF_AUTH_COOKIE = "priceflow_access_token"
PF_AUTH_MAX_AGE = 60 * 60

st.markdown('<style>:root{color-scheme:light!important;--pf-bg:#f7f9fc;--pf-panel:#fff;--pf-border:#dce4ef;--pf-blue:#087fff;--pf-text:#102039;--pf-muted:#63738a;--pf-green:#139556}\nhtml,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--pf-bg)!important;color:var(--pf-text)!important;font-family:"Source Sans 3","Segoe UI",sans-serif!important}\n[data-testid="stHeader"]{background:transparent!important;pointer-events:none;height:0!important}[data-testid="stToolbar"]{pointer-events:auto}\n.block-container{max-width:1560px;padding:22px 34px 30px!important}\n[data-testid="stVerticalBlock"]{gap:16px}\nh1,h2,h3,h4,p,label{color:var(--pf-text)}\n.st-key-pf_header{background:#fff;border:1px solid #edf1f7;border-radius:16px;box-shadow:0 12px 32px #20365012;padding:14px 22px 0;margin-bottom:20px}\n.st-key-pf_header [data-testid="stHorizontalBlock"]{align-items:center;gap:22px}\n.pf-brand{padding:1px 0 13px;white-space:nowrap}.pf-brand-name{font-size:42px;font-weight:800;letter-spacing:-1.6px;line-height:1.03;color:#09182d}.pf-brand-name span{color:var(--pf-blue)}.pf-brand small{display:block;font-size:15px;color:#596a81;margin-top:3px}\n.st-key-pf_nav{width:100%}.st-key-pf_nav [role="radiogroup"]>div:last-child{margin-left:auto}.st-key-pf_nav [data-testid="stRadio"]>label{display:none}\n.st-key-pf_nav [role="radiogroup"]{display:flex;flex-wrap:nowrap;align-items:stretch;gap:2px;width:100%}\n.st-key-pf_nav [role="radiogroup"] label{position:relative;display:flex;align-items:center;justify-content:center;gap:9px;padding:22px 12px 25px;margin:0!important;min-height:78px;white-space:nowrap;border-bottom:3px solid transparent;cursor:pointer;border-radius:6px 6px 0 0}\n.st-key-pf_nav [role="radiogroup"] label>div:first-child{display:none!important}.st-key-pf_nav [data-testid="stRadioOption"]>div>div:first-child{display:none!important}\n.st-key-pf_nav [role="radiogroup"] label p{font-size:15px!important;font-weight:550;line-height:1.2;color:#24354d}\n.st-key-pf_nav [role="radiogroup"] label:before{content:"";width:26px;height:29px;flex-shrink:0;background:currentColor;mask-size:contain;mask-position:center;mask-repeat:no-repeat;color:#253b58}\n.st-key-pf_nav [role="radiogroup"] label:has(input:checked){border-bottom-color:var(--pf-blue);background:#f8fbff}\n.st-key-pf_nav [role="radiogroup"] label:has(input:checked) p,.st-key-pf_nav [role="radiogroup"] label:has(input:checked):before{color:var(--pf-blue)}\n.st-key-pf_nav [role="radiogroup"] label:hover{background:#f2f7fe}.st-key-pf_nav [role="radiogroup"] label:focus-within{outline:2px solid #94c8ff;outline-offset:-3px}\n.st-key-pf_nav [role="radiogroup"]>:last-child label{margin-left:auto!important;border-bottom-color:transparent}\n.st-key-pf_nav [role="radiogroup"]>:last-child label:before{content:var(--pf-initials,"PF");mask:none!important;background:var(--pf-blue);color:#fff;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600}\n.pf-page-heading{display:flex;align-items:center;gap:20px;padding:9px 0 14px}.pf-page-heading .pf-icon{color:var(--pf-blue);width:46px;height:46px;flex-shrink:0}.pf-page-heading h2{font-size:34px;font-weight:750;letter-spacing:-.6px;line-height:1.15;padding:0;margin:0}.pf-page-heading p{font-size:17px;color:#4d607a;margin:4px 0 0;line-height:1.4}\n.pf-icon{display:inline-block;width:24px;height:24px;vertical-align:middle}.pf-icon svg{display:block;width:100%;height:100%}\n[class*="st-key-pf_title_"] [data-testid="stHorizontalBlock"]{align-items:center}\n.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:9px!important;border:1px solid #bdd6ee!important;background:#fff!important;color:#1761aa!important;min-height:44px;font-weight:600;padding:10px 18px;transition:background .15s,box-shadow .15s}\n.stButton>button:hover,.stDownloadButton>button:hover{background:#eef6ff!important;border-color:#087fff!important}\nbutton[kind="primary"],.stDownloadButton button[kind="primary"]{background:#087fff!important;border-color:#087fff!important;color:white!important;box-shadow:0 4px 9px #087fff24}\nbutton[kind="primary"] p{color:white!important}button[kind="primary"]:hover{background:#006de0!important}\n[data-testid="stFileUploader"]>label p{font-size:16px!important;font-weight:500!important}\n[data-testid="stFileUploaderDropzone"]{min-height:82px;background:#f1f6fc;border:1px dashed #c8d9ec;border-radius:11px;padding:14px 18px}\n[data-testid="stFileUploaderDropzone"] button{background:#fff;color:#1568bd;border:1px solid #b8d2ee;border-radius:8px}\n[data-testid="stFileUploaderFile"]{background:#fff;border-radius:8px;border:1px solid #e1e9f3;padding:8px 12px}\n[data-testid="stMetric"]{background:#fff;border:1px solid #d6e0ed;border-radius:12px;padding:16px 20px;min-height:108px;box-shadow:0 1px 2px #16345a03}\n[data-testid="stMetricLabel"] p{font-size:16px!important;font-weight:400!important;color:#3c4e65!important}\n[data-testid="stMetricValue"]{font-size:31px!important;line-height:1.35!important;font-weight:450!important;color:#102039!important;font-variant-numeric:tabular-nums}\n[data-testid="stAlert"]{border-radius:10px;padding:14px 18px}[data-testid="stAlert"] p{font-size:15px;line-height:1.45}\n[data-baseweb="notification"]{border-radius:10px}\n[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-baseweb="select"]>div{background:#fff!important;color:#102039!important;border-color:#d6e0ed}\n[data-testid="stExpander"]{border:1px solid #dce5ef;border-radius:10px;background:#fff}\n[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid #dce4ef;border-radius:11px;overflow:hidden;background:#fff}\n.pf-section-title{display:flex;gap:12px;align-items:center;margin:9px 0 12px}.pf-section-title .pf-icon{width:27px;height:27px;color:var(--pf-blue)}.pf-section-title h3{font-size:25px;font-weight:700;margin:0;padding:0;color:#102039}\n.pf-table-wrap{width:100%;overflow:auto;border:1px solid #dce4ef;border-radius:11px;background:#fff;margin:2px 0 8px;box-shadow:0 2px 5px #19324a04}\n.pf-table{border-collapse:separate;border-spacing:0;width:100%;min-width:1100px;font-size:14px;font-variant-numeric:tabular-nums;color:#20344d}\n.pf-table th,.pf-table td{padding:11px 13px;text-align:right;border-right:1px solid #e5ebf3;border-bottom:1px solid #e5ebf3;white-space:nowrap}\n.pf-table th{background:#f1f5fa;color:#31465f;font-weight:600}.pf-table th.left,.pf-table td.left{text-align:left}.pf-table td.left{max-width:340px;white-space:normal;min-width:200px}\n.pf-table th:last-child,.pf-table td:last-child{border-right:0}.pf-table tbody tr:last-child td{border-bottom:0}.pf-table tbody tr:nth-child(even) td:not(.best){background:#fbfcfe}.pf-table tbody tr:hover td:not(.best){background:#f1f7ff}\n.pf-table .supplier-head{text-align:center;background:#f0f5fb;color:#153a64;padding:16px 10px}.pf-table .best-head{text-align:center;background:#eaf8f0;color:#158049}.pf-table td.best{background:#f0faf4;color:#118448;font-weight:650}.pf-table tr.total td{background:#edf3fa!important;font-weight:750;padding-top:15px;padding-bottom:15px}.pf-table tr.total td.best{background:#e1f4e9!important}\n.pf-simple-table{min-width:500px;font-size:15px}.pf-simple-table th:first-child,.pf-simple-table td:first-child{text-align:left;white-space:normal;width:72%}.pf-simple-table th{font-weight:500;padding:9px 14px}.pf-simple-table td{padding:9px 14px}\n.pf-supplier-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:8px 0 4px}.pf-supplier-card{background:white;border:1px solid #dce4ef;border-radius:12px;padding:20px 22px;min-height:114px;display:flex;flex-direction:column;justify-content:center;box-shadow:0 3px 12px #1f375408}\n.pf-supplier-name{font-size:24px;font-weight:800;letter-spacing:-.4px;color:#15588f}.pf-supplier-meta{font-size:13px;color:#687c92;margin-top:9px}.pf-supplier-card[data-brand="pum"] .pf-supplier-name{color:#0088c5;font-size:37px}.pf-supplier-card[data-brand="tube"] .pf-supplier-name{color:#155389;font-size:28px}.pf-supplier-card[data-brand="frans"] .pf-supplier-name{color:#222;letter-spacing:-1px;border-left:4px solid #ee334e;padding-left:10px;font-size:24px}\n.pf-comparison-summary{display:flex;justify-content:space-between;gap:16px;align-items:center;margin:0 0 8px;padding:15px 20px;border:1px solid #c8e7d7;border-radius:11px;background:#f0faf4}.pf-comparison-summary strong{font-size:23px;color:#098645}.pf-comparison-summary span{color:#466859;font-size:15px}\n.pf-bottom{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:8px 0 14px}.pf-note{background:#f0f7ff;border:1px solid #b5d8ff;border-radius:11px;padding:18px 22px;color:#245b92;line-height:1.75}.pf-note.green{background:#effaf3;border-color:#b8dfc9;color:#287243}.pf-note strong{font-size:23px;font-weight:700}.pf-note.green strong{color:#0e8a48}.pf-note span{font-size:14px;color:#61748a}\n.auth-card{max-width:620px;margin:20px auto;padding:25px;border:1px solid #dce4ef;border-radius:14px;background:#fff}\n[data-testid="stCaptionContainer"]{color:#718199;font-size:13px}\n@media(max-width:1200px){.block-container{padding:18px 22px!important}.pf-brand-name{font-size:34px}.pf-brand small{font-size:12px}.st-key-pf_header{padding:10px 15px 0}.st-key-pf_nav [role="radiogroup"] label{padding:20px 8px;gap:6px}.st-key-pf_nav [role="radiogroup"] label p{font-size:14px!important}.st-key-pf_nav [role="radiogroup"] label:before{width:21px}}\n@media(max-width:850px){.st-key-pf_header [data-testid="stHorizontalBlock"]{flex-wrap:wrap}.st-key-pf_header [data-testid="stColumn"]{min-width:100%!important;width:100%!important;flex:1 1 100%!important}.pf-brand{padding-bottom:0}.st-key-pf_header [data-testid="stHorizontalBlock"]{gap:4px}.st-key-pf_nav [role="radiogroup"]{overflow-x:auto}.st-key-pf_nav [role="radiogroup"] label{min-height:64px;padding:15px 10px}.st-key-pf_nav [role="radiogroup"]>:last-child label{margin-left:0!important}.pf-page-heading h2{font-size:29px}.pf-page-heading p{font-size:15px}.pf-page-heading{gap:13px}.pf-page-heading .pf-icon{width:35px;height:35px}.pf-bottom{grid-template-columns:1fr}}\n@media(max-width:600px){.block-container{padding:12px 14px!important}.st-key-pf_header{margin-bottom:8px}.pf-brand-name{font-size:34px}.pf-page-heading h2{font-size:27px}.pf-comparison-summary{align-items:flex-start;flex-direction:column}.pf-supplier-grid{grid-template-columns:1fr}.pf-table td.left{min-width:170px}[data-testid="stMetricValue"]{font-size:27px!important}.pf-market-grid{grid-template-columns:1fr!important}}\n\n.st-key-pf_nav [role="radiogroup"]>:nth-child(1) label:before{mask-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.7%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m12%203%209%205v9l-9%205-9-5V8z%22/%3E%3Cpath%20d%3D%22m3%208%209%205%209-5M12%2013v9M7.5%205.5l9%205%22/%3E%3C/svg%3E")}\n.st-key-pf_nav [role="radiogroup"]>:nth-child(2) label:before{mask-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.7%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M4%2022h8M6%2022V4h4v18M3%204h18v3H3zM8%201v3M19%207v7l-2%202M5%2010h6M5%2014h6M5%2018h6M10%204l5-3%206%203%22/%3E%3C/svg%3E")}\n.st-key-pf_nav [role="radiogroup"]>:nth-child(3) label:before{mask-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.7%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%203v18M7%2021h10M4%206h16M4%206%201%2014h6L4%206Zm16%200-3%208h6l-3-8Z%22/%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%225%22%20r%3D%222%22/%3E%3C/svg%3E")}\n.st-key-pf_nav [role="radiogroup"]>:nth-child(4) label:before{mask-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22currentColor%22%20stroke-width%3D%221.7%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M14%202H5v20h14V7l-5-5Z%22/%3E%3Cpath%20d%3D%22M14%202v6h5M8%2012h8M8%2016h8%22/%3E%3C/svg%3E")}\n.pf-market-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0 18px}.pf-market-kpi{background:#fff;border:1px solid #dbe5ef;border-radius:13px;padding:15px 17px;box-shadow:0 4px 14px rgba(31,55,84,.035)}.pf-market-kpi .n{font-size:1.7rem;font-weight:850;color:#071b33}.pf-market-kpi .l{font-size:.84rem;color:#62748a;margin-top:3px}.pf-finding{background:#fff;border:1px solid #dbe5ef;border-left:5px solid #0b8cff;border-radius:12px;padding:16px 18px;margin:10px 0}.pf-finding.warn{border-left-color:#f59e0b}.pf-finding.danger{border-left-color:#e34b4b}.pf-finding.link{border-left-color:#7c5cff}.pf-finding.ok{border-left-color:#12a56a}.pf-finding h4{margin:0 0 7px;font-size:1.05rem}.pf-finding p{margin:4px 0;color:#40556c}.pf-source{font-size:.82rem;color:#6d8095;margin-top:8px}.pf-source-box{background:#f6f9fc;border:1px solid #dce6ef;border-radius:9px;padding:12px 14px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.82rem;white-space:pre-wrap;color:#203449}.pf-doc-chip{display:inline-block;background:#eef6ff;color:#0b66bd;border:1px solid #c9e3ff;border-radius:999px;padding:5px 10px;margin:3px 5px 3px 0;font-size:.78rem}.pf-ai-note{background:#eef7ff;border:1px solid #b9ddff;border-radius:11px;padding:12px 15px;color:#31506e;margin:8px 0 16px}\n</style>', unsafe_allow_html=True)

st.markdown('<style>.st-key-pf_auth_card{max-width:560px;margin:30px auto 24px;background:#fff;border:1px solid #dce4ef;border-radius:16px;padding:28px;box-shadow:0 12px 32px #2036500c}\n.st-key-pf_auth_card h3{font-size:27px;letter-spacing:-.5px;padding-top:0}\n.st-key-pf_auth_card [data-testid="stForm"]{border:0;padding:0}\n.st-key-pf_auth_card [role="tablist"]{gap:22px}\n.st-key-pf_auth_card [role="tab"][aria-selected="true"]{color:#087fff!important;border-bottom-color:#087fff!important}\n.st-key-pf_auth_card [data-baseweb="tab-highlight"]{background:#087fff!important}\n.st-key-pf_auth_card [data-testid="stTextInput"] input{min-height:44px;background:#f7f9fc;color:#102039}\n.st-key-pf_auth_card .stFormSubmitButton>button{background:#087fff!important;color:white!important;border-color:#087fff!important}.st-key-pf_auth_card .stFormSubmitButton>button p{color:white!important}.pf-auth-footer{text-align:center;color:#718199;font-size:13px}\n@media(max-width:600px){.st-key-pf_auth_card{padding:20px;margin-top:16px}}\n</style>', unsafe_allow_html=True)

PF_ICONS = {'box': '<path d="m12 3 9 5v9l-9 5-9-5V8z"/><path d="m3 8 9 5 9-5M12 13v9M7.5 5.5l9 5"/>', 'crane': '<path d="M4 22h8M6 22V4h4v18M3 4h18v3H3zM8 1v3M19 7v7l-2 2M5 10h6M5 14h6M5 18h6M10 4l5-3 6 3"/>', 'scale': '<path d="M12 3v18M7 21h10M4 6h16M4 6 1 14h6L4 6Zm16 0-3 8h6l-3-8Z"/><circle cx="12" cy="5" r="2"/>', 'file': '<path d="M14 2H5v20h14V7l-5-5Z"/><path d="M14 2v6h5M8 12h8M8 16h8"/>', 'chart': '<path d="M4 20v-6h3v6M11 20V9h3v11M18 20V3h3v17"/>', 'user': '<circle cx="12" cy="8" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>'}


def pf_icon(name):
    shape = PF_ICONS.get(name, PF_ICONS["file"])
    return '<span class="pf-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + shape + '</svg></span>'


def pf_heading(title, subtitle, icon="file"):
    st.markdown(f'<div class="pf-page-heading">{pf_icon(icon)}<div><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div></div>', unsafe_allow_html=True)


def pf_section(title, icon="file"):
    st.markdown(f'<div class="pf-section-title">{pf_icon(icon)}<h3>{html.escape(title)}</h3></div>', unsafe_allow_html=True)


def pf_number(value, decimals=2):
    return f"{float(value):,.{decimals}f}".replace(",", " ").replace(".", ",")


def pf_simple_table(frame):
    view = frame.copy()
    for column in view.columns:
        if pd.api.types.is_numeric_dtype(view[column]):
            view[column] = view[column].apply(lambda value: pf_number(value) if pd.notna(value) else "—")
    table = view.to_html(index=False, escape=True, border=0, classes="pf-table pf-simple-table")
    st.markdown('<div class="pf-table-wrap">' + table + '</div>', unsafe_allow_html=True)


def pf_navigation():
    options = ["▣ Achats / Fournisseurs", "🏗 Locations", "⚖ Comparatif", "📋 Analyse Marché", "Mon compte ⌄"]
    labels = dict(zip(options, ["Achats / Fournisseurs", "Locations", "Comparatif", "Analyse Marché", "Mon compte ⌄"]))
    user = st.session_state.get("pf_user", {})
    name = user.get("user_metadata", {}).get("full_name") or user.get("email", "")
    parts = re.findall(r"[A-Za-zÀ-ÿ]+", name.split("@")[0])
    initials = "".join(part[0] for part in parts[:2]).upper() or "PF"
    st.markdown(f'<style>:root{{--pf-initials:"{initials}"}}</style>', unsafe_allow_html=True)
    with st.container(key="pf_header"):
        brand, menu = st.columns([2.5, 8], gap="small")
        with brand:
            st.markdown('<div class="pf-brand"><div class="pf-brand-name">Price<span>Flow</span></div><small>Analyse & comparaison des achats</small></div>', unsafe_allow_html=True)
        with menu:
            with st.container(key="pf_nav"):
                return st.radio("Navigation PriceFlow", options, format_func=labels.get, horizontal=True, label_visibility="collapsed", key="pf_main_nav")


def pf_supplier_cards(offers):
    cards = []
    for offer in offers:
        supplier = str(offer["Fournisseur"])
        brand = "pum" if supplier == "PUM" else "tube" if "H-TUBE" in supplier else "frans" if "FRANS BONHOMME" in supplier else "other"
        title = "H-TUBE" if brand == "tube" else supplier
        cards.append(f'<div class="pf-supplier-card" data-brand="{brand}"><div class="pf-supplier-name">{html.escape(title)}</div><div class="pf-supplier-meta">N° {html.escape(str(offer["N° document"]))} · {len(offer["Lignes"])} lignes<br>{fmt_money(offer["Total HT"])}</div></div>')
    st.markdown('<div class="pf-supplier-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


if "history" not in st.session_state:
    st.session_state.history = []
if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "saved_signature" not in st.session_state:
    st.session_state.saved_signature = None

def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip(" -")

def fr_float(s):
    if s is None:
        return None
    s = str(s).strip().replace("€", "").replace("\u00a0", " ").replace(" ", "")
    m = re.search(r"-?\d[\d.,]*", s)
    if not m:
        return None
    s = m.group(0).rstrip(".,")
    if "," in s:
        # Format français : 1.348,14 -> 1348.14 ; 50,943 -> 50.943
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None

def qty_float(s):
    return fr_float(s)

def detect_supplier(text):
    low = text.lower()
    compact = re.sub(r"\s+", "", low)
    if "aredis-robinetterie" in low: return "AREDIS"
    if "outillage meridional" in low: return "L'OUTILLAGE MERIDIONAL"
    if "first robinetterie" in low: return "FIRST ROBINETTERIE"
    if "anconetti" in low: return "ANCONETTI"
    if "mypum.fr" in low or '"les cayols"' in low: return "PUM"
    if "clim +" in low or "clim+" in low or "climplus.fr" in low: return "CLIM+"
    if "cedeo" in low or "bon d'enlèvement" in low: return "CEDEO"
    if "midipyreneesscellement" in compact or "mpsvitrolles" in compact: return "MPS"
    if "aldes.fr" in low or "aldes france" in low: return "ALDES"
    if "rexel" in low and "facture" in low: return "REXEL"
    if "ouestisol.fr" in low or "ouest isol" in low or "oiv marseille" in low: return "OUEST ISOL"
    if "prolians" in low or "descours & cabaud" in low: return "PROLIANS"
    if "lorflex" in low: return "LORFLEX"
    if "fritec" in low: return "FRITEC"
    if "richardson" in low and "proposition" in low: return "RICHARDSON"
    if "frans bonhomme" in low or "fransbonhomme.fr" in low: return "FRANS BONHOMME"
    if "point plastique" in low or ("devis n°" in low and "jouanneau" in low): return "H-TUBE / POINT PLASTIQUE"
    if "rodaclim" in low or "klima13" in low: return "RODACLIM"
    if "pack service gemenos" in low: return "PACK SERVICE"
    if "yack sas" in low or "commande@yack.fr" in low: return "YACK"
    if "www.vim.fr" in low or "experts en ventilation" in low: return "VIM"
    return "Fournisseur non identifié"

def detect_document_number(text, supplier):
    patterns = [
        r"Bon d['’]enlèvement\s*N[°º]?\s*([0-9]{6,})",
        r"OFFRE DE PRIX\s*N[°º]?\s*([0-9]{6,})",
        r"\bN[°º]\s*([0-9]{6,})\s+du\s+\d{2}[-/]\d{2}[-/]\d{4}",
        r"\b(M\s*/\s*BL\s*\d+)\b",
        r"Bulletin\s+de\s+livraison\s*\*?\s*([0-9]{5,})",
        r"\*\s*([0-9]{5,})",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return re.sub(r"\s+", "", m.group(1)).upper()

    if supplier == "L'OUTILLAGE MERIDIONAL":
        m = re.search(r"Numéro\s*:\s*([0-9]+)", text, re.I)
        if m: return m.group(1)

    if supplier == "FIRST ROBINETTERIE":
        # En-tête : Date | N° BL | N° Client, ex. 04/07/2025 291 466 10 280.
        m = re.search(r"\b\d{2}/\d{2}/\d{4}\s+(\d{3}\s*\d{3})\s+\d{2}\s*\d{3}\b", text)
        if m: return re.sub(r"\s+", "", m.group(1))
        m = re.search(r"N[°º]?\s*BL.{0,80}?\n?\s*\d{2}/\d{2}/\d{4}\s+(\d{3}\s*\d{3})", text, re.I | re.S)
        if m: return re.sub(r"\s+", "", m.group(1))

    if supplier == "ANCONETTI":
        m = re.search(r"\d{2}/\d{2}/\d{4}\s*(\d{7})(?!\d)", text)
        if m: return m.group(1)
        # Bon d'enlèvement / débit Salica Anconetti scanné.
        m = re.search(r"DEBIT\s+du\s+N[o°]?\s*\n?.{0,100}?\b(\d{6,8})\b", text, re.I | re.S)
        if m: return m.group(1)
        m = re.search(r"O\s*F\s*F\s*R\s*E\s*D\s*E\s*P\s*R\s*I\s*X\s*\n\s*([0-9.]+)", text, re.I)
        if m: return m.group(1)

    if supplier in ("MPS", "PROLIANS"):
        compact = re.sub(r"\s+", "", text)
        m = re.search(r"Bulletindelivraison\*?([0-9]{5,})", compact, re.I)
        if m: return m.group(1)

    supplier_patterns = {
        "ALDES": [r"Offre\s+de\s+prix\s+([0-9]{6,})"],
        "REXEL": [r"FACTURE\s*N[°º]?\s*([0-9]{6,})"],
        "OUEST ISOL": [r"PROPOSITION\s+COMMERCIALE\s*N[°º]?\s*([0-9]{6,})"],
        "PROLIANS": [r"Bulletin\s+de\s+livraison\s*\*?\s*([0-9]{5,})", r"\*\s*([0-9]{5,})"],
        "LORFLEX": [r"\bDevis\s+([0-9]{6,})\b"],
        "FRITEC": [r"Numéro\s*:\s*([0-9]{6,})"],
        "RICHARDSON": [r"PROPOSITION\s*N\.?\s*:\s*([0-9-]+)", r"N\.\s*:\s*([0-9-]+)\s+DU"],
        "FRANS BONHOMME": [r"Offre\s+de\s+prix\s+n[°º]\s*([0-9]+)"],
        "H-TUBE / POINT PLASTIQUE": [r"DEVIS\s+n[°º]\s*([0-9-]+)"],
        "RODACLIM": [r"\b(AR[0-9]{6,})\b"],
        "PACK SERVICE": [r"\b\d{2}/\d{2}/\d{4}\s+([0-9]{5,})\s+CGE"],
        "YACK": [r"Numéro\s+du\s+devis\s*:\s*([A-Z0-9-]+)"],
        "VIM": [r"\b(RI[/\-]?[0-9]{8})\b", r"B\.LIVRAISON\s+([0-9]+)"],
        "CLIM+": [r"Facture\s+([A-Z0-9]+)\s+du"],
    }
    for pat in supplier_patterns.get(supplier, []):
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)

    return "Non détecté"

def detect_total_ht(text, supplier=None):
    if supplier == "ANCONETTI":
        matches = re.findall(r"([0-9][0-9 .]*[,.][0-9]{2})\s*H\.?T\.?\s*$", text, re.M | re.I)
        if matches:
            return fr_float(matches[-1])
    if supplier == "YACK":
        m = re.search(r"MONTANT TOTAL DEVIS BASE HT\s+([0-9][0-9 .]*[,.][0-9]{2})", text, re.I)
        if m: return fr_float(m.group(1))
    # Détection du Total HT quel que soit son emplacement sur la ligne.
    # Compatible notamment : Outillage Méridional, First, Anconetti, MPS,
    # Aredis, PUM et CEDEO.
    normalized = text.replace("\u00a0", " ")
    money = r"([0-9][0-9 .]*[,.][0-9]{2,4})"

    # Salica Anconetti scanné : le total est imprimé sous la forme "238,43 H.T".
    # Totaux spécifiques aux nouveaux formats fournisseurs.
    specific_patterns = {
        "ALDES": [r"Total\s+net\s+HT\s*:\s*" + money, r"Total\s+Net\s*\(HT\)\s+articles\s*:\s*" + money],
        "REXEL": [r"NET\s+H\.T\.\s*" + money, r"Sous\s+total\s+commande\s+\S+\s+" + money],
        "OUEST ISOL": [r"Total\s+HT\s+EUR\s+" + money],
        "PROLIANS": [r"TOTAL\s+H\.T\.\s*:\s*" + money],
        "LORFLEX": [r"Total\s+brut\s+HT\s+" + money, r"Total\s+postes\s+" + money],
        "FRITEC": [r"Montant\s+total\s+de\s+la\s+commande\s+net\s+HT\s+" + money],
        "RICHARDSON": [r"MONTANT\s+H\.T\s+" + money],
        "FRANS BONHOMME": [r"Total\s+HT\s*:\s*" + money, r"Total\s*:\s*" + money],
        "H-TUBE / POINT PLASTIQUE": [r"TOTAL\s+H\.T\s+" + money],
        "RODACLIM": [r"Total\s+HT\s+" + money],
        "PACK SERVICE": [r"Total\s+Devis\s+HT\s+" + money, r"NET\s+H\.T\..*?\n\s*" + money],
        "CLIM+": [r"TOTAL\s+HT\s+" + money],
        "YACK": [r"Total\s+HT\s+" + money, r"TOTAL\s+NET\s+HT\s+" + money],
        "VIM": [r"TOTAL\s+HT\s+" + money, r"NET\s+H\.?T\.?\s+" + money],
    }
    for pat in specific_patterns.get(supplier, []):
        m = re.search(pat, normalized, re.I)
        if m:
            value = fr_float(m.group(1))
            if value is not None:
                return value

    for raw in normalized.splitlines():
        line = clean(raw)
        low = line.lower()

        if not re.search(r"\btotal\s+h\s*\.?\s*t\s*\.?", low):
            continue

        # Ne jamais prendre un sous-total "hors écocontribution".
        if any(x in low for x in [
            "sous total", "sous-total",
            "total ht hors ecocontrib",
            "total ht hors éco",
            "total h.t. hors ecocontrib",
            "total h.t. hors éco"
        ]):
            continue

        # Le libellé peut être au milieu de la ligne :
        # "... Total HT 30.00" ou "... Port Total HT : 140,70 €"
        m = re.search(
            r"\btotal\s+h\s*\.?\s*t\s*\.?\s*[:.]?\s*(?:€\s*)?" + money,
            line,
            flags=re.I
        )
        if m:
            value = fr_float(m.group(1))
            if value is not None:
                return value

    # Secours : certains PDF placent le montant sur la ligne suivante.
    lines = [clean(x) for x in normalized.splitlines()]
    for i, line in enumerate(lines):
        low = line.lower()
        if not re.search(r"\btotal\s+h\s*\.?\s*t\s*\.?", low):
            continue
        if any(x in low for x in ["hors ecocontrib", "hors éco", "sous total", "sous-total"]):
            continue

        # Montant éventuel situé après le libellé, même avec texte parasite.
        pos = re.search(r"\btotal\s+h\s*\.?\s*t\s*\.?", line, flags=re.I)
        tail = line[pos.end():] if pos else ""
        nums = re.findall(money, tail)
        if nums:
            value = fr_float(nums[0])
            if value is not None:
                return value

        for nxt in lines[i + 1:i + 3]:
            nums = re.findall(money, nxt)
            if nums:
                value = fr_float(nums[0])
                if value is not None:
                    return value

    return None

def detect_extra_charges(text):
    """Détecte les frais complémentaires réellement facturés."""
    direct = explicit_eco_charges(text)
    if direct is not None:
        return direct
    charges = []
    seen = set()

    for raw in text.replace("\u00a0", " ").splitlines():
        line = clean(raw)
        low = line.lower()

        # FIRST et formats similaires : total récapitulatif "Contribution REP 0,02 €".
        m_rep_total = re.search(r"^Contribution\s+REP\s*[:.]?\s*([0-9][0-9 .]*[,.][0-9]{2,4})\s*€?\s*$", line, re.I)
        if m_rep_total:
            amount = fr_float(m_rep_total.group(1))
            if amount is not None:
                # Le récapitulatif prévaut sur les micro-lignes REP unitaires.
                charges = [c for c in charges if c.get("label") != "ÉCO-CONTRIBUTION"]
                seen = {k for k in seen if k[0] != "ÉCO-CONTRIBUTION"}
                key = ("ÉCO-CONTRIBUTION", round(amount, 4))
                seen.add(key)
                charges.append({"label": "ÉCO-CONTRIBUTION", "amount": amount})
            continue

        # ALDES : l'éco-participation affichée est déjà incluse dans les prix / total articles.
        if re.search(r"^Dont\s+(?:eco|éco)-?participation\s+HT\s*:", line, re.I):
            continue

        # CLIM+ / Saint-Gobain : lignes récapitulatives en bas du document.
        # On ignore volontairement les lignes article "... HT : 0,60 € / PCE"
        # et on prend seulement les totaux "Dont éco-contribution DEEE : 1,20 €".
        m_clim = re.search(
            r"^(?:(?:Total\s+)?|Dont\s+)(?:eco|éco)-?contribution\s+(?:DEEE|PMCB)(?:\s+HT)?\s*:?\s*"
            r"([0-9][0-9 .]*[,.][0-9]{2,4})\s*€?\s*$",
            line, re.I
        )
        if m_clim:
            amount = fr_float(m_clim.group(1))
            if amount is not None:
                key = ("ÉCO-CONTRIBUTION", round(amount, 4))
                if key not in seen:
                    seen.add(key)
                    charges.append({"label": "ÉCO-CONTRIBUTION", "amount": amount})
            continue

        if re.search(r"\b(?:eco|éco)[-\s]*contribution\b", low):
            # Ligne article, ex. ANCONETTI :
            # 454 ECO CONTRIBUTION REP 1,000 PCE 0,04 0,04
            m = re.search(
                r"(?:eco|éco)\s*contribution(?:\s+rep)?\s+"
                r"([0-9]+(?:[,.][0-9]+)?)\s+"
                r"(?:PCE|BCE|PCS|PIECE|PIÈCE|ML|M|U|UN|KG)\s+"
                r"([0-9]+(?:[,.][0-9]{1,4})?)\s+"
                r"([0-9]+(?:[,.][0-9]{1,4})?)",
                line, flags=re.I
            )
            if m:
                # Le dernier nombre est le montant HT de la ligne.
                amount = fr_float(m.group(3))
                if amount is not None:
                    key = ("ÉCO-CONTRIBUTION", round(amount, 4))
                    if key not in seen:
                        seen.add(key)
                        charges.append({"label": "ÉCO-CONTRIBUTION", "amount": amount})
                continue

            # Ligne récapitulative, ex. PUM : Eco contribution : 2,45 EUR
            m = re.search(
                r"(?:Total\s+)?(?:eco|éco)[-\s]*contribution(?:\s+PMCB|\s+DEEE)?\s*[:.]?\s*"
                r"([0-9][0-9 .]*[,.][0-9]{2,4})\s*(?:eur|€)?",
                line, flags=re.I
            )
            if m:
                amount = fr_float(m.group(1))
                if amount is not None:
                    key = ("ÉCO-CONTRIBUTION", round(amount, 4))
                    if key not in seen:
                        seen.add(key)
                        charges.append({"label": "ÉCO-CONTRIBUTION", "amount": amount})
                continue

        if re.search(r"\bsurcharge\s+[ée]nergie\b", low):
            m = re.search(
                r"surcharge\s+[ée]nergie\s*[:.]?\s*"
                r"([0-9][0-9 .]*[,.][0-9]{2,4})\s*(?:eur|€)?",
                line, flags=re.I
            )
            if m:
                amount = fr_float(m.group(1))
                if amount is not None:
                    key = ("SURCHARGE ÉNERGIE", round(amount, 4))
                    if key not in seen:
                        seen.add(key)
                        charges.append({"label": "SURCHARGE ÉNERGIE", "amount": amount})

    return charges

def strip_eco(desc):
    desc = re.split(r"\bDont\s+(?:éco|eco)[^\n]*", str(desc or ""), flags=re.I)[0]
    return clean(desc)

def table_rows(pdf):
    rows = []
    for page in pdf.pages:
        for table in (page.extract_tables() or []):
            if not table:
                continue
            header_idx = None
            header = None
            for i, r in enumerate(table[:12]):
                vals = [clean(x).lower() for x in (r or [])]
                joined = " | ".join(vals)
                if any(k in joined for k in ["désignation", "description", "nom de l'article"]) and any(k in joined for k in ["p.u", "pu ht", "prix unitaire"]):
                    header_idx, header = i, vals
                    break
            if header_idx is None:
                continue

            def find_col(keys):
                for j, h in enumerate(header):
                    if any(k in h for k in keys):
                        return j
                return None

            dcol = find_col(["désignation", "description", "nom de l'article"])
            qcol = find_col(["qté livrée", "qte livree", "quantité", "quantite", "qte"])
            pcol = find_col(["p.u. ht", "p.u ht", "pu ht", "prix unitaire", "p.u.", "p.u"])
            if dcol is None or qcol is None or pcol is None:
                continue

            for r in table[header_idx + 1:]:
                if not r or max(dcol, qcol, pcol) >= len(r):
                    continue
                desc = strip_eco(r[dcol])
                qty = qty_float(r[qcol])
                pu = fr_float(r[pcol])
                low = desc.lower()
                if not desc or qty is None or pu is None:
                    continue
                if any(x in low for x in ["total ", "transformé de", "reference gaz", "référence gaz", "eco contribution rep", "éco contribution rep"]):
                    continue
                rows.append({"Désignation": desc, "Quantité": qty, "Prix unitaire": pu})
    return rows

def text_rows(text, supplier):
    rows = []
    if supplier == "ANCONETTI":
        text = re.sub(r"(?m)^(\d{5,8})[.:]?(?=[A-Z])", r"\1 ", text)
        text = re.sub(r"(?<=\d),\s+(?=\d)", ",", text)
    lines = [clean(x) for x in text.splitlines() if clean(x)]

    if supplier == "FIRST ROBINETTERIE":
        # FIRST : référence + conditionnement + désignation + quantité + unité + PU + montant.
        # Le conditionnement peut être "2 unité", "3 SACHET" ou seulement un nombre.
        pat = re.compile(
            r"^([A-Z0-9][A-Z0-9._/-]{2,24})\s+\d+(?:[.,]\d+)?(?:\s+(?:unité|unite))?\s+"
            r"(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:ML|PCE|PCS|PC|U|UN|M|KG|BAG)\s+"
            r"(\d+(?:[.,]\d{1,4})?)\s+(\d+(?:[.,]\d{1,4})?)$", re.I
        )
        for line in lines:
            if line.lower().startswith("reste à livrer"):
                break
            m = pat.match(line)
            if not m:
                continue
            q, pu, amount = fr_float(m.group(3)), fr_float(m.group(4)), fr_float(m.group(5))
            if q is None or pu is None or amount is None or abs(q * pu - amount) > max(0.08, abs(amount) * 0.002):
                continue
            rows.append({"Référence": m.group(1), "Désignation": clean(m.group(2)), "Quantité": q, "Prix unitaire": pu})

    elif supplier == "ANCONETTI":
        # Salica Anconetti : fonctionne sur couche texte et sur OCR des bons scannés.
        # Lecture par la fin de ligne : quantité + unité + PU + montant.
        # Cela tolère les petits parasites OCR au milieu de la désignation.
        pat = re.compile(
            r"^(\d{5,})\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+"
            r"(?:PCE|BCE|PCS|PIECE|PIÈCE|ML|M|U|UN|KG|BTE)\s+"
            r"(\d+(?:[.,]\d{1,4})?)\s+(\d+(?:[.,]\d{1,4})?)$", re.I
        )
        scan_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Certains libellés longs sont coupés par l'OCR avant les colonnes chiffrées.
            if re.match(r"^\d{5,}\s+", line) and not pat.match(line):
                merged = line
                for j in range(i + 1, min(i + 3, len(lines))):
                    if re.match(r"^\d{3,}\s+", lines[j]):
                        break
                    merged = clean(merged + " " + lines[j])
                    if pat.match(merged):
                        i = j
                        break
                scan_lines.append(merged)
            else:
                scan_lines.append(line)
            i += 1

        for line in scan_lines:
            m = pat.match(line)
            if not m:
                continue
            ref, desc = m.group(1), clean(m.group(2))
            if "eco contribution" in desc.lower() or "éco contribution" in desc.lower():
                continue
            rows.append({
                "Référence": ref,
                "Désignation": desc,
                "Quantité": fr_float(m.group(3)),
                "Prix unitaire": fr_float(m.group(4)),
            })


    elif supplier == "CLIM+":
        # Saint-Gobain CLIM+ : code article, nombre, désignation, quantité, unité, PU, montant.
        pat = re.compile(r"^(\d{5,})\s+\d+(?:[.,]\d+)?\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:PI|PCE|PC|U|UN|ML|M|KG|RL|BTE|ENS|LOT)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+[A-Z]$", re.I)
        for line in lines:
            m=pat.match(line)
            if m:
                rows.append({"Référence":m.group(1),"Désignation":clean(m.group(2)),"Quantité":fr_float(m.group(3)),"Prix unitaire":fr_float(m.group(4))})

    elif supplier == "YACK":
        pat = re.compile(r"^([A-Z0-9][A-Z0-9._/-]{3,})\s+(.*?)\s*(\d+(?:[.,]\d+)?)\s+([0-9][0-9 ]*[,.]\d{2})\s*€\s+([0-9][0-9 ]*[,.]\d{2})\s*€$")
        title = ""
        for index, line in enumerate(lines):
            if "référence produit" in line.lower():
                title = ""
            if line.lower().startswith("descriptif") and index and not pat.match(lines[index - 1]):
                title = lines[index - 1]
            m = pat.match(line)
            if m:
                q, pu, amount = (fr_float(m.group(i)) for i in (3, 4, 5))
                if q and abs(q * pu - amount) < .02:
                    desc = title or (lines[index - 1] if index else "") or clean(m.group(2)) or m.group(1)
                    rows.append({"Référence": m.group(1), "Désignation": desc, "Quantité": q, "Prix unitaire": pu})
                title = ""

    elif supplier == "VIM":
        # Factures VIM : référence + libellé + éventuelle colonne DEEE + quantité + PU + montant.
        # Le champ DEEE est parfois présent entre la désignation et la quantité (ex. 4,91).
        # On ancre surtout les 3 dernières colonnes : quantité, PU, montant.
        pat=re.compile(r"^([0-9A-Z]{5,})\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+([0-9][0-9 .]*[,.]\d{2,4})\s+([0-9][0-9 .]*[,.]\d{2})$",re.I)
        for line in lines:
            m=pat.match(line)
            if not m or not re.search(r"\d", m.group(1)): continue
            prefix=clean(m.group(2)); q=fr_float(m.group(3)); pu=fr_float(m.group(4)); amount=fr_float(m.group(5))
            if not (q and pu is not None and amount is not None and abs(q*pu-amount)<=max(.12,abs(amount)*.003)):
                continue
            # Retire une éventuelle valeur DEEE isolée en fin de désignation.
            prefix=re.sub(r"\s+\d+[.,]\d{2}$", "", prefix).strip()
            rows.append({"Référence":m.group(1),"Désignation":prefix,"Quantité":q,"Prix unitaire":pu})

    elif supplier == "PUM":
        pat = re.compile(r"^\d+\s*-\s*\d+\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:Mètre|Metre|Pièce|Piece|PCE|ML|U)\s+(\d+(?:[.,]\d+)?)\s+(?:\d+(?:[.,]\d+)\s+)?\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)$", re.I)
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": m.group(1), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

    elif supplier in ("MPS", "PROLIANS"):
        # Gabarit Descours & Cabaud :
        # référence / quantité / unité / PU / ... / prix net / montant net.
        # On exige un PU strictement positif pour éviter les nombres parasites
        # présents dans les adresses, téléphones et codes du PDF.
        for i, line in enumerate(lines):
            m = re.match(
                r"^(\d{5,})\s+(\d+(?:[.,]\d+)?)\s+"
                r"(?:P|K|T|I|M|S|F|D|C|R)\s+"
                r"(\d+(?:[.,]\d+)?)\b",
                line,
                re.I
            )
            if not m or i == 0:
                continue

            qty = fr_float(m.group(2))
            pu = fr_float(m.group(3))
            if qty is None or pu is None or qty <= 0 or pu <= 0:
                continue

            desc = re.sub(r"\s+F\d+$", "", lines[i - 1]).strip()
            if not desc or re.match(r"^\d", desc):
                continue

            rows.append({
                "Référence": m.group(1),
                "Désignation": desc,
                "Quantité": qty,
                "Prix unitaire": pu
            })

    elif supplier == "ALDES":
        # Ex. 10 11052278 SR 135 D125 S/E ACOUS RAL9003 1,00 PC 10 10,36 10,36 4 à 5 jrs
        pat = re.compile(
            r"^\d+\s+([A-Z0-9_-]+)\s+(.+?)\s+"
            r"(\d+(?:[.,]\d+)?)\s+(?:PC|PCE|PCS|U|UN|ML|M|KG)\s+"
            r"\d+(?:[.,]\d+)?\s+(\d+(?:[.,]\d+)?)\s+\d+(?:[.,]\d+)?"
            r"(?:\s+\d+\s+à\s+\d+\s+jrs?)?\s*$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({
                    "Désignation": clean(m.group(2)),
                    "Quantité": fr_float(m.group(3)),
                    "Prix unitaire": fr_float(m.group(4))
                })

    elif supplier == "REXEL":
        # 0010 REF PU_BRUT REMISE PU_NET QTE U TOTAL TVA
        pat = re.compile(
            r"^\d+\s+\S+\s+\d+(?:[.,]\d+)?\s+\d+(?:[.,]\d+)?\s+"
            r"(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+\w+\s+\d+(?:[.,]\d+)?\s+\d+\s*$"
        )
        for i, line in enumerate(lines):
            m = pat.match(line)
            if m:
                desc = lines[i + 1] if i + 1 < len(lines) else "ARTICLE REXEL"
                rows.append({"Désignation": desc, "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(1))})

    elif supplier == "OUEST ISOL":
        # OUEST ISOL / OIV : selon le moteur PDF, la quantité peut être sur
        # la ligne précédente et l'article + unité + PU + montant sur une seule ligne.
        status_qty = re.compile(r"(?:Normalement\s+disponible|Disponibilit[ée]\s+[àa]\s+confirmer|Disponible|En\s+stock)\s+(\d+(?:[.,]\d+)?)\s*$", re.I)
        article_price = re.compile(
            r"^\d+\s+([A-Z0-9][A-Z0-9._/-]{3,})\s+(.+?)\s+"
            r"(CTN|PCE|PCS|PC|U|UN|ML|M|KG|BTE|RL|ENS|LOT)\s+"
            r"(\d+(?:[.,]\d+)?)\s*€?\s+(\d+(?:[.,]\d+)?)\s*€?\s*$", re.I)
        last_qty = None
        for i, line in enumerate(lines):
            mq = status_qty.search(line)
            if mq:
                last_qty = fr_float(mq.group(1))
                continue
            m = article_price.match(line)
            if not m or last_qty is None:
                continue
            ref = clean(m.group(1)); short_desc = clean(m.group(2))
            pu = fr_float(m.group(4)); amount = fr_float(m.group(5)); qty = last_qty
            # La désignation commerciale détaillée est généralement 1-3 lignes après.
            desc = short_desc
            for j in range(i + 1, min(i + 5, len(lines))):
                cand = clean(lines[j]); low = cand.lower()
                if not cand or low == "agence" or "eco-contribution" in low or "éco-contribution" in low:
                    continue
                if article_price.match(cand) or status_qty.search(cand):
                    break
                desc = cand; break
            if qty is not None and pu is not None and amount is not None and abs(qty * pu - amount) <= max(0.12, abs(amount) * 0.004):
                rows.append({"Référence": ref, "Désignation": desc, "Quantité": qty, "Prix unitaire": pu})
            last_qty = None

    elif supplier == "PROLIANS":
        # Désignation sur la ligne précédente, puis réf / quantité / unité / PU.
        for i, line in enumerate(lines):
            m = re.match(
                r"^\d{5,}\s+(\d+(?:[.,]\d+)?)\s+[A-Z]\s+(\d+(?:[.,]\d+)?)"
                r"(?:\s+\d+(?:[.,]\d+)?){2,}.*$",
                line, re.I
            )
            if m and i > 0:
                desc = re.sub(r"\s+F\d+$", "", lines[i - 1]).strip()
                rows.append({"Désignation": desc, "Quantité": fr_float(m.group(1)), "Prix unitaire": fr_float(m.group(2))})

    elif supplier == "LORFLEX":
        # Format LORFLEX :
        # Poste | Article | Description | Quantité | unité | PU Brut |
        # Conditions | remise | PU Net | Montant Net
        #
        # Important : le PDF contient beaucoup d'autres nombres.
        # On ne lit que la zone du tableau, entre son en-tête et "Total postes".
        in_articles = False
        pat = re.compile(
            r"^(\d{1,4})\s+"                       # Poste
            r"([A-Z0-9._/-]+)\s+"                  # Article
            r"(.+?)\s+"                            # Description
            r"(\d+(?:[.,]\d+)?)\s+"                # Quantité
            r"(PC|PCE|PCS|U|UN|ML|M|ENS|LOT)\s+"   # Unité
            r"(\d[\d .]*[,.]\d{2})\s+"             # PU Brut
            r"Remise\s+[-+]?\d+(?:[.,]\d+)?%\s+"  # Conditions
            r"(\d[\d .]*[,.]\d{2})\s+"             # PU Net
            r"(\d[\d .]*[,.]\d{2})$",              # Montant Net
            re.I
        )

        for line in lines:
            up = line.upper()

            if ("POSTE" in up and "ARTICLE" in up and "DESCRIPTION" in up
                    and ("QUANTITÉ" in up or "QUANTITE" in up)):
                in_articles = True
                continue

            if in_articles and ("TOTAL POSTES" in up or "TOTAL BRUT HT" in up):
                break

            if not in_articles:
                continue

            m = pat.match(line)
            if not m:
                continue

            reference = clean(m.group(2))
            desc = clean(m.group(3))
            qty = fr_float(m.group(4))
            pu_net = fr_float(m.group(7))
            montant_net = fr_float(m.group(8))

            if qty is None or pu_net is None or montant_net is None:
                continue

            # Tolérance de quelques centimes : certains PU nets sont affichés
            # à 2 décimales alors que le montant peut provenir d'un calcul interne.
            if abs((qty * pu_net) - montant_net) > 0.08:
                continue

            rows.append({
                "Référence": reference,
                "Désignation": desc,
                "Quantité": qty,
                "Prix unitaire": round(montant_net / qty, 8) if qty and abs(qty * pu_net - montant_net) >= 0.005 else pu_net,
                "Prix unitaire imprimé": pu_net,
                "Montant imprimé": montant_net
            })

    elif supplier == "RICHARDSON":
        pat = re.compile(
            r"^\S+\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+U\s+"
            r"(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": clean(m.group(1)), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

    elif supplier == "FRANS BONHOMME":
        pat = re.compile(r"^(\d{5}\s*[A-Z])\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:ML|PCE|U|UN|M|KG)\s+(\d+(?:[.,]\d+)?)\s*€?\s+(\d+(?:[.,]\d+)?)\s*€?$", re.I)
        for line in lines:
            m = pat.match(line)
            if m:
                q, pu, amount = (fr_float(m.group(i)) for i in (3, 4, 5))
                if q and abs(q * pu - amount) < .02:
                    rows.append({"Référence": re.sub(r"\s+", "", m.group(1)), "Désignation": clean(m.group(2)), "Quantité": q, "Prix unitaire": pu})

    elif supplier == "H-TUBE / POINT PLASTIQUE":
        pat = re.compile(
            r"^(.+?)\s+\S+\s+(\d+(?:[.,]\d+)?)\s+(?:ML|UN|PCE|U)\s+"
            r"\d+(?:[.,]\d+)?(?:\s+\S+)?\s+(\d+(?:[.,]\d+)?)\s+"
            r"\d+(?:[.,]\d+)?\s+\d+$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m and not line.upper().startswith("EAN13"):
                rows.append({"Désignation": clean(m.group(1)), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

        # Page 2 : frais de port et éco-contribution font partie du Total HT.
        if re.search(r"PORT SUR VENTE\s+9915001M\s+1\s+300[,.]00", text, re.I):
            rows.append({"Désignation": "FRAIS DE PORT", "Quantité": 1.0, "Prix unitaire": 300.0})
        m_eco = re.search(r"Eco-contribution\s*:\s*(\d+(?:[.,]\d+)?)\s*EUR", text, re.I)
        if m_eco:
            rows.append({"Désignation": "ÉCO-CONTRIBUTION", "Quantité": 1.0, "Prix unitaire": fr_float(m_eco.group(1))})

    elif supplier == "RODACLIM":
        pat = re.compile(
            r"^\S+\s+(.+?)\s+(?:Pièce|Piece|PCE|U)\s+"
            r"(\d+(?:[.,]\d+)?)\s+\d+(?:[.,]\d+)?(?:\s+\d+%)?\s+"
            r"(\d+(?:[.,]\d+)?)\s+\d+(?:[.,]\d+)?\s+\d{2}/\d{2}/\d{2}$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": clean(m.group(1)), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

    elif supplier == "PACK SERVICE":
        # Le PDF contient beaucoup de nombres dans l'en-tête (téléphone, RIB, IBAN).
        # On ne lit que la zone comprise entre l'en-tête du tableau articles
        # et le récapitulatif NET H.T.
        in_articles = False
        pat = re.compile(
            r"^([A-Z0-9][A-Z0-9._/-]*)\s+(.+?)\s+"
            r"(\d+(?:[.,]\d+)?)\s+"
            r"(\d+(?:[.,]\d+)?)\s+"
            r"(\d+(?:[.,]\d+)?)\s+(\d+)$",
            re.I
        )
        for line in lines:
            up = line.upper()
            if "RÉFÉRENCE" in up and "DÉSIGNATION" in up and ("QTÉ" in up or "QTE" in up):
                in_articles = True
                continue
            if in_articles and ("NET H.T." in up or "TOTAL DEVIS HT" in up):
                break
            if not in_articles:
                continue

            m = pat.match(line)
            if not m:
                continue

            reference = clean(m.group(1))
            desc = clean(m.group(2))
            qty = fr_float(m.group(3))
            pu = fr_float(m.group(4))
            montant = fr_float(m.group(5))

            # Contrôle de cohérence : quantité × PU doit correspondre au montant net imprimé.
            if qty is None or pu is None or montant is None:
                continue
            if abs((qty * pu) - montant) > max(0.08, abs(montant) * 0.002):
                continue

            rows.append({
                "Référence": reference,
                "Désignation": desc,
                "Quantité": qty,
                "Prix unitaire": pu
            })

    elif supplier == "FRITEC":
        # Ligne d'entête article : position, quantité, unité, référence, PU, date.
        pat = re.compile(
            r"^\d+\s+(\d+(?:[.,]\d+)?)\s+(?:m|pc|pce|u|ml|kg)\s+\S+\s+"
            r"(\d+(?:[.,]\d+)?)\s+\d{2}[./]\d{2}[./]\d{2}$",
            re.I
        )
        for i, line in enumerate(lines):
            m = pat.match(line)
            if not m:
                continue
            desc_parts = []
            for nxt in lines[i + 1:i + 4]:
                if nxt.lower().startswith("code:") or re.match(r"^\d+\s+\d", nxt):
                    break
                # Ignore un montant isolé placé avant la désignation.
                if re.fullmatch(r"\d+(?:[.,]\d+)", nxt):
                    continue
                desc_parts.append(nxt)
            desc = clean(" ".join(desc_parts))
            if desc:
                rows.append({"Désignation": desc, "Quantité": fr_float(m.group(1)), "Prix unitaire": fr_float(m.group(2))})

    return rows

def article_sum(rows):
    """Arrondi commercial par ligne, comme sur les documents fournisseurs."""
    return float(sum((Decimal(str(r.get("Quantité", 0) or 0)) * Decimal(str(r.get("Prix unitaire", 0) or 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for r in rows))


def explicit_eco_charges(text):
    # Un récapitulatif ne se cumule pas avec son détail par article.
    patterns = [
        r"DONT ECO-PARTICIPATION HT\s+([0-9][0-9 .]*[,.][0-9]{2})",
        r"Dont\s+(?:éco|eco)-?participation\s+HT\s*:\s*([0-9][0-9 .]*[,.][0-9]{2})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return [{"label": "ÉCO-CONTRIBUTION", "amount": fr_float(m.group(1))}]
    # VIM : colonne d'éco-participation dans le récapitulatif de facture.
    if re.search(r"Éco\.\s*Particip\.", text, re.I):
        m = re.search(r"^Pro\s+([0-9][0-9 .]*[,.][0-9]{2})\s*$", text, re.M | re.I)
        if m:
            return [{"label": "ÉCO-CONTRIBUTION", "amount": fr_float(m.group(1))}]
    # Anconetti : chaque ligne REP représente une contribution facturée.
    amounts = []
    for line in text.splitlines():
        if re.match(r"^\s*454\s*ECO\s+CONTRIBUTION", line, re.I):
            m = re.search(r"(\d+[,.]\d+)\s+(?:PCE|FCE|ML|BTE|U|KG)\s+(\d+[,.]\d+)\s+(\d+[,.]\d+)\s*$", line, re.I)
            if m:
                q, pu, amount = (fr_float(m.group(i)) for i in (1, 2, 3))
                if abs(q * pu - amount) < .011:
                    amounts.append(amount)
    if amounts:
        return [{"label": "ÉCO-CONTRIBUTION", "amount": round(sum(amounts), 2)}]
    m = re.search(r"DONT\s*ECOPART\s*([0-9]+[,.][0-9]{2})", text, re.I)
    if m:
        return [{"label": "ÉCO-CONTRIBUTION", "amount": fr_float(m.group(1))}]
    return None


@lru_cache(maxsize=1)
def rapid_ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
        return RapidOCR()
    except ImportError as exc:
        raise RuntimeError("Ce PDF nécessite l'OCR. Ajoutez rapidocr_onnxruntime et pypdfium2 aux dépendances de PriceFlow, puis redémarrez l'application.") from exc


def image_ocr(image):
    try:
        import numpy as np
        import cv2
    except (ImportError, OSError) as exc:
        raise RuntimeError("OCR indisponible sur le serveur. Installez les dépendances du requirements.txt fourni (dont opencv-python et rapidocr_onnxruntime), ainsi que packages.txt sur Streamlit Cloud, puis redémarrez l'application.") from exc
    array = np.array(image.convert("RGB"))
    # Redresse les scans avant de reconstruire les lignes du tableau.
    edges = cv2.Canny(cv2.cvtColor(array, cv2.COLOR_RGB2GRAY), 50, 150)
    segments = cv2.HoughLinesP(edges, 1, np.pi / 1800, 100, minLineLength=array.shape[1] * .35, maxLineGap=30)
    angles = []
    for line in segments if segments is not None else []:
        x1, y1, x2, y2 = np.asarray(line).reshape(-1)
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 5:
            angles.append(angle)
    if angles:
        matrix = cv2.getRotationMatrix2D((array.shape[1] / 2, array.shape[0] / 2), float(np.median(angles)), 1)
        array = cv2.warpAffine(array, matrix, (array.shape[1], array.shape[0]), borderValue=(255, 255, 255))
    result, _ = rapid_ocr_engine()(array, use_cls=False)
    lines = []
    for box, value, confidence in sorted(result or [], key=lambda r: sum(p[1] for p in r[0]) / 4):
        y = sum(p[1] for p in box) / 4
        height = max(p[1] for p in box) - min(p[1] for p in box)
        if not lines or abs(lines[-1][0] - y) > height * .6:
            lines.append([y, []])
        lines[-1][1].append((box[0][0], value))
    return "\n".join(" ".join(value for x, value in sorted(line)) for y, line in lines)


@lru_cache(maxsize=8)
def pdf_page_texts(pdf_bytes):
    pages = []
    terms_follow = False
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            # Les CGV annexées en image ne font pas partie du tableau commercial.
            # Ne pas imposer l'OCR si le document annonce explicitement ces annexes.
            if not text.strip() and terms_follow:
                pages.append(("", False))
                continue
            if (detect_supplier(text) == "ANCONETTI" and detect_total_ht(text, "ANCONETTI") is not None
                    and re.search(r"vente.{0,15}ci-annex", text, re.I)):
                terms_follow = True
            area = sum(max(0, im["x1"] - im["x0"]) * max(0, im["bottom"] - im["top"]) for im in page.images)
            image_table = area > page.width * page.height * .15 and len(re.findall(r"\d+[,.]\d{2}", text)) < 4
            incomplete_table = (len(text) < 1000 and re.search(r"D.signation|Total\s*:", text, re.I)
                                and len(re.findall(r"\d+[,.]\d{2}", text)) < 4)
            scanned = len(re.sub(r"\s", "", text)) < 120 or image_table or bool(incomplete_table)
            if scanned:
                text = image_ocr(page.to_image(resolution=220).original)
            elif detect_supplier(text) == "Fournisseur non identifié" and page.images:
                # Un logo image peut être le seul nom du fournisseur (VIM).
                header = image_ocr(page.crop((0, 0, page.width, min(100, page.height))).to_image(resolution=180).original)
                if detect_supplier(header) != "Fournisseur non identifié":
                    text = header + "\n" + text
            pages.append((text, scanned))
    return tuple(pages)


@lru_cache(maxsize=8)
def purchase_documents(pdf_bytes):
    """Sépare les BL identifiés dans un même scan, conserve leurs pages de suite."""
    page_texts = pdf_page_texts(pdf_bytes)
    groups = []
    for index, (text, scanned) in enumerate(page_texts):
        supplier = detect_supplier(text)
        number = detect_document_number(text, supplier)
        # Ne scinde que les bons Anconetti portant leur propre numéro de débit.
        key = number if supplier == "ANCONETTI" and re.search(r"D\s*E\s*B\s*I\s*T", text, re.I) and number != "Non détecté" else None
        if not groups or (key and groups[-1][0] and key != groups[-1][0]):
            groups.append([key, []])
        elif key and groups[-1][0] is None:
            groups[-1][0] = key
        groups[-1][1].append(index)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    documents = []
    for key, indexes in groups:
        if len(groups) == 1:
            data = pdf_bytes
        else:
            writer = PdfWriter()
            for index in indexes:
                writer.add_page(reader.pages[index])
            buffer = io.BytesIO()
            writer.write(buffer)
            data = buffer.getvalue()
        text = "\n".join(page_texts[i][0] for i in indexes)
        documents.append((key or "Document", data, text, any(page_texts[i][1] for i in indexes)))
    return tuple(documents)


def generic_text_rows(text):
    """Moteur universel Achats : lignes article détectées par structure et contrôle qté × PU = montant."""
    rows=[]
    raw_lines=[clean(x) for x in text.splitlines() if clean(x)]
    # Certains moteurs PDF coupent la dernière colonne (montant/TVA) sur la ligne suivante.
    lines=[]
    i=0
    while i < len(raw_lines):
        cur=raw_lines[i]
        if i+1 < len(raw_lines) and re.match(r"^[A-Z0-9][A-Z0-9._/-]{2,24}\s+", cur):
            nxt=raw_lines[i+1]
            if re.match(r"^[0-9][0-9 .]*[,.][0-9]{2,4}(?:\s+[A-Z])?$", nxt):
                cur=clean(cur+" "+nxt); i+=1
        lines.append(cur); i+=1
    unit=r"(?:PCE|PCS|PC|PI|PIECE|PIÈCE|U|UN|ML|M|MÈTRE|METRE|KG|ENS|LOT|BTE|BCE|RL|CTN|SACHET|PAQ|COL|L)"
    num=r"[0-9][0-9 .]*[,.][0-9]{1,4}"

    def add(ref, desc, q, pu, amt):
        ref,desc=clean(ref),clean(desc); q,pu,amt=fr_float(q),fr_float(pu),fr_float(amt)
        if not ref or not re.search(r"\d", ref) or not desc or q is None or pu is None or amt is None or q<=0 or pu<0: return
        low=desc.lower()
        if any(x in low for x in ["total ht","total h.t","client acheteur","commande n°","votre référence","reste à livrer","eco contribution","éco contribution","contribution rep"]): return
        if abs(q*pu-amt)>max(.12,abs(amt)*.004): return
        rows.append({"Référence":ref,"Désignation":desc,"Quantité":q,"Prix unitaire":pu})

    patterns=[
      # CLIM+ : REF + nombre + désignation + qté + unité + PU + montant + TVA
      re.compile(rf"^(?P<ref>\d{{5,}})\s+\d+(?:[.,]\d+)?\s+(?P<desc>.+?)\s+(?P<q>\d+(?:[.,]\d+)?)\s+{unit}\s+(?P<pu>{num})\s+(?P<amt>{num})\s+[A-Z]$",re.I),
      # FIRST : REF + conditionnement + désignation + qté + unité + PU + montant
      re.compile(rf"^(?P<ref>[A-Z0-9][A-Z0-9._/-]{{2,24}})\s+\d+(?:[.,]\d+)?(?:\s+\w+)?\s+(?P<desc>.+?)\s+(?P<q>\d+(?:[.,]\d+)?)\s+{unit}\s+(?P<pu>{num})\s+(?P<amt>{num})$",re.I),
      # Standard
      re.compile(rf"^(?P<ref>[A-Z0-9][A-Z0-9._/-]{{2,24}})\s+(?P<desc>.+?)\s+(?P<q>\d+(?:[.,]\d+)?)\s+{unit}\s+(?P<pu>{num})\s+(?P<amt>{num})(?:\s+[A-Z])?$",re.I),
      # VIM : pas toujours de colonne unité ; éventuel DEEE reste dans la désignation et sera retiré
      re.compile(rf"^(?P<ref>[0-9A-Z]{{5,}})\s+(?P<desc>.+?)\s+(?P<q>\d+(?:[.,]\d+)?)\s+(?P<pu>{num})\s+(?P<amt>{num})$",re.I),
    ]
    for line in lines:
        low=line.lower()
        if any(k in low for k in ["total ht","total h.t","sous total","contribution rep","eco-contribution","éco-contribution","dont éco","dont eco"]): continue
        for pat in patterns:
            m=pat.match(line)
            if not m: continue
            desc=clean(m.group("desc"))
            add(m.group('ref'),desc,m.group('q'),m.group('pu'),m.group('amt'))
            break
    return rows

def dedupe(rows):
    out, seen = [], set()
    for r in rows:
        key = (clean(r["Désignation"]).lower(), round(float(r["Quantité"]), 5), round(float(r["Prix unitaire"]), 5))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def ocr_pdf_text(pdf_bytes):
    """OCR local de secours : utilisé seulement si le PDF n'a pas de couche texte exploitable."""
    if not OCR_AVAILABLE:
        return ""
    pages = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # 2,5x donne un bon compromis précision / temps sur les BL A4 scannés.
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            image = ImageOps.grayscale(image)
            txt = pytesseract.image_to_string(image, lang="fra", config="--psm 4")
            pages.append(txt or "")
        doc.close()
    except Exception:
        return ""
    return "\n".join(pages)

def best_pdf_text(pdf_bytes):
    return "\n".join(text for text, scanned in pdf_page_texts(pdf_bytes))


def first_pdf_designations(pdf, rows):
    """Lit les libellés FIRST séparément du conditionnement qui déborde visuellement."""
    for page in pdf.pages:
        words = page.extract_words()
        header = next((w for w in words if re.fullmatch(r"D.signation", w["text"], re.I)), None)
        quantity = next((w for w in words if re.fullmatch(r"Quantit.", w["text"], re.I)), None)
        if not header or not quantity:
            continue
        runs, run = [], []
        for char in page.chars:
            if run and (abs(char["top"] - run[-1]["top"]) > 2 or char["x0"] < run[-1]["x0"] - 1):
                runs.append(run)
                run = []
            run.append(char)
        if run:
            runs.append(run)
        for row in rows:
            ref = row.get("Référence", "")
            matches = [w for w in words if w["text"] == ref and w["x0"] < header["x0"]]
            if len(matches) != 1:
                continue
            y = matches[0]["top"]
            labels = [r for r in runs if abs(r[0]["x0"] - header["x0"]) < 2 and abs(r[0]["top"] - y) < 2]
            if len(labels) == 1:
                label = clean("".join(c["text"] for c in labels[0] if c["x0"] < quantity["x0"]))
                if label:
                    row["Désignation"] = label
    return rows


def charges_outside_total_ht(text, supplier):
    """FIRST affiche la REP après le Total HT ; vérifier aussi l'équation TTC."""
    if supplier != "FIRST ROBINETTERIE":
        return False
    def amount(label):
        m = re.search(label + r"\s*:?\s*([0-9][0-9 .]*[,.][0-9]{2})", text, re.I)
        return fr_float(m.group(1)) if m else None
    ht, vat, ttc, rep = [amount(x) for x in (r"Total HT", r"Total TVA", r"Total TTC", r"Contribution REP")]
    return (all(x is not None for x in (ht, vat, ttc, rep)) and rep > 0
            and abs(round(ttc - ht - vat - rep, 2)) < 0.01)


def extract_document(pdf_bytes, text_override=None):
    if text_override is None:
        parts = purchase_documents(pdf_bytes)
        if len(parts) > 1:
            raise ValueError("Ce fichier contient plusieurs bons : choisissez le bon dans Achats / Fournisseurs.")
        text_override = parts[0][2]
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = text_override if text_override is not None else best_pdf_text(pdf_bytes)
        supplier = detect_supplier(text)
        number = detect_document_number(text, supplier)
        total_ht = detect_total_ht(text, supplier)
        extra_charges = detect_extra_charges(text)
        if charges_outside_total_ht(text, supplier):
            for charge in extra_charges:
                if charge["label"] == "ÉCO-CONTRIBUTION":
                    charge["outside_total_ht"] = True

        # On essaie systématiquement plusieurs moteurs : tableau PDF, parseur fournisseur
        # et parseur générique. Le meilleur résultat est retenu au lieu de dépendre
        # d'un seul gabarit de BL/devis.
        table_candidate = table_rows(pdf)
        specific_candidate = text_rows(text, supplier) if supplier != "Fournisseur non identifié" else []
        generic_candidate = generic_text_rows(text)
        candidates = [c for c in [specific_candidate, table_candidate, generic_candidate] if c]

        def candidate_score(candidate):
            # Priorité à un contrôle financier cohérent ; à égalité, au plus grand
            # nombre de vraies lignes articles reconnues.
            article_total = article_sum(candidate)
            if total_ht is None:
                return (0, len(candidate), article_total)
            extras = round(sum(float(x.get("amount", 0) or 0) for x in extra_charges), 2)
            gaps = [abs(float(total_ht) - article_total), abs(float(total_ht) - article_total - extras)]
            gap = min(gaps)
            # Une extraction qui dépasse fortement le total est presque toujours parasite.
            penalty = 10000 if article_total > float(total_ht) * 1.03 + 1 else 0
            return (-(gap + penalty), len(candidate), article_total)

        rows = max(candidates, key=candidate_score) if candidates else []
        # Une couche texte longue n'exclut pas une extraction incomplète.
        # Une deuxième résolution peut aussi corriger un caractère OCR mal lu.
        score = candidate_score(rows) if rows else (-float("inf"), 0, 0)
        if not rows or (total_ht is not None and score[0] < -0.02):
            retry_text = "\n".join(image_ocr(page.to_image(resolution=140).original) for page in pdf.pages)
            retry_supplier = detect_supplier(retry_text)
            retry_total = detect_total_ht(retry_text, retry_supplier)
            same_total = total_ht is None or (retry_total is not None and abs(total_ht - retry_total) < .011)
            if same_total and retry_supplier in (supplier, "Fournisseur non identifié"):
                retry_rows = text_rows(retry_text, supplier)
                if retry_rows and candidate_score(retry_rows) > score:
                    rows = retry_rows
                    retry_charges = detect_extra_charges(retry_text)
                    if retry_charges:
                        extra_charges = retry_charges
                    if total_ht is None:
                        total_ht = retry_total

        # Ne pas supprimer les lignes identiques chez AREDIS :
        # un même article peut être réellement livré/facturé deux fois sur le BL
        # (notamment lors d'un passage de page).
        # Les lignes physiques répétées restent des achats distincts.

        if supplier == "RICHARDSON" and total_ht is not None:
            extracted = round(sum(float(r["Quantité"]) * float(r["Prix unitaire"]) for r in rows), 2)
            missing = round(float(total_ht) - extracted, 2)
            eco_prices = [
                round(float(r["Prix unitaire"]), 2)
                for r in rows
                if "ECOPARTICIPATION" in clean(r["Désignation"]).upper()
            ]
            if missing > 0 and missing in eco_prices:
                rows.append({"Désignation": "ECOPARTICIPATION", "Quantité": 1.0, "Prix unitaire": missing})

        if supplier == "FIRST ROBINETTERIE":
            rows = first_pdf_designations(pdf, rows)
        return rows, supplier, number, total_ht, extra_charges

def extract_pdf_text(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def market_pdf_pages(pdf_bytes):
    """Extrait le texte page par page pour conserver une source vérifiable."""
    pages=[]
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i,page in enumerate(pdf.pages,1):
            txt=(page.extract_text(x_tolerance=2,y_tolerance=3) or "").replace("\x00", "")
            lines=[clean(x) for x in txt.splitlines() if clean(x)]
            pages.append({"page":i,"text":"\n".join(lines),"lines":lines})
    return pages

def _norm_source(s):
    return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()).strip()

def _source_verified(quote, page_text):
    q=_norm_source(quote); t=_norm_source(page_text)
    if len(q)<18: return False
    if q in t: return True
    # tolère une citation raccourcie : ses premiers mots doivent être réellement présents
    words=q.split()
    return len(words)>=8 and " ".join(words[:8]) in t

def _response_text(payload):
    if isinstance(payload,dict) and payload.get("output_text"):
        return payload["output_text"]
    parts=[]
    for item in (payload.get("output",[]) if isinstance(payload,dict) else []):
        for c in item.get("content",[]) or []:
            if isinstance(c,dict) and c.get("text"): parts.append(c["text"])
    return "\n".join(parts)

def analyse_market_with_ai(documents):
    api_key=st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        return None, "Clé OPENAI_API_KEY absente des Secrets Streamlit."
    blocks=[]; page_index={}
    for d in documents:
        for pg in d["pages"]:
            key=(d["name"],int(pg["page"])); page_index[key]=pg["text"]
            blocks.append(f'=== DOCUMENT: {d["name"]} | PAGE: {pg["page"]} ===\n{pg["text"]}')
    corpus="\n\n".join(blocks)
    # Garde une marge confortable ; les dossiers énormes seront traités par lots dans une évolution ultérieure.
    if len(corpus)>350000:
        corpus=corpus[:350000]
    instruction="""Tu es un assistant de revue de pièces marché spécialisé CVC, plomberie et génie climatique pour une entreprise de travaux. Analyse UNIQUEMENT le corpus fourni. Ne complète jamais avec tes connaissances. Recherche: prestations; équipements (chaufferie, chaudières, PAC, groupe froid, climatisation, CTA/VMC, ventilo-convecteurs, plomberie EF/ECS/EU/EV, condensats, fumisterie, GTB/régulation); matériaux et réseaux (acier, galva, inox, cuivre, multicouche, PER, PVC, PEHD), DN/diamètres, assemblages, calorifuge et supports; contraintes chantier; limites de prestations et interfaces avec GO, électricité, GTB, faux-plafonds, SSI et autres lots; divergences CCTP/DPGF; prestations du CCTP sans poste DPGF clairement identifiable; contradictions potentielles. Une absence de ligne DPGF distincte n'est PAS une erreur: catégorie points_verifier. Une contradiction doit avoir une preuve. Pour chaque constat, fournis une citation EXACTE copiée du corpus, son document, sa page et si possible le paragraphe. N'invente jamais une source. Retourne uniquement du JSON valide, sans markdown, sous la forme {"projet":"...","lot":"...","synthese":"...","findings":[{"category":"prestations|points_verifier|interfaces|incoherences","title":"...","analysis":"...","document":"nom exact","page":1,"section":"...","quote":"citation exacte"}]}. Maximum 35 constats, en privilégiant ceux utiles à un conducteur de travaux CVC/plomberie."""
    payload={"model":"gpt-5.6-luna","input":[{"role":"system","content":instruction},{"role":"user","content":corpus}],"reasoning":{"effort":"medium"},"max_output_tokens":12000}
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=180) as resp: raw=json.loads(resp.read().decode("utf-8"))
        txt=_response_text(raw).strip()
        txt=re.sub(r"^```(?:json)?\s*|\s*```$","",txt,flags=re.I|re.S)
        data=json.loads(txt)
    except Exception as e:
        return None, f"Analyse IA impossible : {e}"
    valid=[]
    for f in data.get("findings",[]):
        try: key=(str(f.get("document","")),int(f.get("page",0)))
        except Exception: continue
        page_text=page_index.get(key,"")
        if page_text and _source_verified(f.get("quote",""),page_text):
            f["source_verified"]=True; valid.append(f)
    data["findings"]=valid
    return data, None

def market_report_excel(data):
    rows=[]
    labels={"prestations":"Prestation identifiée","points_verifier":"Point à vérifier","interfaces":"Interface / limite","incoherences":"Incohérence potentielle"}
    for f in data.get("findings",[]):
        rows.append({"Catégorie":labels.get(f.get("category"),f.get("category")),"Sujet":f.get("title"),"Analyse":f.get("analysis"),"Document":f.get("document"),"Page":f.get("page"),"Paragraphe":f.get("section"),"Passage source exact":f.get("quote")})
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="xlsxwriter") as writer:
        pd.DataFrame(rows).to_excel(writer,index=False,sheet_name="Analyse Marché")
        ws=writer.sheets["Analyse Marché"]; ws.set_column("A:A",22); ws.set_column("B:B",35); ws.set_column("C:C",60); ws.set_column("D:D",38); ws.set_column("E:F",14); ws.set_column("G:G",90)
    out.seek(0); return out

def fmt_money(value):
    """Affiche un montant au format français."""
    if value is None:
        return "Non détecté"
    try:
        return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", " ")
    except (TypeError, ValueError):
        return "Non détecté"


def rental_supplier(text):
    low = text.lower()
    if "brandfrance.fr" in low or ("brand france" in low and "devis location" in low):
        return "BRAND FRANCE / SGB HÜNNEBECK"
    if "loxam" in low and ("offre de location" in low or "retour de location" in low):
        return "LOXAM"
    if "actis location" in low or "actemis vitrolles" in low:
        return "ACTIS LOCATION"
    if "acces-industrie.com" in low or "accès industrie" in low or "acces industrie" in low:
        return "ACCÈS INDUSTRIE"
    return "Loueur non identifié"

def rental_supplements(text, result, day_rate):
    """Estime uniquement les suppléments annoncés dans l'offre Accès Industrie."""
    section = re.search(r"les éléments suivants seront facturés en supplément\s*:(.*?)(?:Sous réserve|CONDITIONS GÉNÉRALES|$)", text, re.I | re.S)
    if not section:
        return []
    conditions = clean(section.group(1))
    lines = result["Lignes"]
    rent = sum(x["Montant HT"] for x in lines if x["Désignation"] == "LOCATION")
    electric = bool(re.search(r"ELECT|ÉLECT", result["Matériel"], re.I))
    supplements = []

    def add(label, amount, calculation):
        amount = float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        supplements.append({"Désignation": label, "Calcul / condition": calculation, "Montant estimé HT": amount})

    number = r"(\d+(?:[,.]\d+)?)"
    m = re.search(r"renonciation à recours[^:]*:\s*" + number + r"\s*%", conditions, re.I)
    if m and day_rate is not None:
        try:
            calendar_days = (datetime.strptime(result["Date fin"], "%d/%m/%Y") - datetime.strptime(result["Date début"], "%d/%m/%Y")).days + 1
        except ValueError:
            calendar_days = 0
        if calendar_days > 0:
            rate = fr_float(m.group(1))
            add("RENONCIATION À RECOURS", Decimal(str(day_rate)) * calendar_days * Decimal(str(rate)) / 100,
                f"{day_rate:g} € × {calendar_days} jours calendaires × {rate:g} %")
    m = re.search(r"nettoyage[^:]*:\s*" + number + r"\s*€\s*pour une machine électrique", conditions, re.I)
    if m and electric:
        add("NETTOYAGE STANDARD", fr_float(m.group(1)), "Machine électrique — facturé en fin de contrat")
    m = re.search(r"participation au recyclage\s*:\s*" + number + r"\s*%", conditions, re.I)
    if m and rent:
        rate = fr_float(m.group(1))
        add("PARTICIPATION AU RECYCLAGE", Decimal(str(rent)) * Decimal(str(rate)) / 100, f"{rent:g} € de location × {rate:g} %")
    m = re.search(r"forfait de charge électrique complète de\s*" + number + r"\s*€", conditions, re.I)
    if m and electric:
        add("RECHARGE ÉLECTRIQUE", fr_float(m.group(1)), "Sur les machines concernées — application à confirmer")
    m = re.search(r"surcharge frais transport[^:]*:\s*" + number + r"\s*% du transport aller et\s*" + number + r"\s*% du transport retour", conditions, re.I)
    if m:
        outbound = sum(x["Montant HT"] for x in lines if x["Désignation"] == "LIVRAISON")
        inbound = sum(x["Montant HT"] for x in lines if x["Désignation"] == "RÉCUPÉRATION")
        a, b = fr_float(m.group(1)), fr_float(m.group(2))
        add("SURCHARGE TRANSPORT", Decimal(str(outbound)) * Decimal(str(a)) / 100 + Decimal(str(inbound)) * Decimal(str(b)) / 100,
            f"{outbound:g} € aller × {a:g} % + {inbound:g} € retour × {b:g} %")
    return supplements


def extract_rental(pdf_bytes):
    text = extract_pdf_text(pdf_bytes)
    flat = re.sub(r"\s+", " ", text.replace("\u00a0", " "))
    supplier = rental_supplier(text)
    result = {
        "Loueur": supplier,
        "N° document": "Non détecté",
        "Matériel": "Non détecté",
        "Date début": "",
        "Date fin": "",
        "Durée": "",
        "Total HT document": None,
        "Lignes": [],
        "Suppléments estimés": [],
        "Points à vérifier": [],
        "Conditions estimation": "Sous réserve des conditions du devis et d'un accord contraire ; recharge à confirmer.",
    }

    if supplier == "BRAND FRANCE / SGB HÜNNEBECK":
        m = re.search(r"Devis Location Simple\s*N[°º]\s*([\d-]+)\s*V\.?\s*(\d+)", text, re.I)
        if m:
            result["N° document"] = f"{m.group(1)} V.{m.group(2)}"
        m = re.search(r"DUREE PREVISIONNELLE DE CHANTIER\s*:\s*(\d+)\s*Jour\(s\).*?Du\s*(\d{2}/\d{2}/\d{4})\s*au\s*(\d{2}/\d{2}/\d{4})", flat, re.I)
        if m:
            result["Durée"] = f"{m.group(1)} jours calendaires (prévisionnels)"
            result["Date début"], result["Date fin"] = m.group(2), m.group(3)
        materials = []
        # Colonnes : code, désignation, durée, PU, quantité, total puis dimensions.
        for m in re.finditer(r"(?m)^\s*(FRN\w+)\s+(.+?)\s+(\d+)\s+(\d+[,.]\d{3})\s+(\d+)\s+([\d ]+[,.]\d{2})(?=\s|$)", text):
            ref, desc, duration, price, qty, amount = m.groups()
            materials.append(clean(desc))
            result["Lignes"].append({"Désignation": f"LOCATION — {ref} — {clean(desc)}", "Montant HT": fr_float(amount)})
        if materials:
            result["Matériel"] = " / ".join(materials)
        for m in re.finditer(r"(?m)^\s*FR\s+(TA|TR)\s+(.+?)\s+(\d+[,.]\d{3})\s+(\d+)\s+([\d ]+[,.]\d{2})\s*$", text):
            result["Lignes"].append({"Désignation": clean(m.group(2)), "Montant HT": fr_float(m.group(5))})
        # Les deux sous-totaux (par jour / services) ne sont pas un total du devis.
        result["Points à vérifier"] = [
            "Période prévisionnelle : date de début de location à confirmer.",
            "Transport susceptible de varier ; montage et démontage à la charge du client.",
            "Nettoyage, détérioration, pièces manquantes et annulation : frais éventuels non inclus dans l'estimation.",
        ]
        result["Conditions estimation"] = "Hypothèse d'une seule facture : contribution environnementale appliquée une fois. Dates et transport à confirmer ; frais éventuels exclus."
        m = re.search(r"Contribution environnement[^:]*:\s*(\d+[,.]\d{2})\s*€", text, re.I)
        if m:
            result["Suppléments estimés"].append({"Désignation": "CONTRIBUTION ENVIRONNEMENT", "Calcul / condition": "Par facture établie — hypothèse : 1 facture", "Montant estimé HT": fr_float(m.group(1))})

    elif supplier == "ACTIS LOCATION":
        # Numéro / total
        m = re.search(r"Offre de location\s*#(\d+)", text, re.I)
        if m:
            result["N° document"] = m.group(1)

        m = re.search(r"Total HT\s+([0-9 .]+[,.]\d{2})\s*€", text, re.I)
        if m:
            result["Total HT document"] = fr_float(m.group(1))

        # Matériel : privilégier la ligne explicite du devis.
        m = re.search(r"(?m)^Matériel\s*:\s*(.+?)(?:\s+N°\s*parc\s*:|\s+Référence\s*:|$)", text, re.I)
        if m:
            result["Matériel"] = clean(m.group(1))

        # Ligne principale de location : désignation + dates.
        m = re.search(
            r"Location\s+(.+?)\s+1\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+\d+\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+"
            r"du\s+(\d{2}/\d{2}/\d{4}).*?\s+au\s+(\d{2}/\d{2}/\d{4}).*?\((\d+)\s+jours?\)",
            flat, re.I
        )
        if m:
            # Si la ligne Matériel n'a pas été trouvée, utiliser la désignation de location.
            if result["Matériel"] == "Non détecté":
                result["Matériel"] = clean(m.group(1))
            result["Date début"] = m.group(2)
            result["Date fin"] = m.group(3)
            result["Durée"] = f"{m.group(4)} jours"

        # Garde-fous dates/durée
        if not result["Date début"]:
            m = re.search(r"Date de début\s+(\d{2}/\d{2}/\d{4})", text, re.I)
            if m:
                result["Date début"] = m.group(1)
        if not result["Durée"]:
            m = re.search(r"Durée initiale\s+(\d+\s+jours?)", text, re.I)
            if m:
                result["Durée"] = m.group(1)

        # Montants réellement imprimés sur le devis.
        m = re.search(
            r"Location\s+.+?\s+1\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+\d+\s+([0-9 ]+(?:[,.]\d+)?)\s*€",
            flat, re.I
        )
        if m:
            result["Lignes"].append({
                "Désignation": "LOCATION",
                "Montant HT": fr_float(m.group(1))
            })

        m = re.search(
            r"Renonciation à recours.*?\s+\d+\s+[0-9 ]+[,.]\d{2}\s*€\s+\d+\s+([0-9 ]+[,.]\d{2})\s*€",
            flat, re.I
        )
        if m:
            result["Lignes"].append({
                "Désignation": "RENONCIATION À RECOURS / ASSURANCE",
                "Montant HT": fr_float(m.group(1))
            })

        for label, pat in [
            ("LIVRAISON", r"LIVRAISON SUR CHANTIER\s+\d+\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+([0-9 ]+(?:[,.]\d+)?)\s*€"),
            ("RÉCUPÉRATION", r"RECUPERATION SUR CHANTIER\s+\d+\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+([0-9 ]+(?:[,.]\d+)?)\s*€"),
            ("CONTRIBUTION VERTE", r"Contribution verte\s*:\s*1%.*?\s+\d+\s+[0-9 ]+(?:[,.]\d+)?\s*€\s+([0-9 ]+(?:[,.]\d+)?)\s*€"),
        ]:
            m = re.search(pat, flat, re.I)
            if m:
                result["Lignes"].append({"Désignation": label, "Montant HT": fr_float(m.group(1))})

    elif supplier == "LOXAM":
        # Le texte LOXAM duplique parfois chaque caractère dans les libellés.
        # Le numéro imprimé après N° est lui aussi parfois doublé caractère par caractère.
        m = re.search(r"N[°º]\s+([0-9-]{16,})\s+dduu\s+\d{1,2}/\d{1,2}/\d{2}", text, re.I)
        if m:
            raw = m.group(1)
            if len(raw) % 2 == 0 and all(raw[i] == raw[i+1] for i in range(0, len(raw), 2)):
                raw = raw[::2]
            result["N° document"] = raw
        else:
            m = re.search(r"\b(\d{10,14})\s+du\s+\d{1,2}/\d{1,2}/\d{2}", text, re.I)
            if m:
                result["N° document"] = m.group(1)

        m = re.search(r"Date de début de location:\s*(\d{1,2}/\d{1,2}/\d{2})", text, re.I)
        if m:
            result["Date début"] = m.group(1)

        m = re.search(r"(\d+)\s*jrs\s+du\s+(\d{1,2}/\d{1,2}/\d{2})\s+au\s+(\d{1,2}/\d{1,2}/\d{2})", text, re.I)
        if m:
            result["Durée"] = f"{m.group(1)} jours"
            result["Date début"] = m.group(2)
            result["Date fin"] = m.group(3)

        # Matériel : les offres LOXAM placent souvent le code avant le libellé,
        # tandis que les retours de location commencent directement par le matériel.
        m = re.search(r"(?m)^\s*\d+\s+(.+?\b\d{3}-\d{4}\b.*?)\s*$", text)
        if m:
            result["Matériel"] = clean(m.group(1))
        else:
            m = re.search(r"\d{3}-\d{4}\s+(.+?)\n", text)
            if m:
                result["Matériel"] = clean(m.group(1))

        # Lignes chiffrées
        line_patterns = [
            ("LOCATION / TOTAL PÉRIODE", r"Total période\s+([0-9 ]+[,.]\d{2})"),
            ("GARANTIE DOMMAGES", r"(?:Garantie dommages|GGaarraannttiiee ddoommmmaaggeess)\s+([0-9 ]+[,.]\d{2})"),
            ("CONTRIBUTION VERTE", r"Contribution verte\s+([0-9 ]+[,.]\d{2})"),
            ("TRANSPORT ALLER", r"(?:Transport Aller|Forfait transport aller)\s+([0-9 ]+[,.]\d{2})"),
            ("TRANSPORT RETOUR", r"(?:Transport Retour|Forfait transport retour)\s+([0-9 ]+[,.]\d{2})"),
            ("CARBURANT GAZOLE NON ROUTIER", r"CARBURANT GAZOLE NON ROUTIER\s+[0-9 ]+[,.]\d{2}\s+([0-9 ]+[,.]\d{2})"),
            ("MAJORATION TRANSPORT RETOUR", r"MAJORATION TRANSPORT RETOUR.*?\s([0-9 ]+[,.]\d{2})\s*$"),
            ("MAJORATION TRANSPORT ALLER", r"MAJORATION TRANSPORT ALLER.*?\s([0-9 ]+[,.]\d{2})\s*$"),
            ("FORFAIT RECHARGE ÉLECTRIQUE", r"FORFAIT RECHARGE ELEC\.?[^\n]*?\s([0-9 ]+[,.]\d{2})\s*$"),
        ]
        for label, pat in line_patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                result["Lignes"].append({"Désignation": label, "Montant HT": fr_float(m.group(1))})

        # Total HT : offre prévisionnelle ou retour de location.
        m = re.search(
            r"(?:Total Prévisionnel HT|TToottaall PPrréévviissiioonnnneell HHTT|Total HT|TToottaall HHTT)\s+([0-9 ]+[,.]\d{2})",
            text, re.I
        )
        if m:
            result["Total HT document"] = fr_float(m.group(1))

    elif supplier == "ACCÈS INDUSTRIE":
        m = re.search(r"N[°º]?\s*(DEV-COM-[A-Z0-9]+)", text, re.I)
        if m:
            result["N° document"] = m.group(1)

        # Ligne article du tableau : CE08 CISEAU ELECT 8 m du lun. 08/06/2026 au ven. 12/06/2026 52,00 €/ jour
        m = re.search(
            r"(?m)^([A-Z0-9]+)\s+(.+?)\s+du\s+\w+\.\s*(\d{2}/\d{2}/\d{4})\s+au\s+\w+\.\s*(\d{2}/\d{2}/\d{4})\s+([0-9 ]+[,.]\d{2})\s*€\s*/\s*jour",
            text, re.I
        )
        day_rate = None
        if m:
            result["Matériel"] = clean(m.group(2))
            result["Date début"] = m.group(3)
            result["Date fin"] = m.group(4)
            day_rate = fr_float(m.group(5))

        m = re.search(r"Durée\s*:\s*(\d+)\s+jours?", text, re.I)
        days = int(m.group(1)) if m else None
        if days:
            result["Durée"] = f"{days} jours"

        if days and day_rate is not None:
            result["Lignes"].append({
                "Désignation": "LOCATION",
                "Montant HT": round(days * day_rate, 2)
            })

        m = re.search(r"Livraison\s+([0-9 ]+[,.]\d{2})\s*€", text, re.I)
        if m:
            result["Lignes"].append({"Désignation": "LIVRAISON", "Montant HT": fr_float(m.group(1))})

        m = re.search(r"Récupération\s+([0-9 ]+[,.]\d{2})\s*€", text, re.I)
        if m:
            result["Lignes"].append({"Désignation": "RÉCUPÉRATION", "Montant HT": fr_float(m.group(1))})

        # Les suppléments annoncés restent distincts des lignes de base et du total imprimé.
        result["Suppléments estimés"] = rental_supplements(text, result, day_rate)
        m = re.search(r"Total\s+HT\s*:?\s*([0-9 ]+[,.]\d{2})", text, re.I)
        result["Total HT document"] = fr_float(m.group(1)) if m else None

    return result

def comparison_key(desc):
    """Clé métier pour rapprocher des désignations fournisseurs différentes."""
    s = unicodedata.normalize("NFKD", clean(desc).upper()).encode("ascii", "ignore").decode()
    s = s.replace("Ø", "D")
    fee_words = ["PORT", "LIVRAISON", "CARBURANT", "ECO", "SURCHARGE", "FRAIS"]
    if any(w in s for w in fee_words):
        return "FRAIS | " + re.sub(r"\s+", " ", s)

    if "TUBE" in s and ("PEHD" in s or "PE100" in s):
        family = "TUBE PEHD"
    elif "TUBE" in s:
        family = "TUBE"
    elif "COUDE" in s:
        family = "COUDE"
    elif "CULOT" in s or "BRANCHEMENT" in s or "EMBRANC" in s:
        family = "CULOTTE/EMBRANCHEMENT"
    elif "MANCHON" in s or "COULISSE" in s:
        family = "MANCHON"
    elif "AUGMENT" in s or "REDUC" in s:
        family = "AUGMENTATION/REDUCTION"
    else:
        family = re.sub(r"[^A-Z0-9]+", " ", s).strip()[:45]

    dims = re.findall(r"(?:D|DN|DIA)\s*([0-9]{2,3})(?:\s*[Xx]\s*([0-9]{2,3}))?", s)
    if not dims:
        dims = re.findall(r"\b([0-9]{2,3})\s*[Xx]\s*([0-9]{2,3})\b", s)
    dimtxt = ""
    if dims:
        a, b = dims[0]
        dimtxt = a + (("X" + b) if b else "")

    angle = ""
    ma = re.search(r"\b(45|90)\s*(?:D|DEG|°)", s)
    if ma:
        angle = ma.group(1) + "°"

    joint = ""
    if re.search(r"\bFF\b", s): joint = "FF"
    elif re.search(r"\bMF\b", s): joint = "MF"

    return " | ".join(x for x in [family, angle, dimtxt, joint] if x)



# -------------------------------------------------------------------
# SUPABASE AUTH — comptes PriceFlow
# Les clés restent dans les Secrets Streamlit, jamais dans GitHub.
# -------------------------------------------------------------------
def _supabase_config():
    try:
        url = str(st.secrets["SUPABASE_URL"]).rstrip("/")
        key = str(st.secrets["SUPABASE_KEY"])
        return url, key
    except Exception:
        return None, None

def _supabase_request(path, payload=None, access_token=None):
    url, key = _supabase_config()
    if not url or not key:
        return None, "Configuration Supabase absente dans les Secrets Streamlit."

    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    headers["Authorization"] = f"Bearer {access_token or key}"

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        headers=headers,
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}, None
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            info = json.loads(raw)
            msg = info.get("msg") or info.get("message") or info.get("error_description") or info.get("error")
        except Exception:
            msg = str(exc)
        return None, msg or f"Erreur Supabase ({exc.code})"
    except Exception as exc:
        return None, f"Connexion impossible à Supabase : {exc}"


def _supabase_rest(method, table, access_token, payload=None, query="", prefer=None):
    url, key = _supabase_config()
    if not url or not key:
        return None, "Configuration Supabase absente."
    headers = {"apikey": key, "Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{url}/rest/v1/{table}{query}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}, None
    except urllib.error.HTTPError as exc:
        try:
            info = json.loads(exc.read().decode("utf-8"))
            msg = info.get("message") or info.get("hint") or info.get("details") or str(exc)
        except Exception:
            msg = str(exc)
        return None, msg
    except Exception as exc:
        return None, str(exc)

def track_usage(event_type, metadata=None):
    """Enregistre une utilisation PriceFlow sans bloquer l'application en cas d'erreur."""
    tok = _token()
    user = st.session_state.get("pf_user") or {}
    uid = user.get("id")
    if not tok or not uid:
        return
    payload = {
        "user_id": uid,
        "event_type": str(event_type),
        "metadata": metadata or {},
    }
    _supabase_rest("POST", "usage_events", tok, payload=payload, prefer="return=minimal")

def load_admin_usage():
    """Charge les événements d'utilisation accessibles à l'administrateur via les politiques RLS."""
    tok = _token()
    if not tok:
        return [], "Session administrateur absente."
    return _supabase_rest(
        "GET", "usage_events", tok,
        query="?select=created_at,user_id,event_type,metadata&order=created_at.desc&limit=10000"
    )

def _token():
    return (st.session_state.get("pf_session") or {}).get("access_token")

def is_admin():
    try:
        admin_email = str(st.secrets.get("ADMIN_EMAIL", "")).strip().lower()
    except Exception:
        admin_email = ""
    email = str((st.session_state.get("pf_user") or {}).get("email", "")).strip().lower()
    return bool(admin_email and email == admin_email)

def load_cloud_history(force=False):
    if st.session_state.get("history_loaded") and not force:
        return
    tok = _token()
    if not tok:
        return
    data, err = _supabase_rest("GET", "documents", tok, query="?select=id,created_at,supplier,document_number,line_count,total_ht,total_extracted,difference,file_name&order=created_at.desc&limit=500")
    if err:
        st.session_state.history = []
        st.session_state.history_error = err
    else:
        def fm(v): return fmt_money(v) if v is not None else "—"
        st.session_state.history = [{
            "Date": (x.get("created_at") or "").replace("T", " ")[:16],
            "Fournisseur": x.get("supplier") or "—", "N° document": x.get("document_number") or "—",
            "Lignes": x.get("line_count") or 0, "Total HT BL": fm(x.get("total_ht")),
            "Total extrait": fm(x.get("total_extracted")), "Écart": fm(x.get("difference")),
            "Fichier": x.get("file_name") or "—"
        } for x in (data or [])]
        st.session_state.history_error = None
    st.session_state.history_loaded = True

def upload_pdf_to_storage(pdf_bytes, filename, user_id, access_token):
    url, key = _supabase_config()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    path = f"{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{safe}"
    headers = {"apikey": key, "Authorization": f"Bearer {access_token}", "Content-Type": "application/pdf", "x-upsert": "false"}
    req = urllib.request.Request(f"{url}/storage/v1/object/priceflow-documents/{path}", data=pdf_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
        return path, None
    except Exception as exc:
        return None, str(exc)

def save_document_cloud(uploaded, supplier, doc_number, total_ht, total_extrait, ecart, rows):
    tok = _token(); user = st.session_state.get("pf_user") or {}; uid = user.get("id")
    if not tok or not uid:
        return False, "Session utilisateur absente."
    storage_path, storage_err = upload_pdf_to_storage(uploaded.getvalue(), uploaded.name, uid, tok)
    payload = {"user_id": uid, "supplier": supplier, "document_number": doc_number, "file_name": uploaded.name,
               "storage_path": storage_path, "line_count": len(rows), "total_ht": total_ht,
               "total_extracted": total_extrait, "difference": ecart}
    docs, err = _supabase_rest("POST", "documents", tok, payload=payload, prefer="return=representation")
    if err:
        return False, err
    doc_id = docs[0].get("id") if isinstance(docs, list) and docs else None
    if doc_id:
        lines=[]
        for r in rows:
            lines.append({"document_id": doc_id, "user_id": uid, "designation": str(r.get("Désignation", "")),
                          "quantity": float(r.get("Quantité") or 0), "unit_price": float(r.get("Prix unitaire") or 0), "supplier": supplier})
        if lines:
            _, lerr = _supabase_rest("POST", "price_lines", tok, payload=lines, prefer="return=minimal")
            if lerr: return True, f"Document enregistré, mais lignes prix non enregistrées : {lerr}"
    st.session_state.history_loaded = False
    return True, ("PDF non archivé dans Storage, mais données enregistrées." if storage_err else None)

def signup_user(email, password):
    return _supabase_request(
        "/auth/v1/signup",
        {"email": email.strip().lower(), "password": password},
    )

def login_user(email, password):
    return _supabase_request(
        "/auth/v1/token?grant_type=password",
        {"email": email.strip().lower(), "password": password},
    )

def get_current_user(access_token):
    return _supabase_request("/auth/v1/user", access_token=access_token)

def _save_browser_session(result):
    """Conserve uniquement le jeton Supabase dans le navigateur pendant 1 heure."""
    token = (result or {}).get("access_token")
    if token:
        cookie_controller.set(
            PF_AUTH_COOKIE, token, path="/", max_age=PF_AUTH_MAX_AGE,
            secure=True, same_site="strict"
        )

def _clear_browser_session():
    try:
        cookie_controller.remove(PF_AUTH_COOKIE)
    except Exception:
        pass

def _restore_browser_session():
    """Restaure la connexion après F5 si le jeton navigateur est encore valide."""
    try:
        token = cookie_controller.get(PF_AUTH_COOKIE)
    except Exception:
        token = None
    if not token:
        return False
    user, error = get_current_user(token)
    if error or not user:
        _clear_browser_session()
        return False
    st.session_state.pf_session = {"access_token": token}
    st.session_state.pf_user = user
    return True

def logout_priceflow():
    _clear_browser_session()
    st.session_state.pop("pf_session", None)
    st.session_state.pop("pf_user", None)
    st.session_state.history_loaded = False
    time.sleep(0.25)
    st.rerun()

def render_auth():
    with st.container(key="pf_header"):
        st.markdown('<div class="pf-brand"><div class="pf-brand-name">Price<span>Flow</span></div><small>Analyse & comparaison des achats</small></div>', unsafe_allow_html=True)
    with st.container(key="pf_auth_card"):
        st.subheader("Bienvenue sur PriceFlow")
        st.caption("Connectez-vous pour accéder à votre espace et à vos outils PriceFlow.")

        login_tab, signup_tab = st.tabs(["Se connecter", "Créer un compte"])

        with login_tab:
            with st.form("pf_login_form"):
                email = st.text_input("Adresse e-mail", key="pf_login_email")
                password = st.text_input("Mot de passe", type="password", key="pf_login_password")
                submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.warning("Renseignez votre adresse e-mail et votre mot de passe.")
                else:
                    result, error = login_user(email, password)
                    if error:
                        st.error(f"Connexion impossible : {error}")
                    elif result and result.get("access_token"):
                        st.session_state.pf_session = result
                        st.session_state.pf_user = result.get("user", {})
                        _save_browser_session(result)
                        time.sleep(0.25)
                        st.rerun()
                    else:
                        st.error("Connexion impossible.")

        with signup_tab:
            with st.form("pf_signup_form"):
                email = st.text_input("Adresse e-mail", key="pf_signup_email")
                password = st.text_input(
                    "Mot de passe",
                    type="password",
                    key="pf_signup_password",
                    help="Utilisez au minimum 8 caractères.",
                )
                password2 = st.text_input("Confirmer le mot de passe", type="password", key="pf_signup_password2")
                submitted = st.form_submit_button("Créer mon compte", type="primary", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.warning("Renseignez votre adresse e-mail et votre mot de passe.")
                elif len(password) < 8:
                    st.warning("Le mot de passe doit contenir au moins 8 caractères.")
                elif password != password2:
                    st.warning("Les deux mots de passe ne correspondent pas.")
                else:
                    result, error = signup_user(email, password)
                    if error:
                        st.error(f"Création impossible : {error}")
                    elif result and result.get("access_token"):
                        st.session_state.pf_session = result
                        st.session_state.pf_user = result.get("user", {})
                        _save_browser_session(result)
                        st.success("Compte créé. Vous êtes connecté.")
                        time.sleep(0.25)
                        st.rerun()
                    else:
                        st.success(
                            "Compte créé. Un e-mail de confirmation vient de vous être envoyé. "
                            "Confirmez votre adresse puis revenez vous connecter à PriceFlow."
                        )

    st.markdown('<p class="pf-auth-footer">© 2026 Michel RACHOU · PriceFlow</p>', unsafe_allow_html=True)


def require_login():
    session = st.session_state.get("pf_session")
    if session and session.get("access_token"):
        user, error = get_current_user(session["access_token"])
        if not error and user:
            st.session_state.pf_user = user
            return True
        st.session_state.pop("pf_session", None)
        st.session_state.pop("pf_user", None)
        _clear_browser_session()

    # Après une actualisation Streamlit, session_state est neuf :
    # on restaure alors le jeton conservé dans le navigateur.
    if _restore_browser_session():
        return True

    render_auth()
    st.stop()

require_login()
load_cloud_history()


nav = pf_navigation()

if nav == "▣ Achats / Fournisseurs":
    with st.container(key="pf_title_purchase"):
        title_col, action_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            pf_heading("Achats / Fournisseurs", "Importez vos documents fournisseurs et analysez automatiquement vos achats.", "box")
        with action_col:
            if st.button("Nouveau BL", icon=":material/add_circle_outline:", type="primary", use_container_width=True):
                new_document()

    uploaded = st.file_uploader(
        "Déposez votre BL / bon d'enlèvement / commande / offre de prix",
        type=["pdf"],
        accept_multiple_files=False,
        key=f"pdf_{st.session_state.uploader_key}",
    )

    if uploaded:
        progress = st.progress(0, text=f"Lecture du PDF — {uploaded.name}")
        st.caption("La barre avance par étapes terminées. La lecture des scans (OCR) peut prendre plus de temps.")
        try:
            with st.spinner(f"Lecture de {uploaded.name} — OCR si nécessaire…", show_time=True):
                documents = purchase_documents(uploaded.getvalue())
            progress.progress(0.5, text="PDF lu — extraction des articles")
            selected = 0
            if len(documents) > 1:
                st.info(f"Ce PDF contient {len(documents)} bons distincts. Choisissez celui à importer.")
                selected = st.selectbox("Bon à importer", range(len(documents)), format_func=lambda i: f"BL {documents[i][0]}")
            part_number, part_bytes, part_text, used_ocr = documents[selected]
            source_upload = io.BytesIO(part_bytes)
            source_upload.name = uploaded.name if len(documents) == 1 else f"{Path(uploaded.name).stem}_BL_{part_number}.pdf"
            with st.spinner("Extraction des articles et contrôle des montants…", show_time=True):
                rows, supplier, doc_number, total_ht, extra_charges = extract_document(part_bytes, part_text)
            progress.progress(1.0, text=f"Lecture terminée — {len(rows)} lignes extraites")
            if used_ocr:
                st.info("Document lu par OCR : vérifiez les références et désignations dans l'aperçu, même lorsque les totaux concordent.")

            info1, info2 = st.columns(2)
            info1.metric("Fournisseur", supplier)
            info2.metric("N° document", doc_number)

            if rows:
                # Format d'import validé dans Esabora (Test 1).
                # Référence reste vide tant qu'elle n'est pas extraite du PDF :
                # le N° document reste affiché dans l'application et dans l'historique.
                export_rows = []
                for r in rows:
                    export_rows.append({
                        "Référence": str(r.get("Référence", "") or ""),
                        "Désignation": str(r.get("Désignation", "") or ""),
                        "Quantité": r.get("Quantité"),
                        "Prix unitaire": r.get("Prix unitaire"),
                    })

                # N'ajoute les frais complémentaires que s'ils ne sont PAS déjà
                # inclus dans les prix unitaires des articles.
                # Exemple CLIM+ : les lignes "Dont éco-contribution" sont informatives
                # et les PU articles donnent déjà exactement le Total HT.
                articles_total = article_sum(export_rows)

                charges_to_add = list(extra_charges)
                if total_ht is not None:
                    gap_before_extras = round(float(total_ht) - articles_total, 2)
                    detected_extras = round(sum(float(x["amount"]) for x in extra_charges), 2) if extra_charges else 0.0

                    # Si les articles atteignent déjà le Total HT, l'éco-contribution
                    # est déjà comprise dans les PU : ne pas la rajouter une 2e fois.
                    if abs(gap_before_extras) <= 0.01:
                        charges_to_add = [x for x in extra_charges if x.get("outside_total_ht")]
                    # Si les frais détectés correspondent exactement à l'écart,
                    # on les ajoute normalement (PUM, ANCONETTI, etc.).
                    elif detected_extras and abs(gap_before_extras - detected_extras) <= 0.02:
                        charges_to_add = list(extra_charges)

                # Regroupe les frais réellement à ajouter en une seule ligne Esabora.
                extras_total = round(sum(float(x["amount"]) for x in charges_to_add), 2) if charges_to_add else 0.0
                if extras_total:
                    labels = {x["label"] for x in charges_to_add}
                    if labels == {"ÉCO-CONTRIBUTION"}:
                        extra_label = "ÉCO-CONTRIBUTION"
                    else:
                        extra_label = "ÉCO-CONTRIBUTION / SURCHARGES"
                    export_rows.append({
                        "Référence": "",
                        "Désignation": extra_label,
                        "Quantité": 1,
                        "Prix unitaire": extras_total,
                    })

                df = pd.DataFrame(export_rows, columns=["Référence", "Désignation", "Quantité", "Prix unitaire"])
                df["Quantité"] = df["Quantité"].apply(lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x)

                # Contrôle comptable : comparaison du Total HT imprimé sur le BL
                # avec la somme des lignes réellement extraites.
                total_extrait = article_sum(export_rows)
                separate_charges = round(sum(float(x["amount"]) for x in charges_to_add if x.get("outside_total_ht")), 2)
                control_total = round(total_ht + separate_charges, 2) if total_ht is not None else None
                ecart = round(control_total - total_extrait, 2) if control_total is not None else None

                ctrl1, ctrl2, ctrl3 = st.columns(3)
                ctrl1.metric("Total HT + REP séparée" if separate_charges else "Total HT du BL", fmt_money(control_total))
                ctrl2.metric("Total extrait", fmt_money(total_extrait))
                ctrl3.metric("Écart", fmt_money(ecart))

                if charges_to_add:
                    eco_total = round(sum(x["amount"] for x in extra_charges if x["label"] == "ÉCO-CONTRIBUTION"), 2)
                    energy_total = round(sum(x["amount"] for x in extra_charges if x["label"] == "SURCHARGE ÉNERGIE"), 2)
                    details = []
                    if eco_total:
                        details.append(f"éco-contribution : {fmt_money(eco_total)}")
                    if energy_total:
                        details.append(f"surcharge énergie : {fmt_money(energy_total)}")
                    st.info(
                        f"♻️ Frais complémentaires détectés : {fmt_money(extras_total)} "
                        f"({', '.join(details)}). Ils ont été regroupés en une seule ligne et ajoutés au fichier Excel."
                    )
                    if separate_charges:
                        st.caption(f"Total HT imprimé : {fmt_money(total_ht)} + REP facturée séparément : {fmt_money(separate_charges)}. Le contrôle inclut les deux montants.")
                elif extra_charges and not charges_to_add:
                    st.info(
                        "♻️ Éco-contribution détectée, déjà comprise dans les lignes extraites. "
                        "Elle n'est pas ajoutée une seconde fois dans l'Excel."
                    )

                if ecart is not None:
                    if abs(ecart) <= 0.01:
                        st.success(
                            f"✅ Total extrait après intégration : {fmt_money(total_extrait)} — "
                            f"Écart : {fmt_money(ecart)}"
                        )
                    else:
                        st.warning(
                            f"⚠️ Écart restant : {fmt_money(abs(ecart))}. "
                            "Le document contient peut-être une autre ligne facturée, une remise ou un frais non encore détecté."
                        )

                adjusted = [r for r in rows if "Prix unitaire imprimé" in r and r["Prix unitaire"] != r["Prix unitaire imprimé"]]
                if adjusted:
                    st.info("Certains prix unitaires imprimés sont arrondis. Pour reproduire le montant de chaque ligne dans l'export, le prix exporté est calculé à partir du montant imprimé divisé par la quantité.")
                    st.dataframe(pd.DataFrame(adjusted)[["Référence", "Prix unitaire imprimé", "Prix unitaire", "Montant imprimé"]], hide_index=True)
                st.info(f"{len(rows)} ligne(s) extraite(s), {len(df)} ligne(s) dans l'export.")
                pf_section("Aperçu avant export")
                st.dataframe(df, use_container_width=True, hide_index=True)

                # XlsxWriter écrit les chaînes dans sharedStrings.xml.
                # C'est le format qui a été validé par le Test 1 dans l'import Esabora.
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Feuil1")
                    workbook = writer.book
                    ws = writer.sheets["Feuil1"]

                    text_fmt = workbook.add_format({"num_format": "@"})
                    qty_fmt = workbook.add_format({"num_format": "0.00"})
                    price_fmt = workbook.add_format({"num_format": "0.00"})

                    ws.set_column("A:A", 22, text_fmt)
                    ws.set_column("B:B", 62, text_fmt)
                    ws.set_column("C:C", 14, qty_fmt)
                    ws.set_column("D:D", 18, price_fmt)

                output.seek(0)

                safe_num = re.sub(r"[^A-Za-z0-9._-]+", "_", doc_number)
                st.download_button(
                    "⬇ Télécharger l'Excel",
                    data=output,
                    file_name=f"Extraction_{safe_num}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )

                signature = (source_upload.name, doc_number, len(df), total_ht, total_extrait)
                if st.session_state.saved_signature != signature:
                    entry = {
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Fournisseur": supplier,
                        "N° document": doc_number,
                        "Lignes": len(df),
                        "Total HT BL": fmt_money(total_ht),
                        "Total extrait": fmt_money(total_extrait),
                        "Écart": fmt_money(ecart),
                        "Fichier": source_upload.name,
                    }
                    ok, cloud_msg = save_document_cloud(source_upload, supplier, doc_number, total_ht, total_extrait, ecart, export_rows)
                    if ok:
                        load_cloud_history(force=True)
                        track_usage("achat", {"supplier": supplier, "document_number": doc_number})
                        if cloud_msg:
                            st.info(cloud_msg)
                    else:
                        st.warning(f"Historique Supabase non enregistré : {cloud_msg}")
                    st.session_state.saved_signature = signature
            else:
                st.warning("Aucune ligne article reconnue sur ce document. Le format devra être ajouté à l'extracteur.")

        except Exception as e:
            progress.empty()
            st.error(f"Erreur de lecture du PDF : {e}")

if nav == "🏗 Locations":
    if "location_uploader_key" not in st.session_state:
        st.session_state.location_uploader_key = 0
    with st.container(key="pf_title_location"):
        title_col, action_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            pf_heading("Locations", "Analyse de vos devis et offres de location", "crane")
        with action_col:
            if st.button("Nouvelle location", icon=":material/add_circle_outline:", type="primary", use_container_width=True):
                st.session_state.location_uploader_key += 1
                st.rerun()

    uploaded_loc = st.file_uploader(
        "Déposez votre devis / offre de location",
        type=["pdf"],
        accept_multiple_files=False,
        key=f"location_pdf_{st.session_state.location_uploader_key}",
    )

    if uploaded_loc:
        progress = st.progress(0, text=f"Lecture du PDF — {uploaded_loc.name}")
        st.caption("La barre avance par étapes terminées. La lecture des scans (OCR) peut prendre plus de temps.")
        try:
            with st.spinner(f"Lecture de {uploaded_loc.name} — OCR si nécessaire…", show_time=True):
                loc = extract_rental(uploaded_loc.getvalue())
            progress.progress(1.0, text=f"Lecture terminée — {len(loc['Lignes'])} lignes extraites")
            c1, c2 = st.columns(2)
            c1.metric("Loueur", loc["Loueur"])
            c2.metric("N° document", loc["N° document"])

            d1, d2, d3 = st.columns(3)
            d1.metric("Début", loc["Date début"] or "Non détecté")
            d2.metric("Fin", loc["Date fin"] or "Non détecté")
            d3.metric("Durée", loc["Durée"] or "Non détectée")

            st.info(f"Matériel : **{loc['Matériel']}**")
            for note in loc.get("Points à vérifier", []):
                st.info(note)

            if loc["Lignes"]:
                loc_df = pd.DataFrame(loc["Lignes"], columns=["Désignation", "Montant HT"])
                total_loc = round(float(loc_df["Montant HT"].sum()), 2)
                total_doc = loc["Total HT document"]
                ecart_loc = round(total_doc - total_loc, 2) if total_doc is not None else None
                supplements = loc.get("Suppléments estimés", [])
                supplements_total = round(sum(x["Montant estimé HT"] for x in supplements), 2)
                estimated_total = round(total_loc + supplements_total, 2) if supplements else None

                m1, m2, m3 = st.columns(3)
                m1.metric("Total HT document", fmt_money(total_doc))
                m2.metric("Sous-total de base HT" if supplements else "Total extrait", fmt_money(total_loc))
                m3.metric("Écart", fmt_money(ecart_loc))

                if total_doc is None:
                    st.info(
                        "Aucun total HT global détecté dans le devis. "
                        "Le montant de base est calculé à partir des lignes de location et de prestations reconnues."
                    )
                elif abs(ecart_loc) <= 0.01:
                    st.success(f"✅ Contrôle location OK — Écart : {fmt_money(ecart_loc)}")
                else:
                    st.warning(
                        f"⚠️ Écart location : {fmt_money(abs(ecart_loc))}. "
                        "Une prestation ou un frais du devis doit encore être identifié."
                    )

                loc_signature = (uploaded_loc.name, loc["N° document"], len(loc_df), total_loc)
                if st.session_state.get("last_location_usage") != loc_signature:
                    track_usage("location", {"supplier": loc["Loueur"], "document_number": loc["N° document"]})
                    st.session_state.last_location_usage = loc_signature

                pf_section("Détail de la location")
                pf_simple_table(loc_df)

                if supplements:
                    pf_section("Suppléments annoncés dans le devis")
                    st.warning(loc.get("Conditions estimation", "Sous réserve des conditions du devis.") +
                               " Ces montants ne constituent pas un total imprimé ni une facture définitive.")
                    pf_simple_table(pd.DataFrame(supplements))
                    extra_col, estimate_col = st.columns(2)
                    extra_col.metric("Suppléments estimés HT", fmt_money(supplements_total))
                    estimate_col.metric("Total estimé avec suppléments HT", fmt_money(estimated_total))

                export_loc = pd.DataFrame([{
                    "Loueur": loc["Loueur"],
                    "N° document": loc["N° document"],
                    "Matériel": loc["Matériel"],
                    "Date début": loc["Date début"],
                    "Date fin": loc["Date fin"],
                    "Durée": loc["Durée"],
                    "Total HT document": total_doc,
                    "Total extrait": total_loc,
                    "Écart": ecart_loc,
                    "Suppléments estimés HT": supplements_total if supplements else None,
                    "Total estimé HT": estimated_total,
                    "Conditions estimation": loc.get("Conditions estimation", "") if supplements else "",
                    "Points à vérifier": " | ".join(loc.get("Points à vérifier", [])),
                }])

                out_loc = io.BytesIO()
                with pd.ExcelWriter(out_loc, engine="xlsxwriter") as writer:
                    export_loc.to_excel(writer, index=False, sheet_name="Synthèse")
                    loc_df.to_excel(writer, index=False, sheet_name="Détail")
                    if supplements:
                        pd.DataFrame(supplements).to_excel(writer, index=False, sheet_name="Suppléments estimés")
                    wb = writer.book
                    ws1 = writer.sheets["Synthèse"]
                    ws2 = writer.sheets["Détail"]
                    money_fmt = wb.add_format({"num_format": "0.00"})
                    ws1.set_column("A:C", 28)
                    ws1.set_column("D:F", 16)
                    ws1.set_column("G:I", 18, money_fmt)
                    ws1.set_column("J:K", 24, money_fmt)
                    ws1.set_column("L:L", 70)
                    ws1.set_column("M:M", 80)
                    ws2.set_column("A:A", 42)
                    ws2.set_column("B:B", 18, money_fmt)
                    if supplements:
                        writer.sheets["Suppléments estimés"].set_column("A:A", 32)
                        writer.sheets["Suppléments estimés"].set_column("B:B", 65)
                        writer.sheets["Suppléments estimés"].set_column("C:C", 22, money_fmt)
                out_loc.seek(0)

                safe_loc = re.sub(r"[^A-Za-z0-9._-]+", "_", loc["N° document"])
                st.download_button(
                    "⬇ Télécharger l'Excel Location",
                    data=out_loc,
                    file_name=f"Location_{safe_loc}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.warning("Aucune ligne de location reconnue sur ce document.")
        except Exception as e:
            progress.empty()
            st.error(f"Erreur de lecture du PDF Location : {e}")


if nav == "⚖ Comparatif":
    pf_heading("Comparatif fournisseurs", "Comparez vos devis et identifiez automatiquement les meilleurs prix", "scale")

    compare_files = st.file_uploader("Déposez 2 devis ou plus", type=["pdf"], accept_multiple_files=True, key="compare_pdfs")
    if compare_files:
        if len(compare_files) < 2:
            st.info("Ajoutez au moins 2 devis pour lancer la comparaison.")
        else:
            offers, errors = [], []
            document_count = len(compare_files)
            progress = st.progress(0, text=f"Analyse des devis : 0 / {document_count} documents traités")
            st.caption("La barre avance à chaque PDF terminé. La lecture des scans (OCR) peut prendre plus de temps.")
            for index, f in enumerate(compare_files, 1):
                progress.progress((index - 1) / document_count, text=f"Document {index} / {document_count} — {f.name}")
                try:
                    with st.spinner(f"Lecture de {f.name} — OCR si nécessaire…", show_time=True):
                        rws, sup, num, tht, extras = extract_document(f.getvalue())
                    offers.append({"Fichier":f.name,"Fournisseur":sup,"N° document":num,"Total HT":tht,"Lignes":rws})
                except Exception as e:
                    errors.append(f"{f.name} : {e}")
                finally:
                    progress.progress(index / document_count, text=f"Analyse des devis : {index} / {document_count} documents traités")
            progress.progress(1.0, text=f"Lecture terminée — {len(offers)} devis lus, {len(errors)} échec(s)")
            if errors: st.warning("Certains fichiers n'ont pas pu être lus : " + " | ".join(errors))
            if offers:
                sig=("comparatif",tuple((o["Fichier"],o["N° document"]) for o in offers))
                if st.session_state.get("compare_usage_sig") != sig:
                    track_usage("comparatif", {"documents":len(offers),"suppliers":[o["Fournisseur"] for o in offers]})
                    st.session_state.compare_usage_sig=sig

                pf_supplier_cards(offers)

                records=[]
                for o in offers:
                    for r in o["Lignes"]:
                        desc=clean(r["Désignation"])
                        if any(w in desc.upper() for w in ["FRAIS DE PORT","PORT SUR VENTE","LIVRAISON STANDARD","CARBURANT","ECO-CONTRIBUTION"]): continue
                        key=comparison_key(desc)
                        if key:
                            records.append({"Clé":key,"Désignation":desc,"Fournisseur":o["Fournisseur"],"Quantité":float(r["Quantité"]),"Prix unitaire":float(r["Prix unitaire"])})
                if records:
                    rdf=pd.DataFrame(records)
                    suppliers=[o["Fournisseur"] for o in offers]
                    # une offre par fournisseur et famille : on conserve le PU le plus bas en cas de doublon
                    rows=[]
                    for key,g in rdf.groupby("Clé",sort=False):
                        by={}
                        for sup,sg in g.groupby("Fournisseur"):
                            rr=sg.sort_values("Prix unitaire").iloc[0]; by[sup]=rr
                        avail=list(by.values())
                        if not avail: continue
                        best=min(avail,key=lambda x:float(x["Prix unitaire"]))
                        qty=float(best["Quantité"]); bestpu=float(best["Prix unitaire"])
                        worstpu=max(float(x["Prix unitaire"]) for x in avail)
                        desc=str(best["Désignation"])
                        rows.append({"key":key,"desc":desc,"qty":qty,"by":by,"best_sup":best["Fournisseur"],"best_pu":bestpu,"best_total":qty*bestpu,"gap":qty*(worstpu-bestpu) if len(avail)>1 else 0,"gap_pct":((worstpu-bestpu)/worstpu*100) if len(avail)>1 and worstpu else 0,"comparable":len(avail)>1})
                    if rows:
                        comparable=[r for r in rows if r["comparable"]]
                        saving=sum(r["gap"] for r in comparable); worstbasket=sum(r["best_total"]+r["gap"] for r in comparable)
                        saving_pct=(saving/worstbasket*100) if worstbasket else 0
                        st.markdown(f'<div class="pf-comparison-summary"><span>Meilleurs prix identifiés sur <b>{len(comparable)} lignes comparables</b></span><div><span>Économie potentielle </span><strong>{fmt_money(saving)}</strong></div></div>', unsafe_allow_html=True)

                        h1='<tr><th rowspan="2">#</th><th rowspan="2" class="left">Désignation</th><th rowspan="2">Qté</th>'
                        h2='<tr>'
                        for sup in suppliers:
                            h1+=f'<th colspan="2" class="supplier-head">{html.escape(str(sup))}</th>'; h2+='<th>Prix U. (€)</th><th>Total (€)</th>'
                        h1+='<th colspan="3" class="best-head">Meilleur prix</th><th colspan="2">Écart max</th></tr>'
                        h2+='<th class="best-head">Fournisseur</th><th class="best-head">Prix U. (€)</th><th class="best-head">Total (€)</th><th>(€)</th><th>(%)</th></tr>'
                        body=''; totals={sup:0.0 for sup in suppliers}; best_total_sum=0
                        export=[]
                        for i,r in enumerate(rows,1):
                            body+=f'<tr><td>{i}</td><td class="left">{html.escape(r["desc"])}</td><td>{r["qty"]:g}</td>'
                            er={"#":i,"Désignation":r["desc"],"Qté":r["qty"]}
                            for sup in suppliers:
                                rr=r["by"].get(sup)
                                if rr is None: body+='<td>—</td><td>—</td>'; er[f'{sup} PU']=None; er[f'{sup} Total']=None
                                else:
                                    pu=float(rr["Prix unitaire"]); total=r["qty"]*pu; totals[sup]+=total
                                    cls=' class="best"' if sup==r["best_sup"] else ''
                                    body+=f'<td{cls}>{pf_number(pu)}</td><td{cls}>{pf_number(total)}</td>'; er[f'{sup} PU']=pu; er[f'{sup} Total']=total
                            best_total_sum+=r["best_total"]
                            body+=f'<td class="best left">{html.escape(str(r["best_sup"]))}</td><td class="best">{pf_number(r["best_pu"])}</td><td class="best">{pf_number(r["best_total"])}</td><td>{pf_number(r["gap"])}</td><td>{pf_number(r["gap_pct"], 1)}%</td></tr>'
                            er.update({"Meilleur fournisseur":r["best_sup"],"Meilleur PU":r["best_pu"],"Meilleur total":r["best_total"],"Écart max €":r["gap"],"Écart max %":r["gap_pct"]}); export.append(er)
                        body+='<tr class="total"><td colspan="2" class="left">TOTAL</td><td></td>'
                        for sup in suppliers: body+=f'<td></td><td>{pf_number(totals[sup])}</td>'
                        body+=f'<td class="best"></td><td class="best"></td><td class="best">{pf_number(best_total_sum)}</td><td>{pf_number(saving)}</td><td>{pf_number(saving_pct, 1)}%</td></tr>'
                        table=f'<div class="pf-table-wrap"><table class="pf-table"><thead>{h1}{h2}</thead><tbody>{body}</tbody></table></div>'
                        st.markdown(table,unsafe_allow_html=True)
                        st.markdown(f'<div class="pf-bottom"><div class="pf-note green">En choisissant les meilleurs prix<br><strong>Vous économisez {fmt_money(saving)}</strong><br><span>Soit {pf_number(saving_pct, 1)}% par rapport aux prix les plus élevés comparables</span></div><div class="pf-note">📊 Analyse terminée<br><strong>{len(rows)} lignes analysées</strong><br><span>Meilleurs prix trouvés sur {len(comparable)} lignes comparables</span></div></div>',unsafe_allow_html=True)
                        out_cmp=io.BytesIO(); edf=pd.DataFrame(export)
                        with pd.ExcelWriter(out_cmp,engine="xlsxwriter") as writer:
                            edf.to_excel(writer,index=False,sheet_name="Comparatif")
                            ws=writer.sheets["Comparatif"]; ws.set_column("A:A",6); ws.set_column("B:B",45); ws.set_column("C:Z",17)
                        out_cmp.seek(0)
                        st.download_button("⬇ Télécharger le comparatif Excel",data=out_cmp,file_name="Comparatif_fournisseurs.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary",use_container_width=True)
                    else: st.warning("Aucune ligne exploitable pour la comparaison.")
                else: st.warning("Aucune ligne exploitable pour la comparaison.")



if nav == "📋 Analyse Marché":
    pf_heading("Analyse Marché", "Analysez vos CCTP, DPGF et pièces marché CVC et plomberie.", "file")
    st.markdown('<div class="pf-ai-note"><strong>👁 Aperçu — fonctionnalité en développement</strong><br>Cette page est une démonstration visuelle. Aucune analyse IA ni consommation API n’est effectuée.</div>', unsafe_allow_html=True)
    st.markdown("**Documents du marché**")
    st.markdown('<span class="pf-doc-chip">📄 CCTP CVC</span><span class="pf-doc-chip">📄 DPGF CVC</span><span class="pf-doc-chip">📄 CCTP GTB</span><span class="pf-doc-chip">📄 DPGF GTB</span>', unsafe_allow_html=True)
    st.caption("Exemple de présentation : les documents réels seront déposés ici lors de l’activation du module.")
    st.markdown("### Projet : RHR Marseille")
    st.caption("Lot analysé : CVC · 4 documents analysés · Démonstration")
    st.markdown("""<div class="pf-market-grid">
      <div class="pf-market-kpi"><div class="n">18</div><div class="l">🟢 Prestations identifiées</div></div>
      <div class="pf-market-kpi"><div class="n">6</div><div class="l">🟠 Points à vérifier</div></div>
      <div class="pf-market-kpi"><div class="n">5</div><div class="l">🔗 Interfaces / limites</div></div>
      <div class="pf-market-kpi"><div class="n">3</div><div class="l">🔴 Incohérences potentielles</div></div>
    </div>""", unsafe_allow_html=True)
    st.markdown("### Synthèse CMT")
    st.markdown("""<div class="pf-finding ok"><h4>🔥 Chaufferie / PAC / groupe froid</h4><p><strong>Prestations repérées :</strong> production chaud/froid, équipements hydrauliques, raccordements, régulation et mise en service.</p><p><strong>À contrôler :</strong> puissances, accessoires, limites électriques/GTB et prestations de manutention.</p><div class="pf-source">Source de démonstration · CCTP CVC · page 12 · § Production thermique</div></div>""", unsafe_allow_html=True)
    with st.expander("📖 Voir le passage source — Chaufferie / PAC"):
        st.caption("Exemple de rendu — le texte ci-dessous est fictif et sert uniquement à montrer l’interface.")
        st.markdown("**Document :** CCTP CVC  ·  **Page :** 12  ·  **Article :** Production thermique")
        st.markdown('<div class="pf-source-box">[PASSAGE SOURCE DU CCTP AFFICHÉ ICI À L’IDENTIQUE]<br>La version opérationnelle rappellera le texte exact de la page ayant généré le constat.</div>', unsafe_allow_html=True)
    st.markdown("""<div class="pf-finding ok"><h4>🧰 Réseaux et matériaux</h4><p><strong>Matériaux détectés :</strong> acier noir, acier galvanisé, cuivre, multicouche, PVC et PEHD.</p><p><strong>Détails prévus :</strong> DN/diamètres, assemblages, raccords, supports, calorifuge et protections lorsqu’ils sont prescrits.</p><div class="pf-source">Source de démonstration · CCTP CVC · page 21 · § Réseaux hydrauliques</div></div>""", unsafe_allow_html=True)
    with st.expander("📖 Voir le passage source — Réseaux et matériaux"):
        st.caption("Exemple de rendu — passage non issu d’un document réel.")
        st.markdown("**Document :** CCTP CVC  ·  **Page :** 21  ·  **Article :** Réseaux hydrauliques")
        st.markdown('<div class="pf-source-box">[PASSAGE SOURCE EXACT : matériau, diamètre, assemblage, calorifuge et prescriptions de pose]</div>', unsafe_allow_html=True)
    st.markdown("""<div class="pf-finding link"><h4>🔗 Interface CVC ↔ Gros Œuvre</h4><p><strong>Point détecté :</strong> répartition des réservations et carottages entre lots selon les prescriptions du marché.</p><p><strong>Action :</strong> vérifier les diamètres nécessaires et communiquer les réservations hors périmètre CVC.</p><div class="pf-source">Source de démonstration · CCTP CVC · page 8 · § Limites de prestations</div></div>""", unsafe_allow_html=True)
    with st.expander("📖 Voir le passage source — Interface Gros Œuvre"):
        st.caption("Exemple de rendu — la version active affichera la clause exacte, sans reformulation.")
        st.markdown("**Document :** CCTP CVC  ·  **Page :** 8  ·  **Article :** Limites de prestations")
        st.markdown('<div class="pf-source-box">[CLAUSE EXACTE DU CCTP RELATIVE AUX RÉSERVATIONS / CAROTTAGES]</div>', unsafe_allow_html=True)
    st.markdown("""<div class="pf-finding warn"><h4>🟠 Condensats — À vérifier</h4><p>Une prestation est décrite au CCTP mais aucun poste DPGF clairement identifiable n’est présenté dans cet aperçu.</p><p><strong>Action :</strong> contrôler le chiffrage avant remise de l’offre.</p><div class="pf-source">Comparaison de démonstration · CCTP ↔ DPGF</div></div>""", unsafe_allow_html=True)
    with st.expander("📖 Voir les passages source — CCTP ↔ DPGF"):
        st.caption("Exemple visuel : dans la version opérationnelle, les deux passages seront affichés côte à côte avec leurs pages.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**CCTP CVC · page X**")
            st.markdown('<div class="pf-source-box">[PASSAGE CCTP EXACT]</div>', unsafe_allow_html=True)
        with c2:
            st.markdown("**DPGF CVC · page Y**")
            st.markdown('<div class="pf-source-box">[POSTE DPGF CORRESPONDANT OU ABSENCE DE POSTE CLAIR]</div>', unsafe_allow_html=True)
    st.info("Le futur module couvrira notamment chauffage, climatisation, chaufferie, PAC/groupes froids, ventilation, plomberie, GTB/régulation, matériaux, DN, calorifuge, supports, essais, mises en service et interfaces entre lots.")

if nav == "Mon compte ⌄":
    pf_heading("Mon compte", "Retrouvez vos informations et les accès de votre compte.", "user")
    user = st.session_state.get("pf_user", {}) or {}
    email = user.get("email", "—")
    created_at = user.get("created_at", "")
    last_sign_in = user.get("last_sign_in_at", "")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Adresse e-mail**")
        st.write(email)
    with c2:
        st.markdown("**Statut**")
        st.success("Compte connecté")

    if created_at:
        st.caption(f"Compte créé : {created_at[:10]}")
    if last_sign_in:
        st.caption(f"Dernière connexion : {last_sign_in.replace('T', ' ')[:19]}")

    st.success("Historique Supabase actif : vos documents et lignes de prix sont rattachés à votre compte.")
    st.metric("Documents enregistrés", len(st.session_state.history))

    if is_admin():
        st.divider()
        st.subheader("🛡️ Administration PriceFlow")
        tok = _token()
        docs, derr = _supabase_rest("GET", "documents", tok, query="?select=created_at,user_id,supplier,document_number,line_count,total_ht,file_name&order=created_at.desc&limit=10000")
        events, eerr = load_admin_usage()

        if derr:
            st.warning(f"Documents administrateur non disponibles : {derr}")
        if eerr:
            st.warning(f"Statistiques d'utilisation non disponibles : {eerr}")

        adf = pd.DataFrame(docs or [])
        udf = pd.DataFrame(events or [])
        now_utc = pd.Timestamp.now(tz="UTC")

        if not udf.empty and "created_at" in udf.columns:
            udf["created_at"] = pd.to_datetime(udf["created_at"], utc=True, errors="coerce")
            all_users = int(udf["user_id"].nunique()) if "user_id" in udf else 0
            active_7 = int(udf.loc[udf["created_at"] >= now_utc - pd.Timedelta(days=7), "user_id"].nunique())
            active_30 = int(udf.loc[udf["created_at"] >= now_utc - pd.Timedelta(days=30), "user_id"].nunique())
            usage_users = all_users
        else:
            all_users = int(adf["user_id"].nunique()) if not adf.empty and "user_id" in adf else 0
            active_7 = active_30 = 0
            usage_users = all_users

        # Le total des inscrits provient de la vue admin_profiles créée dans Supabase.
        profiles, perr = _supabase_rest("GET", "admin_profiles", tok, query="?select=user_id,email,created_at,last_sign_in_at&order=created_at.desc&limit=10000")
        pdf = pd.DataFrame(profiles or []) if not perr else pd.DataFrame()
        registered = len(pdf) if not pdf.empty else all_users
        activation_pct = round((usage_users / registered * 100), 1) if registered else 0.0
        active7_pct = round((active_7 / registered * 100), 1) if registered else 0.0
        active30_pct = round((active_30 / registered * 100), 1) if registered else 0.0
        docs_per_user = round(len(adf) / usage_users, 1) if usage_users else 0.0

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Utilisateurs inscrits", registered)
        a2.metric("Ont utilisé PriceFlow", f"{activation_pct:.1f} %")
        a3.metric("Actifs sur 7 jours", f"{active7_pct:.1f} %")
        a4.metric("Actifs sur 30 jours", f"{active30_pct:.1f} %")

        b1, b2, b3 = st.columns(3)
        b1.metric("Documents enregistrés", len(adf))
        b2.metric("Documents / utilisateur", f"{docs_per_user:.1f}")
        b3.metric("Fournisseurs", adf["supplier"].nunique() if not adf.empty and "supplier" in adf else 0)

        if not udf.empty and "event_type" in udf:
            st.markdown("**Répartition de l'utilisation**")
            counts = udf["event_type"].value_counts()
            total_events = int(counts.sum())
            cols = st.columns(3)
            for col, key, label in zip(cols, ["achat", "location", "comparatif"], ["Achats", "Locations", "Comparatif"]):
                n = int(counts.get(key, 0))
                pct = (n / total_events * 100) if total_events else 0
                col.metric(label, f"{pct:.1f} %", f"{n} utilisation(s)")

            daily = (udf.dropna(subset=["created_at"])
                     .assign(Jour=lambda x: x["created_at"].dt.date)
                     .groupby("Jour").size().rename("Utilisations"))
            if not daily.empty:
                st.markdown("**Activité dans le temps**")
                chart_df = daily.reset_index()
                chart_df["Jour"] = chart_df["Jour"].astype(str)
                st.markdown("<div class=\"pf-chart-note\">Activité enregistrée par jour</div>", unsafe_allow_html=True)
                st.area_chart(chart_df.set_index("Jour"), color="#0B8CFF")

        if perr:
            st.caption("Le nombre total d'inscrits sera disponible après création de la vue admin_profiles dans Supabase (SQL fourni avec cette version).")
        elif not pdf.empty:
            with st.expander("Voir les comptes inscrits"):
                show_profiles = pdf.rename(columns={"email":"E-mail", "created_at":"Inscription", "last_sign_in_at":"Dernière connexion"})
                st.dataframe(show_profiles[[c for c in ["E-mail", "Inscription", "Dernière connexion"] if c in show_profiles]], use_container_width=True, hide_index=True)

    if st.button("🚪 Se déconnecter", use_container_width=False):
        logout_priceflow()

# Historique personnel : toujours affiché tout en bas de chaque onglet.
# Le contenu propre à la page est rendu en premier, puis l’historique juste avant le footer.
st.divider()
with st.expander("Historique de contrôle", expanded=False):
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True, hide_index=True)
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("↻ Actualiser", key=f"refresh_history_{nav}"):
                load_cloud_history(force=True)
                st.rerun()
        with c2:
            hist_csv = pd.DataFrame(st.session_state.history).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                "Exporter l'historique CSV",
                hist_csv,
                "historique_extracteur.csv",
                "text/csv",
                key=f"export_history_{nav}",
            )
    else:
        st.caption("Aucun document traité pour le moment.")

st.caption("Historique de contrôle indépendant des fichiers Excel. Le Total HT n'est jamais ajouté à l'export.")

st.markdown('<div class="copyright">© 2026 Michel RACHOU · PriceFlow</div>', unsafe_allow_html=True)
