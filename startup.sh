#!/bin/bash
# Azure App Service startup script

echo "Starting DeepTrace on Azure..."

# Use Oryx-built virtual environment if available, otherwise create one
if [ -d "/home/site/wwwroot/antenv" ]; then
    echo "Using existing virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
elif [ -d "antenv" ]; then
    echo "Using local virtual environment..."
    source antenv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv antenv
    source antenv/bin/activate
    pip install --upgrade pip
    pip install -r requirements-web.txt
fi

# Ensure src is importable
export PYTHONPATH="/home/site/wwwroot/src:$PYTHONPATH"

# Run with Gunicorn on the port Azure expects (default 8000)
gunicorn wsgi:app --bind=0.0.0.0:8000 --workers=2 --timeout=120
