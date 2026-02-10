"""WSGI entry point for Azure App Service deployment."""

import sys
from pathlib import Path

# Add src directory to Python path for package imports
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from deeptrace.dashboard import create_app

# Create the Flask app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run()
