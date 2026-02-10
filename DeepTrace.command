#!/bin/bash
# DeepTrace Launcher for macOS
# Double-click to launch DeepTrace

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment if it exists
if [ -d "$DIR/.venv" ]; then
    source "$DIR/.venv/bin/activate"
fi

# Run the launcher
python3 "$DIR/launch_deeptrace.py"
