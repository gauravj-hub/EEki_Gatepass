import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Eeki Gatepass Reader", page_icon="🚚", layout="wide")
st.title("Eeki Gatepass Reader (Customer / Crop / Bags / Qty)")

uploaded = st.file_uploader("Upload Gatepass (PDF)", type=["pdf"])

def extract_customer_from_text(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        if line.startswith("To:"):
            return line.replace("To:", "").strip()
    return ""

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

                # Our PDF has these exact headers in English part:
                # "Crop Name | Total Number of Bags/Boxes | Weight per box (kgs) | Total Quantity (kgs)"
                needed = [
                    "Crop Name",
                    "Total Number of Bags/Boxes",
                    "Total Quantity (kgs)",
                ]
                if not all(h in header for h in needed):
                    continue

                crop_idx = header.index("Crop Name")
                bags_idx = header.index("Total Number of Bags/Boxes")
                qty_idx = header.index("Total Quantity (kgs)")

                for r in tbl[1:]:
                    if not r:
                        continue
                    crop = (r[crop_idx] or "").strip()
                    if crop == "" or crop.lower() == "total":
                        continue

                    bags_raw = (r[bags_idx] or "").replace(",", "").strip()
                    qty_raw  = (r[qty_idx]  or "").replace(",", "").strip()

                    try:
                        bags = int(bags_raw)
                    except:
                        bags = bags_raw

                    try:
                        qty = int(qty_raw)
                    except:
                        qty = qty_raw

                    rows.append(
                        {
                            "Customer": customer,
                            "Crop": crop,
                            "Bags": bags,
                            "Quantity_kg": qty,
                        }
                    )

    return pd.DataFrame(rows)

if uploaded:
    df = parse_gatepass_pdf(uploaded.read())
    if df.empty:
        st.error(
            "Could not detect customer/crop table in this PDF. "
            "Try another gatepass or we need to adjust header detection."
        )
    else:
        st.success("Gatepass read successfully ✅")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "gatepass_summary.csv")
