import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="Gatepass Reader", page_icon="🚚", layout="wide")

st.markdown("""
    ## 🚚 Eeki Gatepass Reader
    Upload your PDF gatepass to extract Customer, Crop, Bags, and Quantity data.
""")

def extract_customer_from_text(text: str) -> str:
    """Extracts the customer name after the 'To:' label."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if line.upper().startswith("TO:"):
            # Check if name is on the same line (e.g., "To: Customer Name")
            customer = line[3:].strip()
            # If the same line is empty, the name is likely on the very next line
            if not customer and i + 1 < len(lines):
                customer = lines[i+1]
            return customer
    return "Not Found"

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
                
                # Clean header names: remove newlines and extra spaces
                header = [str(c).replace('\n', ' ').strip() if c else "" for c in tbl[0]]

                # Logic to identify the specific table by checking for key column headers
                if ("Crop Name" in header and 
                    "Total Number of Bags/Boxes" in header and 
                    "Total Quantity (kgs)" in header):

                    crop_idx = header.index("Crop Name")
                    bags_idx = header.index("Total Number of Bags/Boxes")
                    qty_idx = header.index("Total Quantity (kgs)")

                    for r in tbl[1:]:
                        if not any(r):
                            continue
                        
                        crop = (r[crop_idx] or "").strip()
                        
                        # Skip footer rows or empty rows
                        if not crop or crop.lower() in ["total", "sub total"]:
                            continue

                        # Clean numeric strings (remove commas)
                        bags_raw = str(r[bags_idx] or "0").replace(",", "").strip()
                        qty_raw = str(r[qty_idx] or "0").replace(",", "").strip()

                        # Convert to numeric, keep as string if conversion fails
                        try:
                            bags = int(float(bags_raw))
                        except ValueError:
                            bags = bags_raw
                            
                        try:
                            qty = float(qty_raw)
                        except ValueError:
                            qty = qty_raw

                        rows.append({
                            "Customer": customer,
                            "Crop": crop,
                            "Bags": bags,
                            "Quantity_kg": qty,
                        })
    
    return pd.DataFrame(rows)

# --- UI Layout ---
uploaded = st.file_uploader("Upload Gatepass (PDF)", type=["pdf"])

if uploaded:
    with st.spinner("Processing PDF..."):
        try:
            df = parse_gatepass_pdf(uploaded.read())
            
            if df.empty:
                st.warning("⚠️ No data found. Ensure the PDF contains the standard Crop Table.")
            else:
                st.success("Gatepass read successfully ✅")
                
                # Display Summary Metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Items", len(df))
                col2.metric("Total Bags", f"{df['Bags'].sum() if isinstance(df['Bags'].iloc[0], (int, float)) else 'N/A'}")
                col3.metric("Total Qty (kg)", f"{df['Quantity_kg'].sum() if isinstance(df['Quantity_kg'].iloc[0], (int, float)) else 'N/A'}")

                st.divider()
                st.dataframe(df, use_container_width=True)

                # Download Options
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"gatepass_{df['Customer'].iloc[0] if not df.empty else 'export'}.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"An error occurred: {e}")
