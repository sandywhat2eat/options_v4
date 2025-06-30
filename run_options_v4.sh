#!/bin/bash

# Options V4 Runner Script
# This script activates the virtual environment and runs the Options V4 system

echo "🚀 Starting Options V4 Trading System..."

# Activate virtual environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Change to project directory
cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4

# Run the main script with all arguments passed through
python3 main.py "$@"

echo "✅ Options V4 execution completed"