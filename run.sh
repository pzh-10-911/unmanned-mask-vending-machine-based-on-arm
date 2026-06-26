#!/bin/bash
# run.sh — Mask Vending Machine startup script
# Usage: bash run.sh

echo "Starting Mask Vending Machine..."

# Activate virtualenv if exists
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
pip install -r requirements.txt -q

# Start Flask server
echo "Server starting at http://0.0.0.0:5000"
python app.py
