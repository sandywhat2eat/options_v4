#!/usr/bin/env python3
"""
Monitoring System Launcher
Ensures correct working directory and provides easy access to monitoring systems
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

def run_script(script_path, args=None):
    """Run a script with correct working directory and path setup"""
    if args is None:
        args = []
    
    # Change to project root
    os.chdir(PROJECT_ROOT)
    
    # Ensure project root is in Python path
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    # Build command
    cmd = [sys.executable, script_path] + args
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
        sys.exit(1)

def main():
    """Main launcher function"""
    if len(sys.argv) < 2:
        print("""
🔍 Options V4 Monitoring System Launcher

Usage: python run_monitoring.py <system> [options]

Available Systems:
  realtime     - Real-time WebSocket monitoring (recommended)
  legacy       - Legacy polling-based monitoring  
  interactive  - Interactive monitoring dashboard

Examples:
  python run_monitoring.py realtime --help
  python run_monitoring.py realtime --execute
  python run_monitoring.py legacy --execute --interval 5
  python run_monitoring.py interactive --continuous

Note: Run from anywhere - this script handles paths automatically!
        """)
        sys.exit(1)
    
    system = sys.argv[1].lower()
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if system == "realtime":
        script_path = "trade_monitoring/realtime/realtime_automated_monitor.py"
    elif system == "legacy":
        script_path = "trade_monitoring/legacy/automated_monitor.py"
    elif system == "interactive":
        script_path = "trade_monitoring/legacy/monitor.py"
    else:
        print(f"❌ Unknown system: {system}")
        print("Available systems: realtime, legacy, interactive")
        sys.exit(1)
    
    print(f"🚀 Launching {system} monitoring system...")
    print(f"📁 Working directory: {PROJECT_ROOT}")
    print(f"📄 Script: {script_path}")
    print("-" * 50)
    
    run_script(script_path, args)

if __name__ == "__main__":
    main()