#!/usr/bin/env python3
"""Test SICON extraction with fixes"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'unified_system'))

from unified_system.extractors.siam.sicon import SICONExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_sicon_extraction():
    """Test SICON extraction with fixed parsing"""
    
    print("\n🔬 Testing SICON extraction with fixes...\n")
    
    extractor = SICONExtractor()
    
    try:
        # Run extraction - need to get credentials first
        from src.core.credential_manager import get_credentials
        creds = get_credentials('SICON')
        
        if not creds:
            print("❌ No SICON/ORCID credentials found")
            print("Please set up 1Password or environment variables")
            return
        
        result = await extractor.extract(
            username=creds['username'],
            password=creds['password'],
            headless=False
        )
        
        if result['success']:
            print(f"\n✅ Extraction successful!")
            print(f"📊 Found {len(result['manuscripts'])} manuscripts\n")
            
            # Display detailed results
            for ms in result['manuscripts']:
                print(f"\n📄 Manuscript: {ms['id']}")
                print(f"   Title: {ms['title'][:80]}...")
                print(f"   Authors: {', '.join(ms.get('authors', []))}")
                print(f"   Associate Editor: {ms.get('associate_editor', 'N/A')}")
                print(f"   Status: {ms.get('status', 'N/A')}")
                print(f"   Referees: {len(ms.get('referees', []))}")
                
                for ref in ms.get('referees', []):
                    print(f"\n   👤 {ref['name']}")
                    print(f"      Email: {ref.get('email', 'NOT FOUND')}")
                    print(f"      Institution: {ref.get('institution', 'N/A')}")
                    print(f"      Status: {ref.get('status', 'N/A')}")
            
            # Save results
            output_dir = Path('output/sicon')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = output_dir / f'sicon_fixed_{timestamp}.json'
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result['data'], f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_file}")
            
        else:
            print(f"\n❌ Extraction failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await extractor.cleanup()

if __name__ == "__main__":
    asyncio.run(test_sicon_extraction())