import io
import json
import re
from datetime import datetime
from pathlib import Path

import pdfplumber
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Extracteur PDF", page_icon="📄", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1450px; padding-top: 2rem;}
.hero {
    padding: 1.4rem 1.6rem;
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 18px;
    margin-bottom: 1.2rem;
    background: linear-gradient(135deg, rgba(40,90,180,.13), rgba(120,60,180,.08));
}
.hero h1 {margin:0; font-size:2.35rem;}
.hero p {margin:.35rem 0 0 0; opacity:.75;}
.copyright {font-size:.82rem; opacity:.58; margin-top:.55rem;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.22);
    padding: 1rem;
    border-radius: 14px;
}
</style>
<div class="hero">
  <h1>Extracteur PDF</h1>
  <p>Extraction automatique des documents fournisseurs vers Excel</p>
</div>
""", unsafe_allow_html=True)

HISTORY_FILE = Path("extracteur_history.json")

def load_history():
    try:
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_history(items):
    try:
        HISTORY_FILE.write_text(json.dumps(items[:500], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

if "history" not in st.session_state:
    st.session_state.history = load_history()
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
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    s = m.group(0)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
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

    elif supplier == "MPS":
        for i, line in enumerate(lines):
            m = re.match(r"^\d+\s+(\d+(?:[.,]\d+)?)\s+\w\s+(\d+(?:[.,]\d+)?)\b", line)
            if m and i > 0:
                desc = lines[i - 1]
                desc = re.sub(r"\s+F\d+$", "", desc).strip()
                if desc and not re.match(r"^\d", desc):
                    rows.append({"Désignation": desc, "Quantité": fr_float(m.group(1)), "Prix unitaire": fr_float(m.group(2))})

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
        pat = re.compile(
            r"^\d+\s+\S+\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s+PC\s+"
            r"\d+(?:[.,]\d+)?\s+Remise\s+-?\d+(?:[.,]\d+)?%\s+"
            r"(\d+(?:[.,]\d+)?)\s+\d+(?:[.,]\d+)?$",
            re.I
        )
        for line in lines:
            m = pat.match(line)
            if m:
                rows.append({"Désignation": m.group(1), "Quantité": fr_float(m.group(2)), "Prix unitaire": fr_float(m.group(3))})

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

def extract_document(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text(x_tolerance=2, y_tolerance=3) or "" for page in pdf.pages)
        supplier = detect_supplier(text)
        number = detect_document_number(text, supplier)
        total_ht = detect_total_ht(text, supplier)
        extra_charges = detect_extra_charges(text)

        rows = table_rows(pdf)
        # Certains fournisseurs ont des PDF sans tableau exploitable.
        if not rows or supplier in ["FIRST ROBINETTERIE", "ANCONETTI", "PUM", "MPS", "ALDES", "REXEL", "OUEST ISOL", "PROLIANS", "LORFLEX", "FRITEC"]:
            specific = text_rows(text, supplier)
            if specific:
                rows = specific

        # Ne pas supprimer les lignes identiques chez AREDIS :
        # un même article peut être réellement livré/facturé deux fois sur le BL
        # (notamment lors d'un passage de page).
        if supplier != "AREDIS":
            rows = dedupe(rows)

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

        m = re.search(r"Renonciation à recours.*?\s+\d+\s+([0-9 ]+[,.]\d{2})\s*€", flat, re.I)
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

tab_achats, tab_location = st.tabs(["📦 Achats / Fournisseurs", "🏗️ Locations"])

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
                    st.session_state.history.insert(0, entry)
                    st.session_state.history = st.session_state.history[:500]
                    save_history(st.session_state.history)
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

st.divider()
with st.expander("Historique de contrôle", expanded=False):
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True, hide_index=True)
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("Effacer l'historique"):
                st.session_state.history = []
                save_history([])
                st.session_state.saved_signature = None
                st.rerun()
        with c2:
            hist_csv = pd.DataFrame(st.session_state.history).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("Exporter l'historique CSV", hist_csv, "historique_extracteur.csv", "text/csv")
    else:
        st.caption("Aucun document traité pour le moment.")

st.caption("Historique de contrôle indépendant des fichiers Excel. Le Total HT n'est jamais ajouté à l'export.")
st.markdown('<div class="copyright">© 2026 Michel RACHOU · V13.5</div>', unsafe_allow_html=True)
