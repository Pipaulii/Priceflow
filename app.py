
import io
import re
import pdfplumber
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Extracteur PDF → Excel", page_icon="📄", layout="wide")
st.title("Extracteur PDF → Excel")
st.caption("Déposez un ou plusieurs bons/factures PDF. L'application extrait uniquement : Désignation, Quantité et Prix unitaire.")

def fr_float(s):
    if s is None:
        return None
    s = str(s).strip().replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except:
        return None

def clean_desc(s):
    return re.sub(r"\s+", " ", s).strip(" -")

def extract_lines(pdf_bytes):
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            # Priorité aux tableaux : fiable pour les BL/factures structurés.
            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue
                # Cherche une ligne d'en-tête contenant Description et P.U.
                header_idx = None
                header = None
                for i, r in enumerate(table[:12]):
                    vals = [str(x or "").replace("\n", " ").strip().lower() for x in r]
                    joined = " | ".join(vals)
                    if ("description" in joined or "désignation" in joined) and ("p.u" in joined or "prix unitaire" in joined):
                        header_idx, header = i, vals
                        break
                if header_idx is None:
                    continue

                def col_index(keys):
                    for j, h in enumerate(header):
                        if any(k in h for k in keys):
                            return j
                    return None

                dcol = col_index(["description", "désignation"])
                qcol = col_index(["qté livrée", "qte livree", "quantité", "quantite"])
                if qcol is None:
                    # Sur certains PDF l'en-tête Qté / livrée est éclaté.
                    for j, h in enumerate(header):
                        if "livr" in h:
                            qcol = j
                            break
                pcol = col_index(["p.u", "prix unitaire"])
                if dcol is None or qcol is None or pcol is None:
                    continue

                for r in table[header_idx+1:]:
                    if not r or max(dcol, qcol, pcol) >= len(r):
                        continue
                    desc = clean_desc(str(r[dcol] or "").replace("\n", " "))
                    qty = fr_float(r[qcol])
                    pu = fr_float(r[pcol])
                    # Ignore sous-titres, totaux, lignes vides et éco-participations.
                    low = desc.lower()
                    if not desc or qty is None or pu is None:
                        continue
                    if any(x in low for x in ["total ", "dont eco", "dont éco", "transformé de", "reference gaz", "référence gaz"]):
                        continue
                    rows.append({"Désignation": desc, "Quantité": qty, "Prix unitaire": pu})

            # Secours pour les PDF dont les tableaux ne sont pas détectés.
            if not tables:
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                for line in text.splitlines():
                    line = re.sub(r"\s+", " ", line).strip()
                    # Format courant : CODE DESCRIPTION U QTE PU MONTANT TVA
                    m = re.match(r"^\S+\s+(.+?)\s+U\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d{1,4})?)\s+\d+(?:[.,]\d+)?\s+20[.,]00$", line, re.I)
                    if m:
                        rows.append({
                            "Désignation": clean_desc(m.group(1)),
                            "Quantité": fr_float(m.group(2)),
                            "Prix unitaire": fr_float(m.group(3)),
                        })
    return rows

files = st.file_uploader("Glissez vos PDF ici", type=["pdf"], accept_multiple_files=True)

if files:
    all_rows = []
    for f in files:
        try:
            extracted = extract_lines(f.getvalue())
            all_rows.extend(extracted)
            st.success(f"{f.name} : {len(extracted)} ligne(s) extraite(s)")
        except Exception as e:
            st.error(f"{f.name} : erreur de lecture — {e}")

    if all_rows:
        df = pd.DataFrame(all_rows, columns=["Désignation", "Quantité", "Prix unitaire"])
        # Affichage propre des quantités entières.
        df["Quantité"] = df["Quantité"].apply(lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x)

        st.subheader("Aperçu")
        st.dataframe(df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Extraction")
            ws = writer.book["Extraction"]
            ws.column_dimensions["A"].width = 55
            ws.column_dimensions["B"].width = 14
            ws.column_dimensions["C"].width = 18
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)
            for cell in ws["C"][1:]:
                cell.number_format = '#,##0.0000 [$€-fr-FR]'
        output.seek(0)

        st.download_button(
            "Télécharger l'Excel",
            data=output,
            file_name="extraction_factures.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.warning("Aucune ligne article reconnue. Le PDF peut utiliser une mise en page différente ou être un scan.")
else:
    st.info("Ajoutez un ou plusieurs fichiers PDF pour commencer.")
