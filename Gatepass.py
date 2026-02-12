import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Eeki Gatepass Reader", page_icon="🚚", layout="wide")
st.title("Eeki Gatepass Reader (text based)")

uploaded = st.file_uploader("Upload Gatepass (PDF)", type=["pdf"])


def extract_customer(text: str) -> str:
    # Prefer line starting with 'To:'
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("To:"):
            return line.replace("To:", "").strip()
    # Fallback: line containing Fambo / Zomato / Kiranakart etc.
    for line in text.splitlines():
        if "Fambo" in line or "Zomato" in line or "Kiranakart" in line:
            return line.strip()
    return ""


def parse_gatepass_from_text(text: str, default_customer: str = "") -> pd.DataFrame:
    rows = []
    customer = extract_customer(text) or default_customer or "Unknown"

    # Normalize spaces
    clean = re.sub(r"[ \t]+", " ", text)
    lines = [l.strip() for l in clean.splitlines() if l.strip()]

    # After header "Crop Name ... Total Quantity (kgs)" we expect rows:
    # e.g. "Red Tomato (Oval) 200 4000"
    in_main_table = False
    for line in lines:
        if (
            "Crop Name" in line
            and "Total Number of Bags/Boxes" in line
            and "Total Quantity (kgs)" in line
        ):
            in_main_table = True
            continue

        if in_main_table:
            # Stop when reaching 'Loose Bags/Boxes' or 'For Buyer'
            if line.startswith("Loose Bags/Boxes") or line.startswith("For Buyer"):
                break

            # Skip 'Total' row
            if line.lower().startswith("total"):
                continue

            parts = line.split()
            if len(parts) >= 3:
                try:
                    bags = int(parts[-2].replace(",", ""))
                    qty = int(parts[-1].replace(",", ""))
                    crop = " ".join(parts[:-2])
                    if crop:
                        rows.append(
                            {
                                "Customer": customer,
                                "Crop": crop,
                                "Bags": bags,
                                "Quantity_kg": qty,
                            }
                        )
                except ValueError:
                    continue

    return pd.DataFrame(rows)


if uploaded:
    all_pages = []

    with pdfplumber.open(uploaded) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            df_page = parse_gatepass_from_text(text, default_customer=f"Page {page_idx}")
            if not df_page.empty:
                all_pages.append(df_page)

    if all_pages:
        df = pd.concat(all_pages, ignore_index=True)
        st.success("Gatepass read successfully ✅")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "gatepass_summary.csv")
    else:
        st.error("❌ No crop rows detected from text in this PDF.")
