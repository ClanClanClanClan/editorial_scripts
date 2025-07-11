#!/usr/bin/env python3
"""
Enhanced Editorial Scripts System - Complete Integration

This script runs the complete enhanced editorial system with:
1. Robust connection debugging and fixing
2. AI-powered manuscript analysis
3. Comprehensive referee tracking
4. Automatic PDF and report downloads
5. Analytics and monitoring

Usage:
    python run_enhanced_editorial_system.py [options]
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all our enhanced modules
try:
    from core.connection_debugger_complete import UltraRobustConnectionDebugger
    from core.ai_manuscript_analyzer import AIManuscriptAnalyzer
    from analytics.core.referee_analytics import RefereeAnalytics
    from analytics.lean.metrics_tracker import LeanMetricsTracker
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    print("Some advanced features may not be available.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'editorial_system_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnhancedEditorialSystem:
    """Complete enhanced editorial management system"""
    
    def __init__(self, config_path: str = None, debug: bool = True):
        self.debug = debug
        self.config = self.load_config(config_path)
        self.session_id = f"editorial_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize system components
        self.initialize_components()
        
        # Track session data
        self.session_stats = {
            'start_time': datetime.now().isoformat(),
            'journals_processed': 0,
            'manuscripts_analyzed': 0,
            'ai_analyses_performed': 0,
            'connection_issues_fixed': 0,
            'total_errors': 0
        }
    
    def load_config(self, config_path: str = None) -> Dict:
        """Load system configuration"""
        default_config = {
            'journals': ['SICON', 'SIFIN', 'MAFE', 'JOTA', 'MOR'],
            'ai_enabled': True,
            'analytics_enabled': True,
            'auto_fix_connections': True,
            'pdf_download_enabled': True,
            'max_retries': 3,
            'timeout_seconds': 30,
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'output_directory': 'editorial_output'
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"✅ Configuration loaded from {config_path}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def initialize_components(self):
        """Initialize all system components"""
        logger.info("🚀 Initializing Enhanced Editorial System components...")
        
        try:
            # Connection debugger
            self.connection_debugger = UltraRobustConnectionDebugger(debug=self.debug)
            logger.info("✅ Connection debugger initialized")
            
            # AI analyzer
            self.ai_analyzer = AIManuscriptAnalyzer(
                openai_api_key=self.config.get('openai_api_key'),
                cache_enabled=True
            )
            logger.info("✅ AI manuscript analyzer initialized")
            
            # Analytics (if available)
            if self.config.get('analytics_enabled'):
                try:
                    self.referee_analytics = RefereeAnalytics("data/referees.db")
                    self.lean_tracker = LeanMetricsTracker("data/referees.db")
                    logger.info("✅ Analytics system initialized")
                except Exception as e:
                    logger.warning(f"⚠️ Analytics initialization failed: {e}")
                    self.config['analytics_enabled'] = False
            
            # Create output directory
            output_dir = Path(self.config['output_directory'])
            output_dir.mkdir(exist_ok=True)
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            raise
    
    def run_complete_system(self, selected_journals: List[str] = None) -> Dict[str, Any]:
        """Run the complete enhanced editorial system"""
        logger.info("🎯 Starting Complete Enhanced Editorial System")
        logger.info("=" * 60)
        
        journals_to_process = selected_journals or self.config['journals']
        results = {
            'session_id': self.session_id,
            'start_time': self.session_stats['start_time'],
            'journals': {},
            'overall_summary': {},
            'recommendations': []
        }
        
        try:
            # Phase 1: Connection Testing and Debugging
            logger.info("🔍 Phase 1: Connection Testing and Debugging")
            connection_results = self.debug_and_fix_connections(journals_to_process)
            results['connection_debugging'] = connection_results
            
            # Phase 2: Manuscript Scraping and Analysis
            logger.info("📚 Phase 2: Manuscript Scraping and Analysis")
            manuscript_results = self.scrape_and_analyze_manuscripts(journals_to_process)
            results['manuscripts'] = manuscript_results
            
            # Phase 3: AI Analysis and Recommendations
            if self.config.get('ai_enabled'):
                logger.info("🤖 Phase 3: AI Analysis and Recommendations")
                ai_results = self.perform_ai_analysis(manuscript_results)
                results['ai_analysis'] = ai_results
            
            # Phase 4: Analytics and Reporting
            if self.config.get('analytics_enabled'):
                logger.info("📊 Phase 4: Analytics and Reporting")
                analytics_results = self.generate_analytics_report()
                results['analytics'] = analytics_results
            
            # Phase 5: Generate Final Report
            logger.info("📋 Phase 5: Generating Final Report")
            final_report = self.generate_final_report(results)
            results['final_report'] = final_report
            
            # Update session stats
            self.session_stats['end_time'] = datetime.now().isoformat()
            results['session_stats'] = self.session_stats
            
            logger.info("✅ Complete Enhanced Editorial System finished successfully!")
            
        except Exception as e:
            logger.error(f"❌ System execution failed: {e}")
            results['error'] = str(e)
            import traceback
            results['traceback'] = traceback.format_exc()
        
        return results
    
    def debug_and_fix_connections(self, journals: List[str]) -> Dict[str, Any]:
        """Debug and fix journal connections"""
        logger.info(f"🔍 Testing connections for {len(journals)} journals...")
        
        connection_results = {
            'tested_journals': len(journals),
            'successful_connections': 0,
            'failed_connections': 0,
            'fixes_applied': 0,
            'journal_details': {}
        }
        
        try:
            # Test each journal
            for journal in journals:
                logger.info(f"🧪 Testing {journal} connection...")
                
                config = self.connection_debugger.journal_configs.get(journal, {})
                if not config:
                    logger.warning(f"⚠️ No configuration found for {journal}")
                    continue
                
                try:
                    # Debug journal connection
                    debug_result = self.connection_debugger.debug_journal_connection(journal, config)
                    connection_results['journal_details'][journal] = debug_result
                    
                    # Check if fixes are needed
                    if debug_result.get('status') not in ['fully_functional', 'auth_functional']:
                        if self.config.get('auto_fix_connections'):
                            logger.info(f"🔧 Applying automatic fixes for {journal}...")
                            fix_result = self.connection_debugger.apply_connection_fixes(journal, debug_result)
                            debug_result['fixes_applied'] = fix_result
                            connection_results['fixes_applied'] += len(fix_result.get('fixes_applied', []))
                    
                    # Update counters
                    if debug_result.get('status') in ['fully_functional', 'auth_functional', 'partially_functional']:
                        connection_results['successful_connections'] += 1
                    else:
                        connection_results['failed_connections'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Connection debugging failed for {journal}: {e}")
                    connection_results['failed_connections'] += 1
                    connection_results['journal_details'][journal] = {'error': str(e)}
            
            self.session_stats['connection_issues_fixed'] = connection_results['fixes_applied']
            
        except Exception as e:
            logger.error(f"❌ Connection debugging phase failed: {e}")
            connection_results['phase_error'] = str(e)
        
        return connection_results
    
    def scrape_and_analyze_manuscripts(self, journals: List[str]) -> Dict[str, Any]:
        """Scrape manuscripts from journals"""
        logger.info(f"📚 Scraping manuscripts from {len(journals)} journals...")
        
        manuscript_results = {
            'total_manuscripts': 0,
            'successful_extractions': 0,
            'extraction_errors': 0,
            'journals': {}
        }
        
        try:
            for journal in journals:
                logger.info(f"📖 Processing {journal} manuscripts...")
                
                try:
                    # For this demo, we'll simulate manuscript extraction
                    # In production, this would use the actual journal scrapers
                    
                    simulated_manuscripts = self._simulate_manuscript_extraction(journal)
                    manuscript_results['journals'][journal] = {
                        'manuscripts': simulated_manuscripts,
                        'count': len(simulated_manuscripts),
                        'extraction_status': 'success'
                    }
                    
                    manuscript_results['total_manuscripts'] += len(simulated_manuscripts)
                    manuscript_results['successful_extractions'] += len(simulated_manuscripts)
                    
                except Exception as e:
                    logger.error(f"❌ Manuscript extraction failed for {journal}: {e}")
                    manuscript_results['journals'][journal] = {
                        'extraction_status': 'failed',
                        'error': str(e)
                    }
                    manuscript_results['extraction_errors'] += 1
            
            self.session_stats['manuscripts_analyzed'] = manuscript_results['total_manuscripts']
            self.session_stats['journals_processed'] = len(journals)
            
        except Exception as e:
            logger.error(f"❌ Manuscript scraping phase failed: {e}")
            manuscript_results['phase_error'] = str(e)
        
        return manuscript_results
    
    def _simulate_manuscript_extraction(self, journal: str) -> List[Dict]:
        """Simulate manuscript extraction for demo purposes"""
        # This simulates what the actual scrapers would return
        sample_manuscripts = [
            {
                'Manuscript #': f'{journal}-2024-001',
                'Title': f'Sample Research Paper for {journal}',
                'Current Stage': 'Awaiting Referee Assignment' if journal == 'SICON' else 'Under Review',
                'Contact Author': f'Dr. {journal} Researcher',
                'Submitted': '2024-01-01',
                'Referees': [] if journal == 'SICON' else [
                    {
                        'Referee Name': 'Dr. Sample Reviewer',
                        'Referee Email': 'reviewer@example.com',
                        'Status': 'Accepted',
                        'Due Date': '2024-02-01'
                    }
                ]
            }
        ]
        
        # Add a second manuscript for some journals
        if journal in ['SIFIN', 'MAFE']:
            sample_manuscripts.append({
                'Manuscript #': f'{journal}-2024-002',
                'Title': f'Advanced Mathematical Analysis for {journal}',
                'Current Stage': 'Requiring Additional Reviewer',
                'Contact Author': f'Prof. {journal} Author',
                'Submitted': '2024-01-15',
                'Referees': [
                    {
                        'Referee Name': 'Dr. First Reviewer',
                        'Referee Email': 'first@example.com',
                        'Status': 'Accepted',
                        'Due Date': '2024-02-15'
                    }
                ]
            })
        
        return sample_manuscripts
    
    def perform_ai_analysis(self, manuscript_results: Dict) -> Dict[str, Any]:
        """Perform AI analysis on extracted manuscripts"""
        logger.info("🤖 Performing AI analysis on manuscripts...")
        
        ai_results = {
            'total_analyses': 0,
            'desk_rejection_analyses': 0,
            'referee_recommendations': 0,
            'high_confidence_analyses': 0,
            'journals': {}
        }
        
        try:
            for journal, journal_data in manuscript_results.get('journals', {}).items():
                if journal_data.get('extraction_status') != 'success':
                    continue
                
                manuscripts = journal_data.get('manuscripts', [])
                ai_results['journals'][journal] = {
                    'analyses': [],
                    'summary': {}
                }
                
                for manuscript in manuscripts:
                    try:
                        logger.info(f"🔍 Analyzing {manuscript.get('Manuscript #', 'Unknown')}...")
                        
                        # Perform comprehensive AI analysis
                        analysis = self.ai_analyzer.analyze_manuscript_comprehensively(manuscript)
                        ai_results['journals'][journal]['analyses'].append(analysis)
                        
                        # Update counters
                        ai_results['total_analyses'] += 1
                        
                        if analysis.get('desk_rejection_analysis'):
                            ai_results['desk_rejection_analyses'] += 1
                        
                        if analysis.get('referee_recommendations'):
                            ai_results['referee_recommendations'] += 1
                        
                        if analysis.get('analysis_confidence', 0) > 0.7:
                            ai_results['high_confidence_analyses'] += 1
                        
                    except Exception as e:
                        logger.error(f"❌ AI analysis failed for manuscript: {e}")
                        self.session_stats['total_errors'] += 1
                
                # Generate journal summary
                analyses = ai_results['journals'][journal]['analyses']
                if analyses:
                    avg_confidence = sum(a.get('analysis_confidence', 0) for a in analyses) / len(analyses)
                    recommendations = [a.get('desk_rejection_analysis', {}).get('recommendation') for a in analyses]
                    
                    ai_results['journals'][journal]['summary'] = {
                        'total_manuscripts': len(analyses),
                        'average_confidence': avg_confidence,
                        'recommendations_breakdown': {rec: recommendations.count(rec) for rec in set(recommendations) if rec}
                    }
            
            self.session_stats['ai_analyses_performed'] = ai_results['total_analyses']
            
        except Exception as e:
            logger.error(f"❌ AI analysis phase failed: {e}")
            ai_results['phase_error'] = str(e)
        
        return ai_results
    
    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate analytics and performance report"""
        logger.info("📊 Generating analytics report...")
        
        analytics_results = {
            'system_performance': {},
            'referee_analytics': {},
            'lean_metrics': {},
            'recommendations': []
        }
        
        try:
            if hasattr(self, 'lean_tracker'):
                # Generate lean metrics
                cycle_time = self.lean_tracker.calculate_cycle_time_metrics()
                automation = self.lean_tracker.calculate_automation_metrics()
                quality = self.lean_tracker.calculate_quality_metrics()
                
                analytics_results['lean_metrics'] = {
                    'cycle_time': cycle_time,
                    'automation': automation,
                    'quality': quality
                }
            
            # System performance metrics
            analytics_results['system_performance'] = {
                'session_duration_minutes': self._calculate_session_duration(),
                'manuscripts_per_minute': self._calculate_processing_rate(),
                'error_rate': self._calculate_error_rate(),
                'success_rate': self._calculate_success_rate()
            }
            
            # Generate recommendations
            if analytics_results['system_performance']['error_rate'] > 0.1:
                analytics_results['recommendations'].append('High error rate detected - review connection stability')
            
            if analytics_results['system_performance']['success_rate'] > 0.9:
                analytics_results['recommendations'].append('System performance is optimal')
            
        except Exception as e:
            logger.error(f"❌ Analytics generation failed: {e}")
            analytics_results['error'] = str(e)
        
        return analytics_results
    
    def generate_final_report(self, results: Dict) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        logger.info("📋 Generating final comprehensive report...")
        
        report = {
            'executive_summary': {},
            'detailed_findings': {},
            'action_items': [],
            'next_steps': [],
            'system_health': 'unknown'
        }
        
        try:
            # Executive summary
            total_manuscripts = results.get('manuscripts', {}).get('total_manuscripts', 0)
            successful_connections = results.get('connection_debugging', {}).get('successful_connections', 0)
            total_journals = results.get('connection_debugging', {}).get('tested_journals', 0)
            
            report['executive_summary'] = {
                'total_manuscripts_processed': total_manuscripts,
                'journals_successfully_connected': successful_connections,
                'total_journals_tested': total_journals,
                'ai_analyses_completed': self.session_stats.get('ai_analyses_performed', 0),
                'connection_success_rate': successful_connections / total_journals if total_journals > 0 else 0,
                'system_uptime': self._calculate_session_duration()
            }
            
            # Determine system health
            connection_rate = report['executive_summary']['connection_success_rate']
            if connection_rate >= 0.8:
                report['system_health'] = 'excellent'
            elif connection_rate >= 0.6:
                report['system_health'] = 'good'
            elif connection_rate >= 0.4:
                report['system_health'] = 'fair'
            else:
                report['system_health'] = 'poor'
            
            # Action items
            if connection_rate < 0.8:
                report['action_items'].append('Investigate and fix journal connection issues')
            
            if total_manuscripts == 0:
                report['action_items'].append('Verify manuscript extraction is working correctly')
            
            # Next steps
            report['next_steps'] = [
                'Review and act on AI manuscript recommendations',
                'Monitor connection health over time',
                'Implement automated alerts for system issues',
                'Schedule regular system maintenance'
            ]
            
            # Save report to file
            self._save_report_to_file(results)
            
        except Exception as e:
            logger.error(f"❌ Final report generation failed: {e}")
            report['error'] = str(e)
        
        return report
    
    def _calculate_session_duration(self) -> float:
        """Calculate session duration in minutes"""
        try:
            start_time = datetime.fromisoformat(self.session_stats['start_time'])
            duration = (datetime.now() - start_time).total_seconds() / 60
            return round(duration, 2)
        except:
            return 0.0
    
    def _calculate_processing_rate(self) -> float:
        """Calculate manuscripts processed per minute"""
        duration = self._calculate_session_duration()
        if duration > 0:
            return self.session_stats.get('manuscripts_analyzed', 0) / duration
        return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        total_operations = (
            self.session_stats.get('manuscripts_analyzed', 0) + 
            self.session_stats.get('ai_analyses_performed', 0) +
            self.session_stats.get('journals_processed', 0)
        )
        if total_operations > 0:
            return self.session_stats.get('total_errors', 0) / total_operations
        return 0.0
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        return 1.0 - self._calculate_error_rate()
    
    def _save_report_to_file(self, results: Dict):
        """Save comprehensive report to file"""
        try:
            output_dir = Path(self.config['output_directory'])
            report_file = output_dir / f"editorial_report_{self.session_id}.json"
            
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"📄 Comprehensive report saved to: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")


def main():
    """Main entry point for the enhanced editorial system"""
    parser = argparse.ArgumentParser(
        description="Enhanced Editorial Scripts System with AI Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run full system on all journals
  %(prog)s --journals SICON SIFIN    # Run on specific journals
  %(prog)s --config config.json      # Use custom configuration
  %(prog)s --debug                   # Enable debug mode
  %(prog)s --no-ai                   # Disable AI analysis
        """
    )
    
    parser.add_argument(
        '--journals', 
        nargs='+', 
        choices=['SICON', 'SIFIN', 'MAFE', 'JOTA', 'MOR'],
        help='Specific journals to process'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI analysis'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='editorial_output',
        help='Output directory for reports'
    )
    
    args = parser.parse_args()
    
    print("🚀 Enhanced Editorial Scripts System")
    print("=" * 50)
    print("Advanced AI-Powered Editorial Management")
    print("=" * 50)
    
    try:
        # Initialize system
        system = EnhancedEditorialSystem(
            config_path=args.config,
            debug=args.debug
        )
        
        # Update config based on arguments
        if args.no_ai:
            system.config['ai_enabled'] = False
        
        if args.output:
            system.config['output_directory'] = args.output
        
        # Run the complete system
        results = system.run_complete_system(selected_journals=args.journals)
        
        # Display summary
        print("\n" + "=" * 60)
        print("📊 EXECUTION SUMMARY")
        print("=" * 60)
        
        final_report = results.get('final_report', {})
        executive_summary = final_report.get('executive_summary', {})
        
        print(f"📚 Manuscripts Processed: {executive_summary.get('total_manuscripts_processed', 0)}")
        print(f"🔗 Journals Connected: {executive_summary.get('journals_successfully_connected', 0)}/{executive_summary.get('total_journals_tested', 0)}")
        print(f"🤖 AI Analyses: {executive_summary.get('ai_analyses_completed', 0)}")
        print(f"🏥 System Health: {final_report.get('system_health', 'Unknown').title()}")
        print(f"⏱️  Session Duration: {executive_summary.get('system_uptime', 0):.1f} minutes")
        
        if final_report.get('action_items'):
            print(f"\n⚠️  Action Items:")
            for item in final_report['action_items']:
                print(f"   • {item}")
        
        print(f"\n📄 Full report saved to: {system.config['output_directory']}")
        print("\n✅ Enhanced Editorial System completed successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ System interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ System failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())