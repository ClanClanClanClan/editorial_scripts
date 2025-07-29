#!/usr/bin/env python3
"""Run extraction using the WORKING editorial_assistant implementation"""

import os
import sys
import argparse
import yaml
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

# Load credentials from .env.production
from dotenv import load_dotenv
load_dotenv('.env.production')

# Load baseline targets
def _load_baseline_targets():
    """Load current baseline targets from config"""
    baseline_file = Path(__file__).parent / "config" / "baseline_targets_july_15_2025.yaml"
    try:
        with open(baseline_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠️  Baseline file not found: {baseline_file}")
        return None

def _validate_against_baseline(journal_code, manuscripts):
    """Validate extraction results against baseline targets"""
    baselines = _load_baseline_targets()
    if not baselines:
        return
        
    journal_upper = journal_code.upper()
    
    # Check if journal is in active list
    if journal_upper in baselines['journals']['active']:
        expected = baselines['journals']['active'][journal_upper]
        
        # Count actual results
        actual_manuscripts = len(manuscripts)
        actual_referees = 0
        for m in manuscripts:
            if hasattr(m, 'referees'):
                # Manuscript object format
                actual_referees += len(m.referees)
            elif isinstance(m, dict):
                # Dictionary format - handle different structures
                if 'declined_referees' in m or 'accepted_referees' in m:
                    # SICON format
                    declined = len(m.get('declined_referees', []))
                    accepted = len(m.get('accepted_referees', []))
                    actual_referees += declined + accepted
                elif 'Referees' in m:
                    # SIFIN format
                    actual_referees += len(m.get('Referees', []))
        
        print(f"\n📊 Baseline Validation for {journal_upper}:")
        print(f"   Expected manuscripts: {expected['manuscripts']}")
        print(f"   Actual manuscripts: {actual_manuscripts}")
        
        if 'referees' in expected:
            print(f"   Expected referees: {expected['referees']['total']}")
            print(f"   Actual referees: {actual_referees}")
            
            # Calculate success rates
            manuscript_rate = actual_manuscripts / expected['manuscripts'] if expected['manuscripts'] > 0 else 0
            referee_rate = actual_referees / expected['referees']['total'] if expected['referees']['total'] > 0 else 0
            
            validation_thresholds = baselines['validation']
            manuscript_pass = manuscript_rate >= validation_thresholds['manuscripts']
            referee_pass = referee_rate >= validation_thresholds['referees']
            
            print(f"   Manuscript success: {manuscript_rate:.1%} {'✅' if manuscript_pass else '❌'}")
            print(f"   Referee success: {referee_rate:.1%} {'✅' if referee_pass else '❌'}")
            
            if manuscript_pass and referee_pass:
                print(f"   🎉 {journal_upper} extraction meets baseline criteria!")
            else:
                print(f"   ⚠️  {journal_upper} extraction below baseline thresholds")
    
    elif journal_upper in baselines['journals']['inactive']:
        print(f"\n📊 {journal_upper} Validation:")
        print(f"   Status: Inactive journal (0 manuscripts expected)")
        if len(manuscripts) == 0:
            print(f"   ✅ Correctly shows no manuscripts")
        else:
            print(f"   🎉 Found {len(manuscripts)} manuscripts (more than expected!)")
    else:
        print(f"\n📊 {journal_upper}: No baseline data available")

def main():
    parser = argparse.ArgumentParser(description="Run journal extraction")
    parser.add_argument('journal', choices=['sicon', 'sifin', 'mf', 'mor', 'naco', 'fs', 'jota', 'mafe'], 
                       help='Journal to extract')
    parser.add_argument('--headless', action='store_true', default=False,
                       help='Run in headless mode')
    args = parser.parse_args()
    
    # Import after path setup
    from editorial_assistant.core.data_models import JournalConfig
    
    # Journal configurations
    journals = {
        'sicon': JournalConfig(
            code='SICON',
            name='SIAM Journal on Control and Optimization',
            url='https://sicon.siam.org',
            platform='siam',
            credentials={
                'username_env': 'ORCID_EMAIL',
                'password_env': 'ORCID_PASSWORD'
            }
        ),
        'sifin': JournalConfig(
            code='SIFIN',
            name='SIAM Journal on Financial Mathematics',
            url='https://sifin.siam.org',
            platform='siam',
            credentials={
                'username_env': 'ORCID_EMAIL',
                'password_env': 'ORCID_PASSWORD'
            }
        ),
        'mf': JournalConfig(
            code='MF',
            name='Mathematical Finance',
            url='https://mc.manuscriptcentral.com/mafi',
            platform='scholarone',
            credentials={
                'username_env': 'MF_EMAIL',
                'password_env': 'MF_PASSWORD'
            }
        ),
        'mor': JournalConfig(
            code='MOR',
            name='Mathematics of Operations Research',
            url='https://mc.manuscriptcentral.com/mathor',
            platform='scholarone',
            credentials={
                'username_env': 'MOR_EMAIL',
                'password_env': 'MOR_PASSWORD'
            }
        ),
        'naco': JournalConfig(
            code='NACO',
            name='North American Congress on Optimization',
            url='https://naco.siam.org',
            platform='siam',
            credentials={
                'username_env': 'ORCID_EMAIL',
                'password_env': 'ORCID_PASSWORD'
            }
        ),
        'fs': JournalConfig(
            code='FS',
            name='Finance and Stochastics',
            url='https://www.editorialmanager.com/fist',
            platform='editorial_manager',
            credentials={
                'username_env': 'FS_EMAIL',
                'password_env': 'FS_PASSWORD'
            }
        ),
        'jota': JournalConfig(
            code='JOTA',
            name='Journal of Optimization Theory and Applications',
            url='https://www.editorialmanager.com/jota',
            platform='editorial_manager',
            credentials={
                'username_env': 'JOTA_EMAIL',
                'password_env': 'JOTA_PASSWORD'
            }
        ),
        'mafe': JournalConfig(
            code='MAFE',
            name='Mathematics and Financial Economics',
            url='https://www.editorialmanager.com/mafe',
            platform='editorial_manager',
            credentials={
                'username_env': 'MAFE_EMAIL',
                'password_env': 'MAFE_PASSWORD'
            }
        )
    }
    
    journal_config = journals[args.journal]
    
    # Check credentials
    username_env = journal_config.credentials.get('username_env')
    password_env = journal_config.credentials.get('password_env')
    
    if not os.getenv(username_env) or not os.getenv(password_env):
        print(f"❌ Missing credentials for {journal_config.code}")
        print(f"   Please set {username_env} and {password_env}")
        return 1
    
    print(f"🚀 Extracting {journal_config.code}")
    print(f"   URL: {journal_config.url}")
    print(f"   User: {os.getenv(username_env)}")
    print()
    
    # Import and run extractor
    if args.journal == 'sicon':
        from editorial_assistant.extractors.sicon import SICONExtractor
        extractor_class = SICONExtractor
    elif args.journal == 'sifin':
        from editorial_assistant.extractors.sifin import SIFINExtractor
        extractor_class = SIFINExtractor
    elif args.journal == 'mf':
        from editorial_assistant.extractors.scholarone import ScholarOneExtractor
        extractor_class = ScholarOneExtractor
    elif args.journal == 'mor':
        from editorial_assistant.extractors.scholarone import ScholarOneExtractor
        extractor_class = ScholarOneExtractor
    elif args.journal == 'naco':
        from editorial_assistant.extractors.naco import NACOExtractor
        extractor_class = NACOExtractor
    elif args.journal == 'fs':
        from editorial_assistant.extractors.fs import FSExtractor
        extractor_class = FSExtractor
    elif args.journal == 'jota':
        from editorial_assistant.extractors.jota import JOTAExtractor
        extractor_class = JOTAExtractor
    elif args.journal == 'mafe':
        from editorial_assistant.extractors.mafe import MAFEExtractor
        extractor_class = MAFEExtractor
    
    try:
        # Handle different extractor types
        if args.journal in ['mf', 'mor']:
            # ScholarOne extractors take journal_code string
            extractor = extractor_class(journal_config.code, headless=args.headless)
            result = extractor.extract()
            manuscripts = result.manuscripts
        else:
            # Other extractors take journal_config object
            extractor = extractor_class(journal_config)
            manuscripts = extractor.extract_manuscripts()
        
        print(f"\n✅ Extraction complete!")
        print(f"   Found {len(manuscripts)} manuscripts")
        
        # Count referees - handle both dict and object formats
        total_referees = 0
        for m in manuscripts:
            if hasattr(m, 'referees'):
                # Manuscript object format
                total_referees += len(m.referees)
            elif isinstance(m, dict):
                # Dictionary format - handle different structures
                if 'declined_referees' in m or 'accepted_referees' in m:
                    # SICON format
                    declined = len(m.get('declined_referees', []))
                    accepted = len(m.get('accepted_referees', []))
                    total_referees += declined + accepted
                elif 'Referees' in m:
                    # SIFIN format
                    total_referees += len(m.get('Referees', []))
        
        print(f"   Total referees: {total_referees}")
        
        # Validate against baseline targets
        _validate_against_baseline(args.journal, manuscripts)
        
        # Show first few manuscripts
        print("\n📄 Sample manuscripts:")
        for i, ms in enumerate(manuscripts[:3]):
            if hasattr(ms, 'manuscript_id'):
                # Manuscript object format
                print(f"   {i+1}. {ms.manuscript_id}: {ms.title}")
                author_names = [author.name if hasattr(author, 'name') else str(author) for author in ms.authors[:2]]
                print(f"      Authors: {', '.join(author_names)}...")
                print(f"      Status: {ms.status}")
                print(f"      Referees: {len(ms.referees)}")
            elif isinstance(ms, dict):
                # Dictionary format - handle different structures
                ms_id = ms.get('id', ms.get('Manuscript #', ms.get('manuscript_id', 'Unknown')))
                title = ms.get('title', ms.get('Title', 'No title'))
                
                # Handle authors field variations
                authors_field = ms.get('contributing_authors') or ms.get('Contributing Authors', '')
                authors = authors_field.split(',') if authors_field else []
                
                status = ms.get('current_stage', ms.get('Current Stage', ms.get('status', 'Unknown')))
                
                # Count referees based on structure
                if 'declined_referees' in ms or 'accepted_referees' in ms:
                    # SICON format
                    declined = len(ms.get('declined_referees', []))
                    accepted = len(ms.get('accepted_referees', []))
                    referee_count = declined + accepted
                elif 'Referees' in ms:
                    # SIFIN format
                    referee_count = len(ms.get('Referees', []))
                else:
                    referee_count = 0
                
                print(f"   {i+1}. {ms_id}: {title}")
                print(f"      Authors: {', '.join(authors[:2])}{'...' if len(authors) > 2 else ''}")
                print(f"      Status: {status}")
                print(f"      Referees: {referee_count}")
        
        if len(manuscripts) > 3:
            print(f"   ... and {len(manuscripts) - 3} more")
            
        return 0
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())