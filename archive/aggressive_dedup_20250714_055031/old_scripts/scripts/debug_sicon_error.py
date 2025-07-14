#!/usr/bin/env python3
"""Debug SICON error"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("1. Testing imports...")
    from src.infrastructure.scrapers.stealth_manager import StealthManager, StealthConfig
    print("   ✓ Imports successful")
    
    print("\n2. Testing StealthConfig creation...")
    config = StealthConfig(
        randomize_viewport=True,
        randomize_user_agent=True,
        inject_webdriver_stealth=True,
        randomize_timing=True,
        block_tracking=True,
        base_delay_range=(2, 5),
        typing_delay_range=(0.05, 0.15)
    )
    print(f"   ✓ StealthConfig created: {type(config)}")
    
    print("\n3. Testing StealthManager creation...")
    manager = StealthManager(config)
    print(f"   ✓ StealthManager created: {type(manager)}")
    
    print("\n4. Testing SIAM scraper import...")
    from src.infrastructure.scrapers.siam_scraper import SIAMScraper
    print("   ✓ SIAMScraper imported")
    
    print("\n5. Testing SICON scraper creation...")
    scraper = SIAMScraper('SICON')
    print(f"   ✓ SICON scraper created: {type(scraper)}")
    
    print("\n✅ All tests passed! No 'dict' object error found.")
    
except Exception as e:
    print(f"\n❌ Error occurred: {e}")
    import traceback
    traceback.print_exc()
    
    # Check what type of error it is
    if "'dict' object is not callable" in str(e):
        print("\n🔍 Found the 'dict' object error!")
        print("This usually means something is being called as a function when it's actually a dictionary.")