#!/usr/bin/env python3
"""
Legacy System Migration Script
Helps transition from old scrapers to new clean architecture
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src to path for new system
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Legacy system imports
legacy_available = True
try:
    from journals.sicon import SICON as LegacySICON
    from journals.siam_base import SIAMJournalExtractor
except ImportError:
    legacy_available = False
    print("⚠️  Legacy system not available")

# New system imports
from src.infrastructure.config import get_settings
from src.infrastructure.database.engine import get_session
from src.infrastructure.browser_pool import PlaywrightBrowserPool
from src.infrastructure.scrapers.sicon_scraper import SICONScraper
from src.infrastructure.scrapers.sifin_scraper import SIFINScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages migration from legacy to new architecture"""
    
    def __init__(self):
        self.settings = get_settings()
        self.migration_data = {}
        self.output_dir = Path("migration_output")
        self.output_dir.mkdir(exist_ok=True)
        
    async def analyze_legacy_system(self) -> Dict[str, Any]:
        """Analyze the legacy system structure and data"""
        logger.info("Analyzing legacy system...")
        
        analysis = {
            'legacy_scrapers': [],
            'config_files': [],
            'data_files': [],
            'issues': [],
            'recommendations': []
        }
        
        # Check for legacy scrapers
        journals_dir = Path("journals")
        if journals_dir.exists():
            for file_path in journals_dir.glob("*.py"):
                if file_path.name not in ["__init__.py", "__pycache__"]:
                    analysis['legacy_scrapers'].append({
                        'name': file_path.stem,
                        'path': str(file_path),
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
        
        # Check for configuration files
        config_files = [
            ".env", "config.py", "credentials.json", 
            "journal_config.py", "settings.py"
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                analysis['config_files'].append({
                    'name': config_file,
                    'path': str(config_path),
                    'size': config_path.stat().st_size
                })
        
        # Check for data directories
        data_dirs = ["data", "output", "downloads", "pdfs", "reports"]
        for data_dir in data_dirs:
            data_path = Path(data_dir)
            if data_path.exists():
                file_count = sum(1 for _ in data_path.rglob("*") if _.is_file())
                analysis['data_files'].append({
                    'directory': data_dir,
                    'file_count': file_count,
                    'size_mb': sum(f.stat().st_size for f in data_path.rglob("*") if f.is_file()) / 1024 / 1024
                })
        
        # Add recommendations
        if analysis['legacy_scrapers']:
            analysis['recommendations'].append(
                "Found legacy scrapers - consider running parallel extraction test"
            )
        
        if not analysis['config_files']:
            analysis['issues'].append(
                "No configuration files found - may need manual credential setup"
            )
        
        return analysis
    
    async def compare_extractors(self, journal_code: str) -> Dict[str, Any]:
        """Compare legacy vs new extractor for a specific journal"""
        logger.info(f"Comparing extractors for {journal_code}...")
        
        comparison = {
            'journal': journal_code,
            'legacy_available': False,
            'new_available': False,
            'legacy_results': None,
            'new_results': None,
            'differences': [],
            'recommendation': ""
        }
        
        # Test new extractor
        try:
            browser_pool = PlaywrightBrowserPool(size=1)
            await browser_pool.start()
            
            if journal_code.upper() == "SICON":
                new_scraper = SICONScraper(browser_pool)
                comparison['new_available'] = True
                # Note: Not actually running extraction to avoid authentication
                logger.info("✓ New SICON scraper available")
                
            elif journal_code.upper() == "SIFIN":
                new_scraper = SIFINScraper(browser_pool)
                comparison['new_available'] = True
                logger.info("✓ New SIFIN scraper available")
            
            await browser_pool.stop()
            
        except Exception as e:
            logger.error(f"New extractor test failed: {e}")
            comparison['new_available'] = False
        
        # Test legacy extractor if available
        if legacy_available:
            try:
                if journal_code.upper() == "SICON":
                    legacy_scraper = LegacySICON()
                    comparison['legacy_available'] = True
                    logger.info("✓ Legacy SICON scraper available")
            except Exception as e:
                logger.error(f"Legacy extractor test failed: {e}")
                comparison['legacy_available'] = False
        
        # Generate recommendation
        if comparison['new_available'] and comparison['legacy_available']:
            comparison['recommendation'] = "Both systems available - can run parallel extraction"
        elif comparison['new_available']:
            comparison['recommendation'] = "Only new system available - ready for migration"
        elif comparison['legacy_available']:
            comparison['recommendation'] = "Only legacy system available - need to fix new system"
        else:
            comparison['recommendation'] = "Neither system available - need to investigate"
        
        return comparison
    
    async def create_migration_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed migration plan"""
        logger.info("Creating migration plan...")
        
        plan = {
            'phases': [],
            'timeline': {},
            'risks': [],
            'rollback_plan': {},
            'validation_steps': []
        }
        
        # Phase 1: Environment Setup
        plan['phases'].append({
            'name': "Environment Setup",
            'description': "Prepare new system environment",
            'steps': [
                "Activate clean virtual environment",
                "Verify PostgreSQL database connection",
                "Run integration tests to ensure system health",
                "Backup existing data and configurations"
            ],
            'estimated_time': "30 minutes"
        })
        
        # Phase 2: Data Migration
        plan['phases'].append({
            'name': "Data Migration",
            'description': "Migrate existing data to new system",
            'steps': [
                "Export data from legacy system (if any)",
                "Create database tables using new schema",
                "Import historical data with transformation",
                "Validate data integrity"
            ],
            'estimated_time': "1-2 hours"
        })
        
        # Phase 3: Parallel Running
        plan['phases'].append({
            'name': "Parallel Validation",
            'description': "Run both systems in parallel",
            'steps': [
                "Run legacy extractors and save results",
                "Run new extractors and save results",
                "Compare outputs for accuracy",
                "Document any differences"
            ],
            'estimated_time': "2-4 hours"
        })
        
        # Phase 4: Cutover
        plan['phases'].append({
            'name': "System Cutover",
            'description': "Switch to new system",
            'steps': [
                "Stop legacy system scheduling",
                "Update automation scripts to use new system",
                "Monitor new system for 24 hours",
                "Archive legacy system files"
            ],
            'estimated_time': "1 hour + monitoring"
        })
        
        # Add risks
        plan['risks'] = [
            "Authentication credentials may need re-setup",
            "Journal websites may have changed since legacy implementation",
            "Data formats may be incompatible",
            "Performance may differ between systems"
        ]
        
        # Rollback plan
        plan['rollback_plan'] = {
            'trigger_conditions': [
                "New system fails to authenticate",
                "Data extraction returns empty results",
                "Critical errors in new scrapers"
            ],
            'steps': [
                "Reactivate legacy virtual environment",
                "Restore legacy cron jobs/scheduling",
                "Continue with legacy system while debugging new system"
            ]
        }
        
        # Validation steps
        plan['validation_steps'] = [
            "Run integration tests successfully",
            "Compare manuscript counts between systems",
            "Verify referee data completeness",
            "Check database integrity constraints"
        ]
        
        return plan
    
    async def generate_migration_scripts(self) -> None:
        """Generate helper scripts for migration"""
        logger.info("Generating migration helper scripts...")
        
        # Script 1: Run parallel extraction
        parallel_script = '''#!/usr/bin/env python3
"""
Parallel Extraction Test
Run both legacy and new systems for comparison
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def run_parallel_extraction():
    results = {
        'timestamp': datetime.now().isoformat(),
        'legacy': {},
        'new': {},
        'comparison': {}
    }
    
    # Run legacy SICON (if available)
    try:
        from journals.sicon import SICON
        legacy_sicon = SICON()
        legacy_results = legacy_sicon.extract()
        results['legacy']['sicon'] = {
            'manuscript_count': len(legacy_results.get('manuscripts', [])),
            'success': True
        }
    except Exception as e:
        results['legacy']['sicon'] = {'success': False, 'error': str(e)}
    
    # Run new SICON
    try:
        import sys
        sys.path.insert(0, 'src')
        from infrastructure.browser_pool import PlaywrightBrowserPool
        from infrastructure.scrapers.sicon_scraper import SICONScraper
        
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        
        new_sicon = SICONScraper(browser_pool)
        # Note: Would need authentication setup for full test
        results['new']['sicon'] = {'available': True}
        
        await browser_pool.stop()
    except Exception as e:
        results['new']['sicon'] = {'available': False, 'error': str(e)}
    
    # Save results
    output_file = Path('migration_output/parallel_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Parallel extraction test completed. Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(run_parallel_extraction())
'''
        
        script_path = self.output_dir / "run_parallel_test.py"
        script_path.write_text(parallel_script)
        script_path.chmod(0o755)
        
        # Script 2: Verify new system
        verify_script = '''#!/usr/bin/env python3
"""
New System Verification
Verify all components of new system are working
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

async def verify_new_system():
    print("Verifying new system components...")
    
    try:
        # Test configuration
        from infrastructure.config import get_settings
        settings = get_settings()
        print("✓ Configuration loaded")
        
        # Test database
        from infrastructure.database.engine import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        print("✓ Database connection working")
        
        # Test browser pool
        from infrastructure.browser_pool import PlaywrightBrowserPool
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        await browser_pool.stop()
        print("✓ Browser pool working")
        
        # Test scrapers
        from infrastructure.scrapers.sicon_scraper import SICONScraper
        from infrastructure.scrapers.sifin_scraper import SIFINScraper
        
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        
        sicon = SICONScraper(browser_pool)
        sifin = SIFINScraper(browser_pool)
        
        await browser_pool.stop()
        print("✓ Scrapers instantiated successfully")
        
        print("\\n🎉 New system verification complete!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_new_system())
    sys.exit(0 if success else 1)
'''
        
        verify_path = self.output_dir / "verify_new_system.py"
        verify_path.write_text(verify_script)
        verify_path.chmod(0o755)
        
        logger.info(f"Generated migration scripts in {self.output_dir}/")
    
    async def run_full_migration_analysis(self) -> None:
        """Run complete migration analysis and generate report"""
        logger.info("Starting full migration analysis...")
        
        # Analyze legacy system
        analysis = await self.analyze_legacy_system()
        
        # Compare extractors
        sicon_comparison = await self.compare_extractors("SICON")
        sifin_comparison = await self.compare_extractors("SIFIN")
        
        # Create migration plan
        plan = await self.create_migration_plan(analysis)
        
        # Generate scripts
        await self.generate_migration_scripts()
        
        # Create comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'legacy_analysis': analysis,
            'extractor_comparisons': {
                'sicon': sicon_comparison,
                'sifin': sifin_comparison
            },
            'migration_plan': plan,
            'next_steps': [
                "Review this migration report",
                "Run parallel extraction test using generated scripts",
                "Backup any important legacy data",
                "Set up credentials for new system",
                "Execute migration plan phases in order"
            ]
        }
        
        # Save report
        report_file = self.output_dir / "migration_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Create human-readable summary
        summary = f"""
Migration Analysis Report
========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Legacy System Analysis:
- Scrapers found: {len(analysis['legacy_scrapers'])}
- Config files: {len(analysis['config_files'])}
- Data directories: {len(analysis['data_files'])}

Extractor Status:
- SICON: Legacy={sicon_comparison['legacy_available']}, New={sicon_comparison['new_available']}
- SIFIN: Legacy={sifin_comparison['legacy_available']}, New={sifin_comparison['new_available']}

Migration Readiness:
{'🟢 READY' if sicon_comparison['new_available'] and sifin_comparison['new_available'] else '🟡 NEEDS ATTENTION'}

Next Steps:
1. Run: python migration_output/verify_new_system.py
2. Run: python migration_output/run_parallel_test.py
3. Review detailed report: migration_output/migration_report.json
4. Follow migration plan phases

Generated Files:
- {report_file}
- {self.output_dir}/verify_new_system.py
- {self.output_dir}/run_parallel_test.py
"""
        
        summary_file = self.output_dir / "migration_summary.txt"
        summary_file.write_text(summary)
        
        print(summary)
        logger.info(f"Migration analysis complete! Check {self.output_dir}/ for all files.")


async def main():
    """Main migration analysis function"""
    manager = MigrationManager()
    await manager.run_full_migration_analysis()


if __name__ == "__main__":
    asyncio.run(main())