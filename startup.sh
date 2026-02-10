#!/bin/bash
set -e
# Azure App Service startup script

echo "Starting DeepTrace on Azure..."

VENV_DIR="/home/site/wwwroot/antenv"

# Ensure a working virtual environment exists
# Check both that activate exists AND the python binary actually works
if [ -f "$VENV_DIR/bin/activate" ] && "$VENV_DIR/bin/python" --version >/dev/null 2>&1; then
    echo "Using existing virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "Creating fresh virtual environment (missing or broken)..."
    rm -rf "$VENV_DIR"
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
fi

# Always ensure dependencies are installed
echo "Installing/verifying dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r /home/site/wwwroot/requirements-web.txt

# Ensure src is importable
export PYTHONPATH="/home/site/wwwroot/src:$PYTHONPATH"

echo "Starting gunicorn..."
# Run with Gunicorn on the port Azure expects (default 8000)
exec gunicorn wsgi:app --bind=0.0.0.0:8000 --workers=2 --timeout=120
