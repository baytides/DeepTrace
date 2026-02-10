#!/bin/bash
# Azure App Service startup script

echo "Starting DeepTrace on Azure..."

# Ensure virtual environment
python -m venv antenv
source antenv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-web.txt

# Run with Gunicorn
gunicorn wsgi:app --bind=0.0.0.0:8000 --workers=4 --timeout=600
