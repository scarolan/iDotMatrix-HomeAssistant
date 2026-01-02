#!/bin/bash
set -e  # Fail on error

if [ ! -d "ha_venv" ]; then
    echo "Creating Home Assistant venv using Python 3.12..."
    python3.12 -m venv ha_venv
    source ha_venv/bin/activate
    
    echo "Installing Home Assistant..."
    pip install homeassistant colorlog
else
    source ha_venv/bin/activate
fi

# Ensure config directory exists
mkdir -p config

# Check if integration is linked
if [ ! -L "config/custom_components/idotmatrix" ]; then
    echo "Linking integration..."
    mkdir -p config/custom_components
    rm -rf config/custom_components/idotmatrix
    # Use absolute path for safety
    ln -sf "$(pwd)/custom_components/idotmatrix" "$(pwd)/config/custom_components/idotmatrix"
fi

echo "Starting Home Assistant..."
hass -c config
