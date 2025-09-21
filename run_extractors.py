#!/usr/bin/env python3
"""
Editorial Extractors Runner
==========================

Simple orchestrator for running journal extractors reliably.
Focuses on working extractors first, not grand architecture.

Supports:
- MF (Mathematical Finance) - WORKING
- MOR (Mathematics of Operations Research) - WORKING
- SICON, SIFIN, NACO, JOTA, MAFE, FS - TODO

Usage:
    python3 run_extractors.py --journal mf
    python3 run_extractors.py --journal mor
    python3 run_extractors.py --all
    python3 run_extractors.py --status
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add production extractors to path
sys.path.insert(0, 'production/src/extractors')

class ExtractorOrchestrator:
    """Simple orchestrator focused on working extractors."""
    
    def __init__(self, output_dir: str = "results"):
        """Initialize orchestrator.
        
        Args:
            output_dir: Directory to save extraction results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Supported extractors (working first)
        self.extractors = {
            'mf': {
                'name': 'Mathematical Finance',
                'module': 'mf_extractor',
                'class': 'ComprehensiveMFExtractor',
                'platform': 'ScholarOne',
                'status': 'WORKING',
                'url': 'https://mc.manuscriptcentral.com/mafi'
            },
            'mor': {
                'name': 'Mathematics of Operations Research', 
                'module': 'mor_extractor',
                'class': 'ComprehensiveMORExtractor',
                'platform': 'ScholarOne', 
                'status': 'WORKING',
                'url': 'https://mc.manuscriptcentral.com/mor'
            },
            'sicon': {
                'name': 'SIAM Control and Optimization',
                'module': 'sicon_extractor',
                'class': 'ComprehensiveSICONExtractor',
                'platform': 'SIAM',
                'status': 'WORKING',
                'url': 'https://epubs.siam.org/journal/sicon'
            },
            'sifin': {
                'name': 'SIAM Financial Mathematics',
                'module': 'sifin_extractor',
                'class': 'ComprehensiveSIFINExtractor',
                'platform': 'SIAM',
                'status': 'WORKING', 
                'url': 'https://epubs.siam.org/journal/sifin'
            },
            'naco': {
                'name': 'Numerical Algebra, Control and Optimization',
                'module': 'naco_extractor',
                'class': 'ComprehensiveNACOExtractor',
                'platform': 'AIMS Sciences',
                'status': 'TODO',
                'url': 'https://www.aimsciences.org/naco'
            },
            'jota': {
                'name': 'Journal of Optimization Theory and Applications',
                'module': 'jota_extractor',
                'class': 'ComprehensiveJOTAExtractor',
                'platform': 'Editorial Manager',
                'status': 'WORKING',
                'url': 'https://www.editorialmanager.com/jota'
            },
            'mafe': {
                'name': 'Mathematics and Financial Economics',
                'module': 'mafe_extractor',
                'class': 'ComprehensiveMAFEExtractor',
                'platform': 'Editorial Manager', 
                'status': 'WORKING',
                'url': 'https://www.editorialmanager.com/mafe'
            },
            'fs': {
                'name': 'Finance and Stochastics',
                'module': 'fs_extractor',
                'class': 'ComprehensiveFSExtractor',
                'platform': 'Email (Gmail)',
                'status': 'WORKING',
                'url': 'Email-based workflow'
            }
        }
        
        self.logger.info(f"Orchestrator initialized with output directory: {self.output_dir}")
        
    def setup_logging(self):
        """Setup logging for orchestrator."""
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def show_status(self):
        """Show status of all extractors."""
        print("\n📊 EDITORIAL EXTRACTORS STATUS")
        print("=" * 60)
        
        working = []
        todo = []
        
        for journal_id, config in self.extractors.items():
            name = config['name']
            platform = config['platform']
            status = config['status']
            
            status_icon = "✅" if status == "WORKING" else "⚠️"
            print(f"{status_icon} {journal_id.upper():6} | {name:35} | {platform:15} | {status}")
            
            if status == "WORKING":
                working.append(journal_id)
            else:
                todo.append(journal_id)
        
        print()
        print(f"✅ WORKING: {len(working)} extractors ({', '.join(working)})")
        print(f"⚠️ TODO: {len(todo)} extractors ({', '.join(todo)})")
        print()
        
    def run_extractor(self, journal_id: str, headless: bool = True) -> Optional[Dict]:
        """Run a specific extractor.
        
        Args:
            journal_id: Journal identifier (mf, mor, etc.)
            headless: Run in headless mode
            
        Returns:
            Extraction results or None if failed
        """
        if journal_id not in self.extractors:
            self.logger.error(f"Unknown journal: {journal_id}")
            return None
            
        config = self.extractors[journal_id]
        
        if config['status'] != 'WORKING':
            self.logger.error(f"Extractor {journal_id} not implemented yet")
            return None
            
        self.logger.info(f"Starting extraction for {config['name']} ({journal_id.upper()})")
        
        try:
            # Import the extractor module
            module_name = config['module']
            class_name = config['class']
            
            module = __import__(module_name)
            extractor_class = getattr(module, class_name)
            
            # Create output directory for this journal
            journal_output = self.output_dir / journal_id
            journal_output.mkdir(exist_ok=True)
            
            # Initialize and run extractor
            extractor = extractor_class()
            
            self.logger.info(f"Running {journal_id.upper()} extraction...")
            start_time = datetime.now()
            
            # Run extraction (this will take time)
            result = extractor.extract_all()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = journal_output / f"{journal_id}_extraction_{timestamp}.json"
            
            if hasattr(extractor, 'manuscripts') and extractor.manuscripts:
                # Save detailed results
                extraction_data = {
                    'journal': journal_id,
                    'journal_name': config['name'],
                    'extraction_time': timestamp,
                    'duration_seconds': duration,
                    'manuscripts_count': len(extractor.manuscripts),
                    'manuscripts': [m.to_dict() if hasattr(m, 'to_dict') else m for m in extractor.manuscripts]
                }
                
                with open(results_file, 'w') as f:
                    json.dump(extraction_data, f, indent=2, default=str)
                
                self.logger.info(f"Extraction completed successfully")
                self.logger.info(f"Duration: {duration:.1f} seconds")
                self.logger.info(f"Manuscripts: {len(extractor.manuscripts)}")
                self.logger.info(f"Results saved: {results_file}")
                
                return extraction_data
                
            else:
                self.logger.warning("No manuscripts extracted")
                return None
                
        except Exception as e:
            self.logger.error(f"Extraction failed for {journal_id}: {e}")
            return None
        finally:
            # Cleanup
            try:
                if 'extractor' in locals():
                    extractor.cleanup()
            except:
                pass
    
    def run_all_working(self, headless: bool = True) -> Dict[str, Optional[Dict]]:
        """Run all working extractors.
        
        Args:
            headless: Run in headless mode
            
        Returns:
            Results for each extractor
        """
        working_extractors = [
            journal_id for journal_id, config in self.extractors.items()
            if config['status'] == 'WORKING'
        ]
        
        self.logger.info(f"Running all working extractors: {working_extractors}")
        
        results = {}
        for journal_id in working_extractors:
            print(f"\n🚀 STARTING {journal_id.upper()} EXTRACTION")
            print("-" * 50)
            
            result = self.run_extractor(journal_id, headless=headless)
            results[journal_id] = result
            
            if result:
                print(f"✅ {journal_id.upper()} completed: {result['manuscripts_count']} manuscripts")
            else:
                print(f"❌ {journal_id.upper()} failed")
                
        return results
        
    def get_recent_results(self, journal_id: Optional[str] = None) -> List[Dict]:
        """Get recent extraction results.
        
        Args:
            journal_id: Specific journal or None for all
            
        Returns:
            List of recent results
        """
        results = []
        
        search_dirs = []
        if journal_id:
            if journal_id in self.extractors:
                search_dirs = [self.output_dir / journal_id]
        else:
            search_dirs = [self.output_dir / j for j in self.extractors.keys()]
            
        for journal_dir in search_dirs:
            if journal_dir.exists():
                for results_file in journal_dir.glob("*_extraction_*.json"):
                    try:
                        with open(results_file) as f:
                            data = json.load(f)
                            data['file_path'] = str(results_file)
                            results.append(data)
                    except Exception as e:
                        self.logger.warning(f"Could not load {results_file}: {e}")
        
        # Sort by extraction time
        results.sort(key=lambda x: x.get('extraction_time', ''), reverse=True)
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Editorial Extractors Runner")
    parser.add_argument('--journal', '-j', 
                       choices=['mf', 'mor', 'sicon', 'sifin', 'naco', 'jota', 'mafe', 'fs'],
                       help="Run specific journal extractor")
    parser.add_argument('--all', action='store_true', 
                       help="Run all working extractors")
    parser.add_argument('--status', action='store_true',
                       help="Show status of all extractors")
    parser.add_argument('--recent', action='store_true',
                       help="Show recent extraction results")
    parser.add_argument('--visible', action='store_true',
                       help="Run with visible browser (default: headless)")
    parser.add_argument('--output', '-o', default="results",
                       help="Output directory (default: results)")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = ExtractorOrchestrator(args.output)
    
    if args.status:
        orchestrator.show_status()
        
    elif args.recent:
        results = orchestrator.get_recent_results()
        print("\n📊 RECENT EXTRACTION RESULTS")
        print("=" * 60)
        
        if not results:
            print("No results found.")
        else:
            for result in results[:10]:  # Show last 10
                journal = result.get('journal', 'unknown')
                time = result.get('extraction_time', 'unknown')
                count = result.get('manuscripts_count', 0)
                duration = result.get('duration_seconds', 0)
                
                print(f"🗂️  {journal.upper():6} | {time} | {count:3} manuscripts | {duration:6.1f}s")
                
    elif args.journal:
        headless = not args.visible
        result = orchestrator.run_extractor(args.journal, headless=headless)
        
        if result:
            print(f"\n✅ EXTRACTION COMPLETED")
            print(f"Journal: {result['journal_name']}")
            print(f"Manuscripts: {result['manuscripts_count']}")
            print(f"Duration: {result['duration_seconds']:.1f} seconds")
        else:
            print(f"\n❌ EXTRACTION FAILED")
            sys.exit(1)
            
    elif args.all:
        headless = not args.visible
        results = orchestrator.run_all_working(headless=headless)
        
        print(f"\n📊 ALL EXTRACTORS SUMMARY")
        print("=" * 40)
        
        total_manuscripts = 0
        successful = 0
        
        for journal_id, result in results.items():
            if result:
                count = result['manuscripts_count']
                duration = result['duration_seconds']
                print(f"✅ {journal_id.upper():6}: {count:3} manuscripts ({duration:6.1f}s)")
                total_manuscripts += count
                successful += 1
            else:
                print(f"❌ {journal_id.upper():6}: FAILED")
        
        print(f"\nTotal: {successful}/{len(results)} successful, {total_manuscripts} manuscripts")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()