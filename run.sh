#!/usr/bin/env bash
# One command to set up and run SiteWatch on your laptop.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -q -r requirements.txt
python -m playwright install chromium

# Load alert settings from .env if you made one
if [ -f .env ]; then
  set -a; source .env; set +a
fi

python sitewatch.py
echo "Open site/index.html in your browser to see the report."
