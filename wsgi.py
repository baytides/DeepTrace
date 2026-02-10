"""WSGI entry point for Azure App Service deployment."""

from deeptrace.dashboard import create_app

# Create the Flask app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run()
