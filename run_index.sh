#!/bin/bash

# INDEX-ONLY Options V4 Analysis Runner
# Wrapper script to run INDEX options analysis with proper environment

echo "🚀 Starting INDEX-ONLY Options V4 Analysis..."
echo "================================================"

# Activate virtual environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Set working directory
cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4

# Create logs directory if it doesn't exist
mkdir -p logs

# Run INDEX-ONLY analysis
echo "📊 Running INDEX-ONLY portfolio analysis..."
python3 main_index.py

echo ""
echo "✅ INDEX-ONLY analysis complete!"
echo "📁 Check results/ folder for output files"
echo "📋 Check logs/ folder for detailed logs"