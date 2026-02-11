import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Eeki Gatepass Reader", page_icon="🚚", layout="wide")
st.title("Eeki Gatepass Reader (Customer / Crop / Bags / Qty)")

uploaded = st.file_uploader("Upload Gatepass (PDF)", type=["pdf"])

# ---------- Helpers ----------

def extract_customer_from_text(text: str) -> str:
    """Get customer name from the 'To:' line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if line.startswith("To:"):
            # e.g. "To: PJTJ TECHNOLOGIES PVT LTD"
            return line.replace("To:", "").strip()
    return ""

def find_table_indices(header: list) -> tuple | None:
    """
    Find indices for Crop, Bags, Quantity columns
    using flexible keyword matching.
    """
    lower = [(h or "").lower() for h in header]

    crop_idx = next((i for i, h in enumerate(lower) if "crop" in h), None)
    bags_idx = next((i for i, h in enumerate(lower) if "bag" in h), None)
    qty_idx  = next(
        (i for i, h in enumerate(lower) if "qty" in h or "quantity" in h),
        None,
    )

    if crop_idx is None or bags_idx is None or qty_idx is None:
        return None
    return crop_idx, bags_idx, qty_idx

def parse_gatepass_pdf(file_bytes: bytes) -> pd.DataFrame:
    """Return dataframe with Customer, Crop, Bags, Quantity_kg from a gatepass PDF."""
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
                idxs = find_table_indices(header)
                if idxs is None:
                    continue

                crop_idx, bags_idx, qty_idx = idxs

                for r in tbl[1:]:
                    if not r:
                        continue
                    crop = (r[crop_idx] or "").strip()
                    if crop == "" or crop.lower() == "total":
                        continue

                    bags_raw = (r[bags_idx] or "").replace(",", "").strip()
                    qty_raw  = (r[qty_idx]  or "").replace(",", "").strip()

                    # Try to convert to int, otherwise keep text
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

# ---------- UI logic ----------

if uploaded:
    df = parse_gatepass_pdf(uploaded.read())
    if df.empty:
        st.error(
            "Could not detect customer/crop table in this PDF. "
            "Check if the PDF has a crop/bags/quantity table."
        )
    else:
        st.success("Gatepass read successfully ✅")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "gatepass_summary.csv")
