#!/bin/bash

echo "Setting up A2J Legal Case Analysis environment..."

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Verify installation
echo "Verifying pandas installation..."
python -c "import pandas; print(f'Pandas version: {pandas.__version__}')"

echo "Setup complete! Use 'source venv/bin/activate' to activate the environment."
