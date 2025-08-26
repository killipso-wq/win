#!/usr/bin/env python3
"""
Test imports for deployment
"""

def test_imports():
    """Test all required imports"""
    try:
        import streamlit as st
        print("✅ streamlit imported successfully")
        
        import pandas as pd
        print("✅ pandas imported successfully")
        
        import numpy as np
        print("✅ numpy imported successfully")
        
        import nfl_data_py as nfl
        print("✅ nfl_data_py imported successfully")
        
        import scipy
        print("✅ scipy imported successfully")
        
        import sklearn
        print("✅ scikit-learn imported successfully")
        
        from slugify import slugify
        print("✅ python-slugify imported successfully")
        
        print("\n🎉 All imports successful! System ready for deployment.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    test_imports()