#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Testing streamlit installation..."
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"

echo "Starting Streamlit app..."
streamlit run app.py --server.port $PORT --server.address 0.0.0.0