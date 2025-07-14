#!/usr/bin/env python3
"""
Analyze referee deduplication between manuscripts and revisions
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def analyze_deduplication():
    """Analyze referee overlap between manuscripts"""
    
    # Load MOR results
    mor_results_file = Path("mor_final_working_results/mor_referee_results.json")
    with open(mor_results_file, 'r') as f:
        results = json.load(f)
    
    logger.info("📊 REFEREE DEDUPLICATION ANALYSIS")
    logger.info("="*60)
    
    # Track all referees across manuscripts
    all_referees = {}
    
    for ms in results['manuscripts']:
        ms_id = ms['manuscript_id']
        logger.info(f"\n📄 {ms_id}:")
        
        # Active referees
        for ref in ms['referees']:
            ref_name = ref['name']
            ref_key = f"{ref_name}|{ref.get('email', 'no-email')}"
            
            if ref_key not in all_referees:
                all_referees[ref_key] = []
            all_referees[ref_key].append(f"{ms_id} (active)")
            
            logger.info(f"   Active: {ref_name}")
        
        # Completed referees
        for ref in ms.get('completed_referees', []):
            ref_name = ref['name']
            ref_key = f"{ref_name}|{ref.get('email', 'no-email')}"
            
            if ref_key not in all_referees:
                all_referees[ref_key] = []
            all_referees[ref_key].append(f"{ms_id} (completed)")
            
            logger.info(f"   Completed: {ref_name}")
    
    # Analyze duplicates
    logger.info(f"\n\n🔍 DUPLICATE ANALYSIS:")
    logger.info("="*60)
    
    duplicates_found = False
    for ref_key, manuscripts in all_referees.items():
        if len(manuscripts) > 1:
            duplicates_found = True
            ref_name = ref_key.split('|')[0]
            logger.info(f"\n⚠️  {ref_name} appears in multiple manuscripts:")
            for ms in manuscripts:
                logger.info(f"   - {ms}")
    
    if not duplicates_found:
        logger.info("✅ No duplicates found - each referee is unique")
    
    # Check specific case: MOR-2023-0376 vs MOR-2023-0376.R1
    logger.info(f"\n\n📋 SPECIFIC CASE: MOR-2023-0376 vs MOR-2023-0376.R1")
    logger.info("="*60)
    
    original = None
    revision = None
    
    for ms in results['manuscripts']:
        if ms['manuscript_id'] == 'MOR-2023-0376':
            original = ms
        elif ms['manuscript_id'] == 'MOR-2023-0376.R1':
            revision = ms
    
    if original and revision:
        logger.info("\nOriginal (MOR-2023-0376):")
        original_refs = set()
        for ref in original['referees']:
            original_refs.add(ref['name'])
            logger.info(f"  Active: {ref['name']}")
        for ref in original.get('completed_referees', []):
            original_refs.add(ref['name'])
            logger.info(f"  Completed: {ref['name']}")
        
        logger.info("\nRevision (MOR-2023-0376.R1):")
        revision_refs = set()
        for ref in revision['referees']:
            revision_refs.add(ref['name'])
            logger.info(f"  Active: {ref['name']}")
        for ref in revision.get('completed_referees', []):
            revision_refs.add(ref['name'])
            logger.info(f"  Completed: {ref['name']}")
        
        # Check overlap
        overlap = original_refs.intersection(revision_refs)
        if overlap:
            logger.info(f"\n⚠️  Overlapping referees: {overlap}")
            logger.info("\nNOTE: This is expected for revisions - the same referees")
            logger.info("      typically review both the original and revised versions.")
        
        # Summary
        logger.info(f"\n📊 COUNTING SUMMARY:")
        logger.info(f"   Original: {len(original_refs)} unique referees")
        logger.info(f"   Revision: {len(revision_refs)} unique referees")
        logger.info(f"   Total if counted separately: {len(original_refs) + len(revision_refs)}")
        logger.info(f"   Total unique referees: {len(original_refs.union(revision_refs))}")

if __name__ == "__main__":
    analyze_deduplication()