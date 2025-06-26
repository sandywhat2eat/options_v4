#!/usr/bin/env python3
"""
Test script for smart expiry logic
Tests the 20th date cutoff functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from options_v4_executor import OptionsV4Executor

def test_smart_expiry_logic():
    """Test the smart expiry logic with various dates"""
    
    print("=" * 60)
    print("SMART EXPIRY LOGIC TEST")
    print("=" * 60)
    
    # Initialize executor
    try:
        executor = OptionsV4Executor()
        print("✅ Executor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize executor: {e}")
        return
    
    # Test scenarios
    test_dates = [
        # Current scenario (June 26, 2025 - expiry day, > 20th)
        datetime(2025, 6, 26),
        
        # Early in month (June 15, 2025 - < 20th)
        datetime(2025, 6, 15),
        
        # Exactly on cutoff (June 20, 2025)
        datetime(2025, 6, 20),
        
        # Late in month (June 25, 2025 - > 20th)
        datetime(2025, 6, 25),
        
        # Early July (July 5, 2025 - < 20th)
        datetime(2025, 7, 5),
        
        # Late July (July 25, 2025 - > 20th)
        datetime(2025, 7, 25),
    ]
    
    print("\nTesting different dates with cutoff_day=20:")
    print("-" * 60)
    
    for test_date in test_dates:
        try:
            # Test legacy logic
            legacy_expiry = executor.get_smart_expiry_date(test_date, cutoff_day=20, use_legacy_logic=True)
            
            # Test smart logic
            smart_expiry = executor.get_smart_expiry_date(test_date, cutoff_day=20, use_legacy_logic=False)
            
            day_status = "≤20" if test_date.day <= 20 else ">20"
            
            print(f"Date: {test_date.strftime('%Y-%m-%d')} (Day {test_date.day}, {day_status})")
            print(f"  Legacy Logic: {legacy_expiry.strftime('%Y-%m-%d') if legacy_expiry else 'None'}")
            print(f"  Smart Logic:  {smart_expiry.strftime('%Y-%m-%d') if smart_expiry else 'None'}")
            
            # Check if there's a difference
            if legacy_expiry and smart_expiry:
                if legacy_expiry.date() != smart_expiry.date():
                    print(f"  📊 DIFFERENCE: Smart logic selects different expiry!")
                else:
                    print(f"  ✅ Same result with both logics")
            print()
            
        except Exception as e:
            print(f"  ❌ Error testing {test_date}: {e}")
            print()
    
    # Test current behavior for strategy 3359
    print("=" * 60)
    print("STRATEGY 3359 EXPIRY ANALYSIS")
    print("=" * 60)
    
    current_date = datetime.now()
    print(f"Current Date: {current_date.strftime('%Y-%m-%d %H:%M:%S')} (Day {current_date.day})")
    
    try:
        # What expiry would be selected with current logic?
        current_expiry = executor.get_smart_expiry_date(current_date, cutoff_day=20, use_legacy_logic=False)
        legacy_expiry = executor.get_smart_expiry_date(current_date, cutoff_day=20, use_legacy_logic=True)
        
        print(f"\nFor strategy execution TODAY:")
        print(f"  Legacy expiry:  {legacy_expiry.strftime('%Y-%m-%d') if legacy_expiry else 'None'}")
        print(f"  Smart expiry:   {current_expiry.strftime('%Y-%m-%d') if current_expiry else 'None'}")
        
        if current_date.day <= 20:
            print(f"  📊 Since today is day {current_date.day} (≤20), smart logic tries current month first")
        else:
            print(f"  📊 Since today is day {current_date.day} (>20), smart logic uses next month")
            
        print(f"\nWhen executing: python options_v4_executor.py --strategy-id 3359")
        print(f"Expected expiry: {current_expiry.strftime('%Y-%m-%d') if current_expiry else 'None'}")
        
    except Exception as e:
        print(f"❌ Error analyzing current scenario: {e}")

if __name__ == "__main__":
    test_smart_expiry_logic()