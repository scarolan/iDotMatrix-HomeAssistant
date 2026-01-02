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
mkdir -p config/www

# Symlink the card to www for /local/ access
# Using copy to avoid permission/symlink serving issues
rm -f "$(pwd)/config/www/idotmatrix-card.js"
cp -f "$(pwd)/custom_components/idotmatrix/www/idotmatrix-card.js" "$(pwd)/config/www/idotmatrix-card.js"

# Check if integration is linked
if [ ! -L "config/custom_components/idotmatrix" ]; then
    echo "Linking integration..."
    mkdir -p config/custom_components
    rm -rf config/custom_components/idotmatrix
    # Use absolute path for safety
    ln -sf "$(pwd)/custom_components/idotmatrix" "$(pwd)/config/custom_components/idotmatrix"
fi

# Overwrite configuration.yaml to ensure valid YAML (no duplicate keys) and correct settings
echo "Generating configuration.yaml..."
cat > config/configuration.yaml <<EOF
default_config:

http:
  server_port: 8128
  cors_allowed_origins:
    - all

frontend:
  themes: !include_dir_merge_named themes
  extra_module_url:
    - /local/idotmatrix-card.js
EOF

echo "Starting Home Assistant..."
hass -c config
