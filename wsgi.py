"""
WSGI entry point for web deployment.

This file is used by web servers (Gunicorn, uWSGI, etc.) to serve DeepTrace.
"""

from deeptrace.dashboard import create_app

# Create the Flask app for web deployment
# No case specified = multi-case mode with case selector
app = create_app()

if __name__ == "__main__":
    # For development server
    app.run(host="0.0.0.0", port=8080, debug=True)
