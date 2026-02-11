import streamlit as st
import sys

# --- FORCED DEPENDENCY CHECK ---
try:
    import pdfplumber
except ImportError:
    st.error("### ❌ Dependency Error")
    st.info("The package **'pdfplumber'** is not installed yet. Streamlit Cloud is likely still building your environment.")
    st.markdown("Please wait 1-2 minutes and **refresh the page**. If it still fails, ensure your `requirements.txt` is in the root folder.")
    st.stop()

import pandas as pd
from io import BytesIO

# --- APP CONFIG ---
st.set_page_config(page_title="Gatepass Reader", page_icon="🚚", layout="wide")

st.title("🚚 Eeki Gatepass Reader")
st.subheader("Extract Data from PDF Gatepasses")

def extract_customer(text):
    for line in text.split('\n'):
        if "To:" in line:
            return line.replace("To:", "").strip()
    return "Unknown Customer"

def process_pdf(file):
    all_data = []
    with pdfplumber.open(BytesIO(file)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            customer = extract_customer(text)
            
            tables = page.extract_tables()
            for table in tables:
                df_tmp = pd.DataFrame(table)
                # Check if this is the target table based on column headers
                if any("Crop Name" in str(cell) for cell in table[0]):
                    # Set the first row as header
                    df_tmp.columns = [str(c).replace('\n', ' ') for c in df_tmp.iloc[0]]
                    df_tmp = df_tmp[1:] # Remove header row from data
                    
                    for _, row in df_tmp.iterrows():
                        crop = str(row.get("Crop Name", "")).strip()
                        if not crop or "Total" in crop: continue
                        
                        all_data.append({
                            "Customer": customer,
                            "Crop": crop,
                            "Bags": row.get("Total Number of Bags/Boxes", "0"),
                            "Weight (kg)": row.get("Total Quantity (kgs)", "0")
                        })
    return pd.DataFrame(all_data)

uploaded_file = st.file_uploader("Choose a Gatepass PDF", type="pdf")

if uploaded_file:
    with st.spinner('Parsing PDF...'):
        results_df = process_pdf(uploaded_file.read())
        
        if not results_df.empty:
            st.success("Data Extracted!")
            st.dataframe(results_df, use_container_width=True)
            
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download as CSV", csv, "gatepass_data.csv", "text/csv")
        else:
            st.warning("No matching table found in the PDF.")
