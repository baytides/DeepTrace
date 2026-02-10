#!/usr/bin/env python3
"""
DeepTrace Launcher - Double-click to start!

This script launches the DeepTrace dashboard automatically.
No terminal commands needed - just double-click this file.
"""

import webbrowser
from pathlib import Path
from time import sleep

from deeptrace.dashboard import create_app


def main():
    """Launch the DeepTrace dashboard."""
    print("=" * 60)
    print("  DeepTrace - Cold Case Investigation Platform")
    print("=" * 60)
    print()
    print("Starting dashboard server...")
    print()

    # Create app without specific case (will show case selector)
    app = create_app()

    port = 8080
    url = f"http://localhost:{port}"

    print(f"Dashboard will open at: {url}")
    print()
    print("✓ Server is starting...")

    # Open browser after a short delay
    def open_browser():
        sleep(1.5)
        print("✓ Opening browser...")
        webbrowser.open(url)

    from threading import Thread
    Thread(target=open_browser, daemon=True).start()

    print()
    print("=" * 60)
    print("  Dashboard is now running!")
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Run the Flask app
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
