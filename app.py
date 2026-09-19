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
    if "cedeo" in low or "bon d'enlèvement" in low: return "CEDEO"
    if "midipyreneesscellement" in compact or "mpsvitrolles" in compact: return "MPS"
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

    return "Non détecté"

def detect_total_ht(text):
    # Variantes fournisseurs : TOTAL HT, Total H.T., TOTAL H.T.., TOTAL H.T. :
    # On exclut explicitement TTC, TVA et "hors écocontribution".
    normalized = text.replace("\u00a0", " ")
    patterns = [
        r"(?im)^\s*TOTAL\s+H\s*\.?\s*T\s*\.?\s*[:.]*(?:\s*€)?\s*([0-9][0-9 .]*[,.][0-9]{2,4})\b",
        r"(?im)^\s*Total\s+HT\s*[:.]*(?:\s*€)?\s*([0-9][0-9 .]*[,.][0-9]{2,4})\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, normalized):
            line_start = normalized.rfind("\n", 0, m.start()) + 1
            line_end = normalized.find("\n", m.end())
            if line_end == -1:
                line_end = len(normalized)
            line = normalized[line_start:line_end].lower()
            if any(x in line for x in ["hors ecocontrib", "hors éco", "ttc", "tva"]):
                continue
            value = fr_float(m.group(1))
            if value is not None:
                return value

    # Secours si le libellé et le montant sont séparés par une mise en page PDF atypique.
    lines = [clean(x) for x in normalized.splitlines()]
    for i, line in enumerate(lines):
        low = line.lower()
        if re.search(r"\btotal\s+h\s*\.?\s*t\s*\.?", low) and not any(x in low for x in ["hors ecocontrib", "hors éco", "ttc", "tva"]):
            nums = re.findall(r"(?:\d{1,3}(?:[ .]\d{3})+|\d+)[,.]\d{2,4}", line)
            if nums:
                return fr_float(nums[-1])
            # Cherche dans les 2 lignes suivantes seulement.
            for nxt in lines[i+1:i+3]:
                nums = re.findall(r"(?:\d{1,3}(?:[ .]\d{3})+|\d+)[,.]\d{2,4}", nxt)
                if nums:
                    return fr_float(nums[0])
    return None

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
        total_ht = detect_total_ht(text)

        rows = table_rows(pdf)
        # Certains fournisseurs ont des PDF sans tableau exploitable.
        if not rows or supplier in ["FIRST ROBINETTERIE", "ANCONETTI", "PUM", "MPS"]:
            specific = text_rows(text, supplier)
            if specific:
                rows = specific

        rows = dedupe(rows)
        return rows, supplier, number, total_ht

def fmt_money(v):
    if v is None:
        return "Non détecté"
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")

def new_document():
    st.session_state.uploader_key += 1
    st.session_state.saved_signature = None
    st.rerun()

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
        rows, supplier, doc_number, total_ht = extract_document(uploaded.getvalue())

        info1, info2, info3 = st.columns(3)
        info1.metric("Fournisseur", supplier)
        info2.metric("N° document", doc_number)
        info3.metric("Total HT", fmt_money(total_ht))

        if rows:
            for r in rows:
                r["N° document"] = doc_number

            df = pd.DataFrame(rows, columns=["N° document", "Désignation", "Quantité", "Prix unitaire"])
            df["Quantité"] = df["Quantité"].apply(lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x)

            st.success(f"{len(df)} ligne(s) article extraite(s)")
            st.subheader("Aperçu avant export")
            st.dataframe(df, use_container_width=True, hide_index=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Extraction")
                ws = writer.book["Extraction"]
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions
                widths = {"A": 20, "B": 62, "C": 14, "D": 18}
                for col, width in widths.items():
                    ws.column_dimensions[col].width = width
                for cell in ws[1]:
                    cell.font = cell.font.copy(bold=True)
                for cell in ws["D"][1:]:
                    cell.number_format = '#,##0.0000 [$€-fr-FR]'
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

            signature = (uploaded.name, doc_number, len(df), total_ht)
            if st.session_state.saved_signature != signature:
                entry = {
                    "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Fournisseur": supplier,
                    "N° document": doc_number,
                    "Lignes": len(df),
                    "Total HT": fmt_money(total_ht),
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
st.markdown('<div class="copyright">© 2026 Michel RACHOU</div>', unsafe_allow_html=True)
