import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Gatepass Reader", page_icon="🚚", layout="wide")
st.title("Eeki Gatepass Reader (Customer / Crop / Bags / Qty)")

uploaded = st.file_uploader("Upload Gatepass (PDF)", type=["pdf"])

def extract_customer_from_text(text: str) -> str:
    customer = ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        # Pattern like: "From : ...", "To:" on same or next line
        if line.startswith("To:"):
            # e.g. "To: PJTJ TECHNOLOGIES PVT LTD"
            customer = line.replace("To:", "").strip()
            # Sometimes address continues on next line(s) – we only want name
            break
    return customer

def parse_gatepass_pdf(file_bytes: bytes) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            customer = extract_customer_from_text(text)

            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                header = [c.strip() if c else "" for c in tbl[0]]

                # Detect the "Total Bags/Boxes" table
                if ("Crop Name" in header
                    and "Total Number of Bags/Boxes" in header
                    and "Total Quantity (kgs)" in header):

                    crop_idx = header.index("Crop Name")
                    bags_idx = header.index("Total Number of Bags/Boxes")
                    qty_idx = header.index("Total Quantity (kgs)")

                    for r in tbl[1:]:
                        if not any(r):
                            continue
                        crop = (r[crop_idx] or "").strip()
                        if crop.lower() == "total" or crop == "":
                            continue

                        bags_raw = (r[bags_idx] or "").replace(",", "").strip()
                        qty_raw = (r[qty_idx] or "").replace(",", "").strip()

                        try:
                            bags = int(bags_raw)
                        except:
                            bags = bags_raw
                        try:
                            qty = int(qty_raw)
                        except:
                            qty = qty_raw

                        rows.append({
                            "Customer": customer,
                            "Crop": crop,
                            "Bags": bags,
                            "Quantity_kg": qty,
                        })
    return pd.DataFrame(rows)

if uploaded:
    df = parse_gatepass_pdf(uploaded.read())
    if df.empty:
        st.error("Could not detect customer/crop table. Check file format.")
    else:
        st.success("Gatepass read successfully ✅")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "gatepass_summary.csv")
