#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line as needed for your project
pip install -r requirements.txt

# Convert static asset building
python -m pip install --upgrade pip