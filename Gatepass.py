import streamlit as st
import os

st.title("System Debugger")

# 1. Check current directory
st.write("### Current Directory Content:")
st.code(os.listdir("."))

# 2. Check if requirements.txt exists and read it
if os.path.exists("requirements.txt"):
    st.success("requirements.txt found!")
    with open("requirements.txt", "r") as f:
        st.code(f.read())
else:
    st.error("requirements.txt NOT found in the root directory!")

# 3. Check Python version
import sys
st.write(f"Python Version: {sys.version}")
