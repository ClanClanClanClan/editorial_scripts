#!/usr/bin/env python3
"""
Simple SICON test without complex credential manager
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment for test
os.environ['ORCID_EMAIL'] = input("Enter your ORCID email: ")
os.environ['ORCID_PASSWORD'] = input("Enter your ORCID password: ")

async def simple_sicon_test():
    """Simple test of SICON extraction"""
    
    print("\n🔬 Simple SICON Test")
    print("=" * 30)
    
    try:
        # Import after setting environment
        from unified_system.extractors.siam.sicon import SICONExtractor
        
        extractor = SICONExtractor()
        
        # Get credentials from environment
        username = os.environ.get('ORCID_EMAIL')
        password = os.environ.get('ORCID_PASSWORD')
        
        if not username or not password:
            print("❌ No credentials provided")
            return
        
        print(f"✅ Using credentials: {username[:3]}***")
        
        # Run extraction
        result = await extractor.extract(
            username=username,
            password=password,
            headless=False
        )
        
        if result['success']:
            print(f"\n✅ Extraction successful!")
            print(f"📊 Found {len(result['manuscripts'])} manuscripts")
            
            # Show results
            for ms in result['manuscripts']:
                print(f"\n📄 {ms['id']}: {ms['title'][:60]}...")
                print(f"   Associate Editor: {ms.get('associate_editor', 'N/A')}")
                print(f"   Referees: {len(ms.get('referees', []))}")
                
                for ref in ms.get('referees', []):
                    email_display = ref.get('email', 'No email')
                    if email_display and len(email_display) > 10:
                        email_display = email_display[:10] + "..."
                    print(f"     - {ref['name']} ({email_display}) - {ref.get('status', 'Unknown')}")
        else:
            print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            await extractor._cleanup()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(simple_sicon_test())