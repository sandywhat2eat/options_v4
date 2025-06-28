#!/usr/bin/env python3
"""
Main Portfolio Allocator - Hybrid Engine
Simple entry point for the hybrid portfolio allocation system
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the hybrid portfolio allocator"""
    
    # Default capital amount
    capital = 1500000  # ₹15 lakh
    
    # Check if user provided capital amount
    if len(sys.argv) > 1:
        try:
            capital = float(sys.argv[1])
        except ValueError:
            print("❌ Invalid capital amount. Using default ₹15,00,000")
    
    print("=" * 80)
    print("🚀 OPTIONS PORTFOLIO ALLOCATOR")
    print("   Hybrid Tier + Industry Allocation Engine")
    print("=" * 80)
    print(f"💰 Capital: ₹{capital:,.0f}")
    print("🎯 Target: 4% monthly return")
    print("⚡ Engine: Hybrid (Tier + Industry + LONG/SHORT)")
    print("=" * 80)
    
    # Run the hybrid allocator
    try:
        result = subprocess.run([
            sys.executable, 
            "portfolio_allocation/core/hybrid_runner.py", 
            "--capital", 
            str(int(capital))
        ], check=True)
        
        print("\n✅ Portfolio allocation completed successfully!")
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running allocator: {e}")
        return 1
    except FileNotFoundError:
        print("❌ Hybrid allocator script not found!")
        print("   Make sure you're in the correct directory")
        return 1

if __name__ == "__main__":
    exit(main())