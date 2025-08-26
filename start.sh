#!/bin/bash
set -e

echo "=== NFL GPP Simulator Deployment ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Testing streamlit installation..."
python test_streamlit.py

echo "Starting Streamlit app..."
python -m streamlit run app.py --server.port $PORT --server.address 0.0.0.0