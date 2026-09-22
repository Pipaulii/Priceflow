import io
import html
import json
import re
import unicodedata
import urllib.request
import urllib.error
import time
from datetime import datetime
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
import pandas as pd
import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="PriceFlow", page_icon="📄", layout="wide")

# Session navigateur PriceFlow : survit aux F5, expire après 1 heure.
cookie_controller = CookieController(key="priceflow_auth_cookie")
PF_AUTH_COOKIE = "priceflow_access_token"
PF_AUTH_MAX_AGE = 60 * 60

st.markdown("""
<style>
:root{color-scheme:light!important;--pf-bg:#f7f9fc;--pf-panel:#fff;--pf-border:#dbe4ee;--pf-blue:#0b8cff;--pf-text:#071b33;--pf-muted:#62748a;--pf-green:#12a56a}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.stApp{background:var(--pf-bg)!important;color:var(--pf-text)!important;font-family:Inter,"Segoe UI",Arial,sans-serif!important}
[data-testid="stHeader"]{background:transparent!important;height:2.2rem}.block-container{max-width:1540px;padding-top:.9rem;padding-bottom:2rem}
.hero{height:96px;box-sizing:border-box;padding:17px 26px;border:1px solid #e6ebf1;border-radius:17px;background:#fff;box-shadow:0 10px 32px rgba(31,55,84,.10);margin:0 0 14px}
.hero h1{margin:0;font-size:2.15rem;line-height:1.05;font-weight:850;letter-spacing:-.05em}.hero .price{color:#071b33}.hero .flow{color:#0b8cff}.hero p{margin:.45rem 0 0;color:#62748a;font-size:.94rem}.copyright{font-size:.78rem;color:#8190a3;margin-top:.8rem}
/* Navigation intégrée dans le header, comme la maquette */
[data-testid="stTabs"]>div:first-child{position:relative;z-index:20}
[data-baseweb="tab-list"]{position:relative!important;top:-91px!important;margin-left:315px!important;width:calc(100% - 340px)!important;height:78px!important;align-items:center!important;gap:12px!important;margin-bottom:-76px!important;border-bottom:0!important;background:transparent!important}
button[data-baseweb="tab"]{height:76px!important;padding:0 18px!important;border-radius:0!important;color:#17283b!important;background:transparent!important;font-size:.98rem!important;border:0!important}
button[data-baseweb="tab"] p{color:inherit!important;font-size:.98rem!important;white-space:nowrap!important}
button[data-baseweb="tab"]:hover{color:var(--pf-blue)!important;background:#f5faff!important}
button[data-baseweb="tab"][aria-selected="true"],button[data-baseweb="tab"][aria-selected="true"] p{color:var(--pf-blue)!important;font-weight:700!important}
button[data-baseweb="tab"]:last-child{margin-left:auto!important;padding-left:12px!important;padding-right:14px!important}
button[data-baseweb="tab"]:last-child:before{content:"MR";display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;margin-right:10px;border-radius:50%;background:#0b8cff;color:white;font-weight:800;font-size:.86rem}
div[data-baseweb="tab-highlight"]{background:#0b8cff!important;height:4px!important;border-radius:4px 4px 0 0!important}
[data-baseweb="input"]>div,[data-baseweb="base-input"],.stTextInput input,.stNumberInput input,.stTextArea textarea{background:#fff!important;color:var(--pf-text)!important;border-color:#d6e0eb!important}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{min-height:46px;border-radius:9px!important;border:1px solid #acd3fb!important;background:#fff!important;color:#0b66bd!important;font-weight:650!important}.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{border-color:var(--pf-blue)!important;color:var(--pf-blue)!important;background:#f3f9ff!important}button[kind="primary"],.stFormSubmitButton button[kind="primary"],.stDownloadButton button[kind="primary"]{background:#0b8cff!important;color:#fff!important;border-color:#0b8cff!important;box-shadow:0 6px 15px rgba(11,140,255,.20)!important}
[data-testid="stFileUploaderDropzone"]{min-height:78px!important;background:#f7fbff!important;border:1px solid #b8d9f8!important;border-radius:12px!important;padding:12px 16px!important}[data-testid="stFileUploaderDropzone"] button{background:#0b8cff!important;color:#fff!important;border-color:#0b8cff!important}
div[data-testid="stMetric"]{background:#fff;border:1px solid #d6e0ea;padding:16px 20px;border-radius:13px;box-shadow:0 3px 12px rgba(31,55,84,.035)}div[data-testid="stMetricLabel"] p{font-size:.92rem!important;color:#25384d!important}div[data-testid="stMetricValue"]{color:#071b33!important;font-size:1.72rem!important}
[data-testid="stAlert"]{border-radius:10px!important}.auth-card{max-width:620px;margin:1.2rem auto 0;padding:1.35rem;border:1px solid var(--pf-border);border-radius:16px;background:#fff}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid #dbe5ef;border-radius:11px;overflow:hidden}[data-testid="stExpander"]{background:#fff!important;border:1px solid #dbe5ef!important;border-radius:10px!important}
div[data-testid="element-container"]:has(iframe[title="streamlit_cookies_controller.cookie_controller.cookie_controller"]){display:none!important}
h1,h2,h3,h4,h5,h6,p,label,[data-testid="stMarkdownContainer"]{color:var(--pf-text)}[data-testid="stCaptionContainer"],.stCaption{color:var(--pf-muted)!important}
h3{font-size:1.75rem!important;font-weight:800!important;letter-spacing:-.02em!important;margin-top:.65rem!important}
.pf-title{display:flex;align-items:center;gap:14px;margin:16px 0 0}.pf-title .ico{font-size:2.45rem;color:#0b8cff}.pf-title h2{margin:0;font-size:2rem;font-weight:820;letter-spacing:-.025em}.pf-sub{color:#42566d;margin:1px 0 22px 58px;font-size:1rem}
.pf-supplier-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:12px 0 18px}.pf-supplier-card{background:#fff;border:1px solid #dbe5ef;border-radius:13px;padding:16px;box-shadow:0 4px 14px rgba(31,55,84,.04)}.pf-supplier-name{font-size:1.05rem;font-weight:800;color:#0b1f33}.pf-supplier-meta{font-size:.82rem;color:#6b7f97;margin-top:5px}.pf-best-card{border-color:#77d7ad;background:#f2fff9}.pf-best-card .pf-supplier-name{color:#087a4d}
.pf-table-wrap{overflow-x:auto;border:1px solid #d7e2ee;border-radius:12px;background:#fff;margin:12px 0 16px}.pf-table{border-collapse:collapse;width:100%;min-width:1100px;font-size:.88rem}.pf-table th,.pf-table td{border-right:1px solid #e2e9f1;border-bottom:1px solid #e8eef4;padding:10px 9px;white-space:nowrap;text-align:right}.pf-table th{background:#f2f6fa;color:#23374d;font-weight:700}.pf-table th.left,.pf-table td.left{text-align:left}.pf-table .supplier-head{background:#eaf4ff;color:#096ecf;text-align:center}.pf-table .best-head{background:#e9fbf3;color:#087a4d;text-align:center}.pf-table td.best{background:#effcf6;color:#087a4d;font-weight:800}.pf-table tr.total td{font-weight:800;background:#f6f9fc}.pf-table tr.total td.best{background:#e6f9f0}.pf-bottom{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0 18px}.pf-note{background:#fff;border:1px solid #dbe5ef;border-radius:13px;padding:16px}.pf-note.green{border-color:#72d5a9;background:#f2fff9}.pf-note strong{font-size:1.15rem}.pf-note.green strong{color:#087a4d}
@media(max-width:1050px){[data-baseweb="tab-list"]{margin-left:250px!important;width:calc(100% - 270px)!important;gap:2px!important}button[data-baseweb="tab"]{padding:0 8px!important}button[data-baseweb="tab"]:last-child:before{display:none}}
@media(max-width:768px){.block-container{padding:.7rem}.hero{height:auto;padding:15px}.hero h1{font-size:1.8rem}.hero p{font-size:.82rem}[data-baseweb="tab-list"]{position:static!important;top:auto!important;margin:0!important;width:100%!important;height:auto!important;overflow-x:auto!important}button[data-baseweb="tab"]{height:52px!important}.pf-bottom{grid-template-columns:1fr}.pf-sub{margin-left:0}}
</style>
<div class="hero"><h1><span class="price">Price</span><span class="flow">Flow</span></h1><p>Analyse & comparaison des achats</p></div>
""", unsafe_allow_html=True)

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
        m = re.search(r"\d{2}/\d{2}/\d{4}\s+([0-9][0-9 ]{3,})\s+\d", text)
        if m: return re.sub(r"\s+", "", m.group(1))

    if supplier == "ANCONETTI":
        m = re.search(r"O\s*F\s*F\s*R\s*E\s*D\s*E\s*P\s*R\s*I\s*X\s*\n\s*([0-9.]+)", text, re.I)
        if m: return m.group(1)

    if supplier == "MPS":
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
    }
    for pat in supplier_patterns.get(supplier, []):
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)

    return "Non détecté"

def detect_total_ht(text, supplier=None):
    # Détection du Total HT quel que soit son emplacement sur la ligne.
    # Compatible notamment : Outillage Méridional, First, Anconetti, MPS,
    # Aredis, PUM et CEDEO.
    normalized = text.replace("\u00a0", " ")
    money = r"([0-9][0-9 .]*[,.][0-9]{2,4})"

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
        if any(x in low for x in ["hors ecocontrib", "hors éco"]):
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
    charges = []
    seen = set()

    for raw in text.replace("\u00a0", " ").splitlines():
        line = clean(raw)
        low = line.lower()

        # ALDES : l'éco-participation affichée est déjà incluse dans les prix / total articles.
        if re.search(r"^Dont\s+(?:eco|éco)-?participation\s+HT\s*:", line, re.I):
            continue

        # CLIM+ / Saint-Gobain : lignes récapitulatives en bas du document.
        # On ignore volontairement les lignes article "... HT : 0,60 € / PCE"
        # et on prend seulement les totaux "Dont éco-contribution DEEE : 1,20 €".
        m_clim = re.search(
            r"^Dont\s+(?:eco|éco)-?contribution\s+(?:DEEE|PMCB)\s*:\s*"
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

        if re.search(r"\b(?:eco|éco)\s*contribution\b", low):
            # Ligne article, ex. ANCONETTI :
            # 454 ECO CONTRIBUTION REP 1,000 PCE 0,04 0,04
            m = re.search(
                r"(?:eco|éco)\s*contribution(?:\s+rep)?\s+"
                r"([0-9]+(?:[,.][0-9]+)?)\s+"
                r"(?:PCE|PCS|PIECE|PIÈCE|ML|M|U|UN|KG)\s+"
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
                r"(?:eco|éco)\s*contribution\s*[:.]?\s*"
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
    lines = [clean(x) for x in text.splitlines() if clean(x)]

    if supplier == "FIRST ROBINETTERIE":
        pat = re.compile(r"^\S+\s+\d+[,.]\d+\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:ML|PCE|U|M|KG|BAG)\s+(\d+(?:[.,]\d{1,4})?)\s+\d+(?:[.,]\d+)$", re.I)
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": m.group(1), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

    elif supplier == "ANCONETTI":
        pat = re.compile(r"^\S+\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+(?:PCE|ML|M|U|KG)\s+(\d+(?:[.,]\d+)?)\s+\d+(?:[.,]\d+)$", re.I)
        for line in lines:
            m = pat.match(line)
            if m and "eco contribution" not in m.group(1).lower():
                rows.append({"Désignation": m.group(1), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

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
        # pdfplumber lit OUEST ISOL dans cet ordre :
        # "Normalement disponible 1,00"
        # "1 C020205127000 ALUFLEX ... CTN 13,71 € 13.71 €"
        # "Agence"
        # La quantité est donc souvent sur la ligne juste AVANT l'article.
        last_qty = None

        for i, line in enumerate(lines):
            mq = re.search(
                r"(?:Normalement\s+disponible|Disponible|En\s+stock)\s+"
                r"(\d+(?:[.,]\d+)?)\s*$",
                line, re.I
            )
            if mq:
                last_qty = fr_float(mq.group(1))
                continue

            m = re.match(
                r"^\d+\s+([A-Z0-9_-]{6,})\s+(.+?)\s+"
                r"(CTN|PCE|PCS|PC|U|UN|ML|M|KG)\s+"
                r"(\d+(?:[.,]\d+)?)\s*€?\s+"
                r"(\d+(?:[.,]\d+)?)\s*€?\s*$",
                line, re.I
            )
            if m:
                qty = last_qty if last_qty is not None else 1.0
                rows.append({
                    "Désignation": clean(m.group(2)),
                    "Quantité": qty,
                    "Prix unitaire": fr_float(m.group(4))
                })
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
                "Prix unitaire": pu_net
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
        pat = re.compile(
            r"^\S+(?:\s+\S+)?\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+"
            r"(?:ML|PCE|U|UN|M|KG)\s+(\d+(?:[.,]\d+)?)\s*€?\s+"
            r"\d+(?:[.,]\d+)?\s*€?$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": clean(m.group(1)), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

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

def dedupe(rows):
    out, seen = [], set()
    for r in rows:
        key = (clean(r["Désignation"]).lower(), round(float(r["Quantité"]), 5), round(float(r["Prix unitaire"]), 5))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def best_pdf_text(pdf_bytes):
    """Choisit la meilleure couche texte disponible sans OCR."""
    texts = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texts.append("\n".join(page.extract_text(x_tolerance=2, y_tolerance=3) or "" for page in pdf.pages))
    except Exception:
        pass
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        texts.append("\n".join((page.extract_text() or "") for page in reader.pages).replace("\x00", ""))
    except Exception:
        pass
    return "\n".join(t for t in texts if t)

def extract_document(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = best_pdf_text(pdf_bytes)
        supplier = detect_supplier(text)
        number = detect_document_number(text, supplier)
        total_ht = detect_total_ht(text, supplier)
        extra_charges = detect_extra_charges(text)

        rows = table_rows(pdf)
        # Certains fournisseurs ont des PDF sans tableau exploitable.
        if not rows or supplier in ["FIRST ROBINETTERIE", "ANCONETTI", "PUM", "MPS", "ALDES", "REXEL", "OUEST ISOL", "PROLIANS", "LORFLEX", "FRITEC", "RICHARDSON", "FRANS BONHOMME", "H-TUBE / POINT PLASTIQUE", "RODACLIM", "PACK SERVICE"]:
            specific = text_rows(text, supplier)
            if specific:
                rows = specific

        # Ne pas supprimer les lignes identiques chez AREDIS :
        # un même article peut être réellement livré/facturé deux fois sur le BL
        # (notamment lors d'un passage de page).
        if supplier != "AREDIS":
            rows = dedupe(rows)

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

        return rows, supplier, number, total_ht, extra_charges

def extract_pdf_text(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)

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
    if "loxam" in low and "offre de location" in low:
        return "LOXAM"
    if "actis location" in low or "actemis vitrolles" in low:
        return "ACTIS LOCATION"
    if "acces-industrie.com" in low or "accès industrie" in low or "acces industrie" in low:
        return "ACCÈS INDUSTRIE"
    return "Loueur non identifié"

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
    }

    if supplier == "ACTIS LOCATION":
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
        m = re.search(r"N[°º]\s+([0-9]{16,})\s+dduu\s+\d{1,2}/\d{1,2}/\d{2}", text, re.I)
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

        m = re.search(r"\d{3}-\d{4}\s+(.+?)\n", text)
        if m:
            result["Matériel"] = clean(m.group(1))

        # Lignes chiffrées
        line_patterns = [
            ("LOCATION / TOTAL PÉRIODE", r"Total période\s+([0-9 ]+[,.]\d{2})"),
            ("GARANTIE DOMMAGES", r"(?:Garantie dommages|GGaarraannttiiee ddoommmmaaggeess)\s+([0-9 ]+[,.]\d{2})"),
            ("CONTRIBUTION VERTE", r"Contribution verte\s+([0-9 ]+[,.]\d{2})"),
            ("TRANSPORT ALLER", r"Transport Aller\s+([0-9 ]+[,.]\d{2})"),
            ("TRANSPORT RETOUR", r"Transport Retour\s+([0-9 ]+[,.]\d{2})"),
            ("MAJORATION TRANSPORT RETOUR", r"MAJORATION TRANSPORT RETOUR.*?\s([0-9 ]+[,.]\d{2})\s*$"),
            ("MAJORATION TRANSPORT ALLER", r"MAJORATION TRANSPORT ALLER.*?\s([0-9 ]+[,.]\d{2})\s*$"),
            ("FORFAIT RECHARGE ÉLECTRIQUE", r"FORFAIT RECHARGE ELEC\.?[^\n]*?\s([0-9 ]+[,.]\d{2})\s*$"),
        ]
        for label, pat in line_patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                result["Lignes"].append({"Désignation": label, "Montant HT": fr_float(m.group(1))})

        # Total prévisionnel HT (libellé normal ou caractères doublés).
        m = re.search(r"(?:Total Prévisionnel HT|TToottaall PPrréévviissiioonnnneell HHTT)\s+([0-9 ]+[,.]\d{2})", text, re.I)
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

        # Ce format ne présente pas de total HT global imprimé.
        result["Total HT document"] = None

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
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.subheader("Bienvenue sur PriceFlow")
    st.caption("Connectez-vous pour accéder à votre espace et à vos outils PriceFlow.")

    login_tab, signup_tab = st.tabs(["🔐 Se connecter", "✨ Créer un compte"])

    with login_tab:
        with st.form("pf_login_form"):
            email = st.text_input("Adresse e-mail", key="pf_login_email")
            password = st.text_input("Mot de passe", type="password", key="pf_login_password")
            submitted = st.form_submit_button("Se connecter", use_container_width=True)
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
            submitted = st.form_submit_button("Créer mon compte", use_container_width=True)

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

    st.markdown("</div>", unsafe_allow_html=True)

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


tab_achats, tab_location, tab_compare, tab_stats, tab_account = st.tabs(["▣  Achats / Fournisseurs", "🏗  Locations", "⚖  Comparatif", "▮▮▮  Statistiques", "Mon compte ⌄"])

with tab_achats:
    st.subheader("📦 Achats / Fournisseurs")

    top1, top2 = st.columns([5, 1])
    with top2:
        if st.button("↻ Nouveau BL", use_container_width=True):
            new_document()

    uploaded = st.file_uploader(
        "Déposez votre BL / bon d'enlèvement / commande / offre de prix",
        type=["pdf"],
        accept_multiple_files=False,
        key=f"pdf_{st.session_state.uploader_key}",
    )

    if uploaded:
        try:
            rows, supplier, doc_number, total_ht, extra_charges = extract_document(uploaded.getvalue())

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
                        "Référence": "",
                        "Désignation": str(r.get("Désignation", "") or ""),
                        "Quantité": r.get("Quantité"),
                        "Prix unitaire": r.get("Prix unitaire"),
                    })

                # N'ajoute les frais complémentaires que s'ils ne sont PAS déjà
                # inclus dans les prix unitaires des articles.
                # Exemple CLIM+ : les lignes "Dont éco-contribution" sont informatives
                # et les PU articles donnent déjà exactement le Total HT.
                articles_total = round(sum(
                    float(r.get("Quantité", 0) or 0) * float(r.get("Prix unitaire", 0) or 0)
                    for r in export_rows
                ), 2)

                charges_to_add = list(extra_charges)
                if total_ht is not None:
                    gap_before_extras = round(float(total_ht) - articles_total, 2)
                    detected_extras = round(sum(float(x["amount"]) for x in extra_charges), 2) if extra_charges else 0.0

                    # Si les articles atteignent déjà le Total HT, l'éco-contribution
                    # est déjà comprise dans les PU : ne pas la rajouter une 2e fois.
                    if abs(gap_before_extras) <= 0.01:
                        charges_to_add = []
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
                total_extrait = 0.0
                for _, row in df.iterrows():
                    try:
                        qte = float(row["Quantité"])
                        pu = float(row["Prix unitaire"])
                        total_extrait += qte * pu
                    except (TypeError, ValueError):
                        pass
                total_extrait = round(total_extrait, 2)
                ecart = round(total_ht - total_extrait, 2) if total_ht is not None else None

                ctrl1, ctrl2, ctrl3 = st.columns(3)
                ctrl1.metric("Total HT du BL", fmt_money(total_ht))
                ctrl2.metric("Total extrait", fmt_money(total_extrait))
                ctrl3.metric("Écart", fmt_money(ecart))

                if extra_charges:
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
                elif extra_charges and not charges_to_add:
                    st.info(
                        "♻️ Éco-contribution détectée, mais déjà incluse dans les prix unitaires des articles. "
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

                st.success(f"{len(df)} ligne(s) article extraite(s)")
                st.subheader("Aperçu avant export")
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

                signature = (uploaded.name, doc_number, len(df), total_ht, total_extrait)
                if st.session_state.saved_signature != signature:
                    entry = {
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Fournisseur": supplier,
                        "N° document": doc_number,
                        "Lignes": len(df),
                        "Total HT BL": fmt_money(total_ht),
                        "Total extrait": fmt_money(total_extrait),
                        "Écart": fmt_money(ecart),
                        "Fichier": uploaded.name,
                    }
                    ok, cloud_msg = save_document_cloud(uploaded, supplier, doc_number, total_ht, total_extrait, ecart, export_rows)
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
            st.error(f"Erreur de lecture du PDF : {e}")

with tab_location:
    st.subheader("🏗️ Locations")

    if "location_uploader_key" not in st.session_state:
        st.session_state.location_uploader_key = 0

    loc_top1, loc_top2 = st.columns([5, 1])
    with loc_top2:
        if st.button("↻ Nouvelle location", use_container_width=True):
            st.session_state.location_uploader_key += 1
            st.rerun()

    uploaded_loc = st.file_uploader(
        "Déposez votre devis / offre de location",
        type=["pdf"],
        accept_multiple_files=False,
        key=f"location_pdf_{st.session_state.location_uploader_key}",
    )

    if uploaded_loc:
        try:
            loc = extract_rental(uploaded_loc.getvalue())
            c1, c2 = st.columns(2)
            c1.metric("Loueur", loc["Loueur"])
            c2.metric("N° document", loc["N° document"])

            d1, d2, d3 = st.columns(3)
            d1.metric("Début", loc["Date début"] or "Non détecté")
            d2.metric("Fin", loc["Date fin"] or "Non détecté")
            d3.metric("Durée", loc["Durée"] or "Non détectée")

            st.info(f"Matériel : **{loc['Matériel']}**")

            if loc["Lignes"]:
                loc_df = pd.DataFrame(loc["Lignes"], columns=["Désignation", "Montant HT"])
                total_loc = round(float(loc_df["Montant HT"].sum()), 2)
                total_doc = loc["Total HT document"]
                ecart_loc = round(total_doc - total_loc, 2) if total_doc is not None else None

                m1, m2, m3 = st.columns(3)
                m1.metric("Total HT document", fmt_money(total_doc))
                m2.metric("Total extrait", fmt_money(total_loc))
                m3.metric("Écart", fmt_money(ecart_loc))

                if total_doc is None:
                    st.info(
                        "ℹ️ Aucun Total HT global n'est imprimé sur ce devis. "
                        "Le total extrait correspond uniquement aux lignes chiffrées présentes dans l'offre."
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

                st.subheader("Détail de la location")
                st.dataframe(loc_df, use_container_width=True, hide_index=True)

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
                }])

                out_loc = io.BytesIO()
                with pd.ExcelWriter(out_loc, engine="xlsxwriter") as writer:
                    export_loc.to_excel(writer, index=False, sheet_name="Synthèse")
                    loc_df.to_excel(writer, index=False, sheet_name="Détail")
                    wb = writer.book
                    ws1 = writer.sheets["Synthèse"]
                    ws2 = writer.sheets["Détail"]
                    money_fmt = wb.add_format({"num_format": "0.00"})
                    ws1.set_column("A:C", 28)
                    ws1.set_column("D:F", 16)
                    ws1.set_column("G:I", 18, money_fmt)
                    ws2.set_column("A:A", 42)
                    ws2.set_column("B:B", 18, money_fmt)
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
            st.error(f"Erreur de lecture du PDF Location : {e}")


with tab_compare:
    st.markdown('<div class="pf-title"><span class="ico">⚖️</span><h2>Comparatif fournisseurs</h2></div><p class="pf-sub">Comparez vos devis et identifiez automatiquement les meilleurs prix</p>', unsafe_allow_html=True)

    compare_files = st.file_uploader("Déposez 2 devis ou plus", type=["pdf"], accept_multiple_files=True, key="compare_pdfs")
    if compare_files:
        if len(compare_files) < 2:
            st.info("Ajoutez au moins 2 devis pour lancer la comparaison.")
        else:
            offers, errors = [], []
            for f in compare_files:
                try:
                    rws, sup, num, tht, extras = extract_document(f.getvalue())
                    offers.append({"Fichier":f.name,"Fournisseur":sup,"N° document":num,"Total HT":tht,"Lignes":rws})
                except Exception as e:
                    errors.append(f"{f.name} : {e}")
            if errors: st.warning("Certains fichiers n'ont pas pu être lus : " + " | ".join(errors))
            if offers:
                sig=("comparatif",tuple((o["Fichier"],o["N° document"]) for o in offers))
                if st.session_state.get("compare_usage_sig") != sig:
                    track_usage("comparatif", {"documents":len(offers),"suppliers":[o["Fournisseur"] for o in offers]})
                    st.session_state.compare_usage_sig=sig

                cards=''.join(f'<div class="pf-supplier-card"><div class="pf-supplier-name">{html.escape(str(o["Fournisseur"]))}</div><div class="pf-supplier-meta">N° {html.escape(str(o["N° document"]))}<br>{len(o["Lignes"])} article(s) · {fmt_money(o["Total HT"])}</div></div>' for o in offers)
                st.markdown(f'<div class="pf-supplier-grid">{cards}</div>', unsafe_allow_html=True)

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
                        top1,top2=st.columns([3,1])
                        with top1: st.success(f"🏆 Meilleurs prix identifiés automatiquement sur {len(comparable)} ligne(s) comparable(s).")
                        with top2: st.metric("Économie potentielle", fmt_money(saving))

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
                                    body+=f'<td{cls}>{pu:,.2f}</td><td{cls}>{total:,.2f}</td>'; er[f'{sup} PU']=pu; er[f'{sup} Total']=total
                            best_total_sum+=r["best_total"]
                            body+=f'<td class="best left">{html.escape(str(r["best_sup"]))}</td><td class="best">{r["best_pu"]:,.2f}</td><td class="best">{r["best_total"]:,.2f}</td><td>{r["gap"]:,.2f}</td><td>{r["gap_pct"]:.1f}%</td></tr>'
                            er.update({"Meilleur fournisseur":r["best_sup"],"Meilleur PU":r["best_pu"],"Meilleur total":r["best_total"],"Écart max €":r["gap"],"Écart max %":r["gap_pct"]}); export.append(er)
                        body+='<tr class="total"><td colspan="2" class="left">TOTAL</td><td></td>'
                        for sup in suppliers: body+=f'<td></td><td>{totals[sup]:,.2f}</td>'
                        body+=f'<td class="best"></td><td class="best"></td><td class="best">{best_total_sum:,.2f}</td><td>{saving:,.2f}</td><td>{saving_pct:.1f}%</td></tr>'
                        table=f'<div class="pf-table-wrap"><table class="pf-table"><thead>{h1}{h2}</thead><tbody>{body}</tbody></table></div>'
                        st.markdown(table,unsafe_allow_html=True)
                        st.markdown(f'<div class="pf-bottom"><div class="pf-note green">En choisissant les meilleurs prix<br><strong>Vous économisez {fmt_money(saving)}</strong><br><span>Soit {saving_pct:.1f}% par rapport aux prix les plus élevés comparables</span></div><div class="pf-note">📊 Analyse terminée<br><strong>{len(rows)} lignes analysées</strong><br><span>Meilleurs prix trouvés sur {len(comparable)} lignes comparables</span></div></div>',unsafe_allow_html=True)
                        out_cmp=io.BytesIO(); edf=pd.DataFrame(export)
                        with pd.ExcelWriter(out_cmp,engine="xlsxwriter") as writer:
                            edf.to_excel(writer,index=False,sheet_name="Comparatif")
                            ws=writer.sheets["Comparatif"]; ws.set_column("A:A",6); ws.set_column("B:B",45); ws.set_column("C:Z",17)
                        out_cmp.seek(0)
                        st.download_button("⬇ Télécharger le comparatif Excel",data=out_cmp,file_name="Comparatif_fournisseurs.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary",use_container_width=True)
                    else: st.warning("Aucune ligne exploitable pour la comparaison.")
                else: st.warning("Aucune ligne exploitable pour la comparaison.")


st.divider()
with st.expander("Historique de contrôle", expanded=False):
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True, hide_index=True)
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("↻ Actualiser"):
                load_cloud_history(force=True)
                st.rerun()
        with c2:
            hist_csv = pd.DataFrame(st.session_state.history).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("Exporter l'historique CSV", hist_csv, "historique_extracteur.csv", "text/csv")
    else:
        st.caption("Aucun document traité pour le moment.")

st.caption("Historique de contrôle indépendant des fichiers Excel. Le Total HT n'est jamais ajouté à l'export.")

with tab_stats:
    st.markdown('<div class="pf-title"><span class="ico">▮▮▮</span><h2>Statistiques</h2></div><div class="pf-sub">Suivez l’utilisation et l’activité de PriceFlow</div>', unsafe_allow_html=True)
    hist_df = pd.DataFrame(st.session_state.history or [])
    s1, s2, s3 = st.columns(3)
    s1.metric("Documents enregistrés", len(hist_df))
    s2.metric("Fournisseurs", hist_df["Fournisseur"].nunique() if not hist_df.empty and "Fournisseur" in hist_df else 0)
    s3.metric("Compte", "Administrateur" if is_admin() else "Utilisateur")
    if not hist_df.empty:
        st.markdown("### Activité récente")
        st.dataframe(hist_df.head(25), use_container_width=True, hide_index=True)
    else:
        st.info("Les statistiques apparaîtront ici dès que des documents auront été analysés.")

with tab_account:
    st.subheader("👤 Mon compte")
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
                st.line_chart(daily)

        if perr:
            st.caption("Le nombre total d'inscrits sera disponible après création de la vue admin_profiles dans Supabase (SQL fourni avec cette version).")
        elif not pdf.empty:
            with st.expander("Voir les comptes inscrits"):
                show_profiles = pdf.rename(columns={"email":"E-mail", "created_at":"Inscription", "last_sign_in_at":"Dernière connexion"})
                st.dataframe(show_profiles[[c for c in ["E-mail", "Inscription", "Dernière connexion"] if c in show_profiles]], use_container_width=True, hide_index=True)

    if st.button("🚪 Se déconnecter", use_container_width=False):
        logout_priceflow()

st.markdown('<div class="copyright">© 2026 Michel RACHOU · PriceFlow V21</div>', unsafe_allow_html=True)
