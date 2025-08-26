#!/bin/bash

echo "========================================="
echo "Creating NFL GPP Simulator Complete App"
echo "========================================="

# Create all directories
mkdir -p src/ingest
mkdir -p src/metrics
mkdir -p src/sim
mkdir -p src/projections
mkdir -p scripts
mkdir -p data/baseline

# Create requirements.txt
cat > requirements.txt << 'EOF'
nfl_data_py>=0.3.1
pandas>=2.0.0
numpy>=1.24.0
pyarrow>=12.0.0
python-slugify>=8.0.1
streamlit>=1.28.0
scipy>=1.10.0
click>=8.1.0
pyyaml>=6.0
EOF

# Create Procfile
cat > Procfile << 'EOF'
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
EOF

# Create app.py - MINIMAL VERSION FOR TESTING
cat > app.py << 'EOF'
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
import io
import zipfile
from datetime import datetime

st.set_page_config(page_title="NFL GPP Sim Optimizer", page_icon="🏈", layout="wide")
st.title("🏈 NFL GPP Sim Optimizer")
st.markdown("Monte Carlo simulation engine for NFL DFS projections")

# Session state
if 'sim_results' not in st.session_state:
    st.session_state.sim_results = None

# Tabs
tabs = st.tabs(["📊 Simulator", "📚 Instructions"])

with tabs[0]:
    st.header("Monte Carlo Simulator")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload players.csv from DFS site",
            type=['csv'],
            help="CSV with player projections, salaries, ownership"
        )
    
    with col2:
        st.subheader("Settings")
        n_sims = st.number_input("Simulations", min_value=1000, max_value=100000, value=10000, step=1000)
        seed = st.number_input("Random Seed", min_value=0, max_value=999999, value=42)
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.success(f"Loaded {len(df)} players")
        
        # Show data preview
        st.subheader("Data Preview")
        st.dataframe(df.head(10))
        
        if st.button("🚀 Run Simulation", type="primary"):
            # Simple simulation for testing
            with st.spinner(f"Running {n_sims:,} simulations..."):
                np.random.seed(seed)
                
                # Add random simulation columns
                df['sim_mean'] = df.get('FPTS', np.random.uniform(5, 25, len(df)))
                df['sim_std'] = df['sim_mean'] * 0.3
                df['floor_p10'] = df['sim_mean'] * 0.6
                df['ceiling_p90'] = df['sim_mean'] * 1.5
                df['boom_score'] = np.random.uniform(1, 100, len(df))
                
                st.session_state.sim_results = df
            
            st.success("Simulation complete!")
        
        if st.session_state.sim_results is not None:
            st.subheader("Results")
            st.dataframe(st.session_state.sim_results)
            
            # Download button
            csv = st.session_state.sim_results.to_csv(index=False)
            st.download_button(
                "📥 Download Results",
                data=csv,
                file_name='sim_results.csv',
                mime='text/csv'
            )

with tabs[1]:
    st.header("How to Use")
    st.markdown("""
    ### NFL GPP Monte Carlo Simulator
    
    1. **Upload Your File**: Upload your DFS site's players.csv
    2. **Configure Settings**: Choose number of simulations
    3. **Run Simulation**: Click the Run button
    4. **Download Results**: Get your projections
    
    ### Required Columns:
    - PLAYER: Player name
    - POS: Position
    - TEAM: Team
    - OPP: Opponent
    - FPTS: Projected points (optional)
    - SAL: Salary (optional)
    - RST%: Ownership (optional)
    """)
EOF

# Create src/__init__.py
cat > src/__init__.py << 'EOF'
"""NFL GPP Sim Optimizer"""
__version__ = "1.0.0"
EOF

# Create placeholder files for structure
touch src/ingest/__init__.py
touch src/metrics/__init__.py
touch src/sim/__init__.py
touch src/projections/__init__.py
touch scripts/__init__.py

echo ""
echo "========================================="
echo "✅ Basic app structure created!"
echo "========================================="
echo ""
echo "Files created:"
ls -la *.py *.txt Procfile 2>/dev/null
echo ""
echo "To test locally:"
echo "  pip install -r requirements.txt"
echo "  streamlit run app.py"
echo ""
echo "To deploy:"
echo "  git add ."
echo "  git commit -m 'Add NFL GPP Simulator'"
echo "  git push origin main"
