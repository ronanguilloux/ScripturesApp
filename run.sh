#!/bin/bash

# Define the virtual environment directory
VENV_DIR=".venv"

# Check if the virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
else
    # Activate the existing virtual environment
    source "$VENV_DIR/bin/activate"
fi

# Run the main script with all passed arguments
python3 main.py "$@"
