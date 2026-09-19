import io
import re
from datetime import datetime

import pdfplumber
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Extracteur PDF → Excel", page_icon="📄", layout="wide")
st.title("Extracteur PDF → Excel")
st.caption("Déposez un ou plusieurs bons/factures PDF. L'application extrait uniquement : Désignation, Quantité et Prix unitaire.")

if "history" not in st.session_state:
    st.session_state.history = []


def fr_float(s):
    if s is None:
        return None
    s = str(s).strip().replace("€", "").replace("\u00a0", " ").replace(" ", "")
    # Formats FR (1 234,56) et formats simples (1234.56)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def clean_desc(s):
    return re.sub(r"\s+", " ", s).strip(" -")


def extract_document(pdf_bytes):
    rows = []
    total_candidates = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""

            # Cherche un total explicite du document. On évite les sous-totaux et TVA.
            for raw_line in text.splitlines():
                line = re.sub(r"\s+", " ", raw_line).strip()
                low = line.lower()
                if "total" not in low:
                    continue
                if any(x in low for x in ["sous-total", "sous total", "total tva", "total taxe", "total remise"]):
                    continue
                nums = re.findall(r"(?:\d{1,3}(?:[ .]\d{3})+|\d+)[,.]\d{2,4}", line)
                if nums:
                    value = fr_float(nums[-1])
                    if value is not None:
                        # Priorité au total HT, puis TTC, puis toute ligne Total.
                        priority = 3 if re.search(r"total\s*h\.?t", low) else 2 if "ttc" in low else 1
                        total_candidates.append((priority, value, line))

            # Priorité aux tableaux : fiable pour les BL/factures structurés.
            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue
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
                    for j, h in enumerate(header):
                        if "livr" in h:
                            qcol = j
                            break
                pcol = col_index(["p.u", "prix unitaire"])
                if dcol is None or qcol is None or pcol is None:
                    continue

                for r in table[header_idx + 1:]:
                    if not r or max(dcol, qcol, pcol) >= len(r):
                        continue
                    raw_desc = str(r[dcol] or "").replace("\n", " ")
                    # Certains articles contiennent une 2e ligne "Dont Eco-Part..." dans
                    # la même cellule. Ce n'est pas une ligne séparée : on conserve
                    # l'article et on retire seulement la mention d'éco-contribution.
                    raw_desc = re.split(r"\\bDont\\s+(?:Eco|Éco)-?Part", raw_desc, flags=re.I)[0]
                    desc = clean_desc(raw_desc)
                    qty = fr_float(r[qcol])
                    pu = fr_float(r[pcol])
                    low = desc.lower()
                    if not desc or qty is None or pu is None:
                        continue
                    if any(x in low for x in ["total ", "transformé de", "reference gaz", "référence gaz"]):
                        continue
                    rows.append({"Désignation": desc, "Quantité": qty, "Prix unitaire": pu})

            # Détection robuste du Total HT dans les tableaux de synthèse.
            # Sur certains BL, le libellé et le montant sont dans des cellules séparées,
            # donc extract_text() ne les place pas forcément sur la même ligne.
            for table in tables:
                for r in table or []:
                    if not r:
                        continue
                    for j, cell in enumerate(r):
                        cell_text = str(cell or "")
                        labels = [x.strip() for x in cell_text.split("\n")]
                        if "Total HT" in labels:
                            # Cherche le montant dans les cellules suivantes de la ligne.
                            for value_cell in r[j + 1:]:
                                values = re.findall(r"(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)[,.]\\d{2,4}", str(value_cell or ""))
                                if values:
                                    value = fr_float(values[0])
                                    if value is not None:
                                        total_candidates.append((4, value, "Total HT"))
                                        break

            # Secours pour les PDF dont les tableaux ne sont pas détectés.
            if not tables:
                for line in text.splitlines():
                    line = re.sub(r"\s+", " ", line).strip()
                    m = re.match(r"^\S+\s+(.+?)\s+U\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d{1,4})?)\s+\d+(?:[.,]\d+)?\s+20[.,]00$", line, re.I)
                    if m:
                        rows.append({
                            "Désignation": clean_desc(m.group(1)),
                            "Quantité": fr_float(m.group(2)),
                            "Prix unitaire": fr_float(m.group(3)),
                        })

    detected_total = None
    detected_label = None
    if total_candidates:
        best_priority = max(x[0] for x in total_candidates)
        best = [x for x in total_candidates if x[0] == best_priority][-1]
        detected_total, detected_label = best[1], best[2]

    return rows, detected_total, detected_label


files = st.file_uploader("Glissez vos PDF ici", type=["pdf"], accept_multiple_files=True)

if files:
    all_rows = []
    doc_results = []

    for f in files:
        try:
            extracted, bl_total, bl_total_label = extract_document(f.getvalue())
            all_rows.extend(extracted)
            doc_results.append({
                "Fichier": f.name,
                "Lignes": len(extracted),
                "Total BL": bl_total,
                "Libellé total": bl_total_label,
            })
            st.success(f"{f.name} : {len(extracted)} ligne(s) extraite(s)")
        except Exception as e:
            st.error(f"{f.name} : erreur de lecture — {e}")

    if all_rows:
        df = pd.DataFrame(all_rows, columns=["Désignation", "Quantité", "Prix unitaire"])
        df["Quantité"] = df["Quantité"].apply(lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x)

        st.subheader("Aperçu")
        st.dataframe(df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Le total reste volontairement hors de l'Excel.
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

        left, right = st.columns([2, 1])
        with left:
            st.download_button(
                "Télécharger l'Excel",
                data=output,
                file_name="extraction_factures.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

        with right:
            st.markdown("### Total du BL")
            for result in doc_results:
                st.markdown(f"**{result['Fichier']}**")
                if result["Total BL"] is not None:
                    st.metric("TOTAL HT", f"{result['Total BL']:,.2f} €".replace(",", " "))
                else:
                    st.info("Total HT du BL non détecté automatiquement")

        # Une entrée par traitement, conservée pendant la session Streamlit.
        signature = tuple((r["Fichier"], r["Lignes"], r["Total BL"]) for r in doc_results)
        if st.session_state.get("last_history_signature") != signature:
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            for result in doc_results:
                st.session_state.history.insert(0, {
                    "Date": now,
                    "Fichier": result["Fichier"],
                    "Lignes": result["Lignes"],
                    "Total HT BL": "—" if result["Total BL"] is None else f"{result['Total BL']:,.2f} €".replace(",", " "),
                })
            st.session_state.last_history_signature = signature

        with st.expander("Historique des extractions", expanded=False):
            if st.session_state.history:
                st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True, hide_index=True)
                if st.button("Effacer l'historique"):
                    st.session_state.history = []
                    st.session_state.pop("last_history_signature", None)
                    st.rerun()
            else:
                st.caption("Aucune extraction dans cette session.")
    else:
        st.warning("Aucune ligne article reconnue. Le PDF peut utiliser une mise en page différente ou être un scan.")
else:
    st.info("Ajoutez un ou plusieurs fichiers PDF pour commencer.")
    if st.session_state.history:
        with st.expander("Historique des extractions", expanded=False):
            st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True, hide_index=True)
            if st.button("Effacer l'historique"):
                st.session_state.history = []
                st.session_state.pop("last_history_signature", None)
                st.rerun()
