#!/usr/bin/env python3
"""Minimal test of SICON extraction"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv('.env.production')

# Add path
sys.path.append(str(Path(__file__).parent / 'editorial_scripts_ultimate'))

async def test_sicon():
    """Test SICON extraction"""
    print("🧪 Testing SICON Extraction")
    print("=" * 50)
    
    # Check credentials
    email = os.getenv('ORCID_EMAIL')
    password = os.getenv('ORCID_PASSWORD')
    
    if not email or not password:
        print("❌ Missing credentials!")
        return
    
    print(f"✅ Credentials loaded: {email}")
    
    try:
        # Import extractor
        from extractors.siam.optimized_sicon_extractor import OptimizedSICONExtractor
        print("✅ Imports successful")
        
        # Create extractor
        extractor = OptimizedSICONExtractor()
        print("✅ Extractor created")
        
        # Run extraction with visible browser
        print("\n🚀 Starting extraction (headed mode)...")
        result = await extractor.extract(headless=False, use_cache=False)
        
        print(f"\n📊 Results:")
        print(f"  Manuscripts: {len(result.manuscripts)}")
        print(f"  Referees: {len(result.referees)}")
        print(f"  Success: {result.success}")
        
        if result.errors:
            print(f"\n❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sicon())