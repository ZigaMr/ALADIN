#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing Python..."
    sudo apt-get update
    sudo apt-get install python3 -y
fi

# Create and activate a virtual environment
echo "Creating and activating a virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install required packages from requirements.txt
echo "Installing required packages..."
pip install -r requirements.txt

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo "MySQL not found. Installing MySQL..."
    sudo apt-get install mysql-server -y
fi

(crontab -l 2>/dev/null; echo "0 * * * * ./venv/bin/python ./main.py") | crontab -

echo "Setup completed successfully."
