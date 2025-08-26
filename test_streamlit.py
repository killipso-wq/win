#!/usr/bin/env python3
"""Test script to verify streamlit installation"""

try:
    import streamlit as st
    print(f"✅ Streamlit imported successfully! Version: {st.__version__}")
    
    # Test basic streamlit functionality
    st.set_page_config(page_title="Test", page_icon="🏈")
    st.write("Streamlit is working!")
    
except ImportError as e:
    print(f"❌ Failed to import streamlit: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Streamlit error: {e}")
    exit(1)

print("✅ All tests passed!")