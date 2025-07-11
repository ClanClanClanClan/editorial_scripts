#!/usr/bin/env python3
"""
SIAM Data Extraction Script

This script performs complete data extraction from SICON and SIFIN journals:
- Authenticates with ORCID
- Extracts manuscript information
- Extracts referee data including names, emails, and statuses
"""

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.sicon import SICONExtractor
from editorial_assistant.extractors.sifin import SIFINExtractor
from editorial_assistant.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'siam_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SIAMDataExtractor:
    """Complete SIAM data extraction for SICON and SIFIN journals."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.config = self._load_config()
        self.output_dir = Path('./siam_extraction_output')
        self.output_dir.mkdir(exist_ok=True)
        
        print("🔬 SIAM Data Extractor initialized")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📋 Session ID: {self.session_manager.session.session_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load journal configuration."""
        import yaml
        config_path = Path(__file__).parent / "config" / "corrected_journals.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_journal_config(self, journal_code: str) -> JournalConfig:
        """Create JournalConfig for specified journal."""
        journal_data = self.config["journals"][journal_code]
        platform_config = self.config["platforms"][journal_data["platform"]]
        
        return JournalConfig(
            code=journal_code,
            name=journal_data["name"],
            platform=journal_data["platform"],
            url=journal_data["url"],
            categories=journal_data.get("categories", []),
            patterns=journal_data.get("patterns", {}),
            credentials=journal_data.get("credentials", {}),
            settings=journal_data.get("settings", {}),
            platform_config=platform_config
        )
    
    def check_credentials(self) -> bool:
        """Check if ORCID credentials are available."""
        print("\n🔐 Checking ORCID credentials...")
        
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user or not orcid_pass:
            print("❌ ORCID credentials not found in environment variables")
            return False
        
        print(f"✅ ORCID_USER: {orcid_user}")
        print(f"✅ ORCID_PASS: {'*' * len(orcid_pass)}")
        return True
    
    def extract_sicon_data(self) -> Dict[str, Any]:
        """Extract complete data from SICON journal."""
        print("\n" + "="*60)
        print("🎯 EXTRACTING SICON DATA")
        print("="*60)
        
        result = {
            "journal": "SICON",
            "success": False,
            "error": None,
            "manuscripts": [],
            "extraction_time": datetime.now().isoformat(),
            "stats": {}
        }
        
        try:
            # Create SICON extractor
            sicon_config = self._create_journal_config('SICON')
            extractor = SICONExtractor(sicon_config)
            
            print("📝 SICON extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   URL: {extractor.journal.url}")
            
            # Extract manuscripts
            print("\n🔍 Extracting manuscripts from SICON...")
            manuscripts = extractor.extract_manuscripts()
            
            if not manuscripts:
                print("⚠️  No manuscripts found in SICON")
                result["manuscripts"] = []
                result["stats"] = {"total_manuscripts": 0, "total_referees": 0}
            else:
                print(f"✅ Found {len(manuscripts)} manuscripts")
                
                # Convert to serializable format
                serializable_manuscripts = []
                total_referees = 0
                
                for manuscript in manuscripts:
                    ms_data = {
                        "manuscript_id": manuscript.get("Manuscript #", ""),
                        "title": manuscript.get("Title", ""),
                        "submitted": manuscript.get("Submitted", ""),
                        "current_stage": manuscript.get("Current Stage", ""),
                        "referees": []
                    }
                    
                    # Process referees
                    for referee in manuscript.get("Referees", []):
                        ref_data = {
                            "name": referee.get("Referee Name", ""),
                            "email": referee.get("Referee Email", ""),
                            "status": referee.get("Status", ""),
                            "due_date": referee.get("Due Date", ""),
                            "url": referee.get("Referee URL", "")
                        }
                        ms_data["referees"].append(ref_data)
                        total_referees += 1
                    
                    serializable_manuscripts.append(ms_data)
                    
                    # Print manuscript summary
                    print(f"   📄 {ms_data['manuscript_id']}: {ms_data['title'][:50]}...")
                    print(f"      📧 {len(ms_data['referees'])} referees")
                
                result["manuscripts"] = serializable_manuscripts
                result["stats"] = {
                    "total_manuscripts": len(manuscripts),
                    "total_referees": total_referees
                }
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SICON extraction failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            result["error"] = error_msg
            result["traceback"] = traceback.format_exc()
        
        return result
    
    def extract_sifin_data(self) -> Dict[str, Any]:
        """Extract complete data from SIFIN journal."""
        print("\n" + "="*60)
        print("🎯 EXTRACTING SIFIN DATA")
        print("="*60)
        
        result = {
            "journal": "SIFIN",
            "success": False,
            "error": None,
            "manuscripts": [],
            "extraction_time": datetime.now().isoformat(),
            "stats": {}
        }
        
        try:
            # Create SIFIN extractor
            sifin_config = self._create_journal_config('SIFIN')
            extractor = SIFINExtractor(sifin_config)
            
            print("📝 SIFIN extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   URL: {extractor.journal.url}")
            
            # Extract manuscripts
            print("\n🔍 Extracting manuscripts from SIFIN...")
            manuscripts = extractor.extract_manuscripts()
            
            if not manuscripts:
                print("⚠️  No manuscripts found in SIFIN")
                result["manuscripts"] = []
                result["stats"] = {"total_manuscripts": 0, "total_referees": 0}
            else:
                print(f"✅ Found {len(manuscripts)} manuscripts")
                
                # Convert to serializable format
                serializable_manuscripts = []
                total_referees = 0
                
                for manuscript in manuscripts:
                    ms_data = {
                        "manuscript_id": manuscript.get("Manuscript #", ""),
                        "title": manuscript.get("Title", ""),
                        "submitted": manuscript.get("Submitted", ""),
                        "current_stage": manuscript.get("Current Stage", ""),
                        "referees": []
                    }
                    
                    # Process referees
                    for referee in manuscript.get("Referees", []):
                        ref_data = {
                            "name": referee.get("Referee Name", ""),
                            "email": referee.get("Referee Email", ""),
                            "status": referee.get("Status", ""),
                            "due_date": referee.get("Due Date", ""),
                            "url": referee.get("Referee URL", "")
                        }
                        ms_data["referees"].append(ref_data)
                        total_referees += 1
                    
                    serializable_manuscripts.append(ms_data)
                    
                    # Print manuscript summary
                    print(f"   📄 {ms_data['manuscript_id']}: {ms_data['title'][:50]}...")
                    print(f"      📧 {len(ms_data['referees'])} referees")
                
                result["manuscripts"] = serializable_manuscripts
                result["stats"] = {
                    "total_manuscripts": len(manuscripts),
                    "total_referees": total_referees
                }
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SIFIN extraction failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            result["error"] = error_msg
            result["traceback"] = traceback.format_exc()
        
        return result
    
    def run_complete_extraction(self) -> Dict[str, Any]:
        """Run complete data extraction for both journals."""
        print("\n🚀 STARTING COMPLETE SIAM DATA EXTRACTION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        session_results = {
            "start_time": datetime.now().isoformat(),
            "credentials_check": False,
            "sicon_results": {},
            "sifin_results": {},
            "overall_success": False,
            "total_stats": {}
        }
        
        try:
            # Check credentials
            session_results["credentials_check"] = self.check_credentials()
            
            if not session_results["credentials_check"]:
                raise Exception("ORCID credentials not available")
            
            # Extract SICON data
            print("\n🔄 Starting SICON extraction...")
            session_results["sicon_results"] = self.extract_sicon_data()
            
            # Extract SIFIN data
            print("\n🔄 Starting SIFIN extraction...")
            session_results["sifin_results"] = self.extract_sifin_data()
            
            # Calculate overall statistics
            sicon_success = session_results["sicon_results"].get("success", False)
            sifin_success = session_results["sifin_results"].get("success", False)
            
            session_results["overall_success"] = sicon_success and sifin_success
            
            # Aggregate statistics
            total_manuscripts = 0
            total_referees = 0
            
            if sicon_success:
                sicon_stats = session_results["sicon_results"].get("stats", {})
                total_manuscripts += sicon_stats.get("total_manuscripts", 0)
                total_referees += sicon_stats.get("total_referees", 0)
            
            if sifin_success:
                sifin_stats = session_results["sifin_results"].get("stats", {})
                total_manuscripts += sifin_stats.get("total_manuscripts", 0)
                total_referees += sifin_stats.get("total_referees", 0)
            
            session_results["total_stats"] = {
                "total_manuscripts": total_manuscripts,
                "total_referees": total_referees,
                "successful_extractions": sum([sicon_success, sifin_success])
            }
            
            # Save results to file
            self._save_results(session_results)
            
            # Save session milestone
            if session_results["overall_success"]:
                self.session_manager.save_implementation_milestone(
                    "SIAM Data Extraction Complete",
                    ["extract_siam_data.py"],
                    f"Successfully extracted {total_manuscripts} manuscripts with {total_referees} referees from SICON and SIFIN journals"
                )
            
        except Exception as e:
            logger.error(f"Complete extraction failed: {e}")
            logger.error(traceback.format_exc())
            session_results["error"] = str(e)
            session_results["traceback"] = traceback.format_exc()
        
        session_results["end_time"] = datetime.now().isoformat()
        
        # Print final summary
        self._print_extraction_summary(session_results)
        
        return session_results
    
    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save extraction results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"siam_extraction_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
    
    def _print_extraction_summary(self, results: Dict[str, Any]) -> None:
        """Print comprehensive extraction summary."""
        print("\n" + "="*80)
        print("📊 SIAM DATA EXTRACTION SUMMARY")
        print("="*80)
        
        # Credentials
        creds_status = "✅" if results["credentials_check"] else "❌"
        print(f"{creds_status} ORCID Credentials: {'Available' if results['credentials_check'] else 'Missing'}")
        
        # SICON results
        sicon_results = results.get("sicon_results", {})
        sicon_success = sicon_results.get("success", False)
        sicon_status = "✅" if sicon_success else "❌"
        print(f"{sicon_status} SICON Extraction: {'Success' if sicon_success else 'Failed'}")
        
        if sicon_success:
            sicon_stats = sicon_results.get("stats", {})
            print(f"   📄 Manuscripts: {sicon_stats.get('total_manuscripts', 0)}")
            print(f"   📧 Referees: {sicon_stats.get('total_referees', 0)}")
        elif sicon_results.get("error"):
            print(f"   Error: {sicon_results['error']}")
        
        # SIFIN results
        sifin_results = results.get("sifin_results", {})
        sifin_success = sifin_results.get("success", False)
        sifin_status = "✅" if sifin_success else "❌"
        print(f"{sifin_status} SIFIN Extraction: {'Success' if sifin_success else 'Failed'}")
        
        if sifin_success:
            sifin_stats = sifin_results.get("stats", {})
            print(f"   📄 Manuscripts: {sifin_stats.get('total_manuscripts', 0)}")
            print(f"   📧 Referees: {sifin_stats.get('total_referees', 0)}")
        elif sifin_results.get("error"):
            print(f"   Error: {sifin_results['error']}")
        
        # Overall results
        overall_status = "✅" if results["overall_success"] else "❌"
        total_stats = results.get("total_stats", {})
        print(f"\n{overall_status} OVERALL STATUS: {'SUCCESS' if results['overall_success'] else 'FAILED'}")
        print(f"📊 Total Manuscripts: {total_stats.get('total_manuscripts', 0)}")
        print(f"📧 Total Referees: {total_stats.get('total_referees', 0)}")
        print(f"🎯 Successful Extractions: {total_stats.get('successful_extractions', 0)}/2")
        
        print(f"\n📁 Output directory: {self.output_dir}")
        print(f"📋 Session ID: {self.session_manager.session.session_id}")


def main():
    """Main extraction entry point."""
    extractor = SIAMDataExtractor()
    
    # Run complete extraction
    results = extractor.run_complete_extraction()
    
    # Exit with appropriate code
    if results["overall_success"]:
        print("\n✅ Data extraction completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Data extraction encountered issues")
        sys.exit(1)


if __name__ == "__main__":
    main()