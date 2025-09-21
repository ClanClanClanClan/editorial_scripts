#!/usr/bin/env python3
"""
Extraction Monitoring Dashboard
===============================

Simple monitoring dashboard for editorial extractors.
Focuses on reliability and basic metrics for working extractors.

Features:
- Shows recent extraction results
- Basic success/failure metrics
- Simple health monitoring
- Export to CSV for further analysis

Usage:
    python3 monitor_extractions.py --dashboard
    python3 monitor_extractions.py --health
    python3 monitor_extractions.py --export
"""

import os
import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics


class ExtractionMonitor:
    """Simple monitoring for extraction results."""
    
    def __init__(self, results_dir: str = "results"):
        """Initialize monitor.
        
        Args:
            results_dir: Directory containing extraction results
        """
        self.results_dir = Path(results_dir)
        
    def get_all_results(self) -> List[Dict]:
        """Get all extraction results from all journals."""
        results = []
        
        if not self.results_dir.exists():
            return results
            
        # Search all journal subdirectories
        for journal_dir in self.results_dir.iterdir():
            if journal_dir.is_dir():
                for results_file in journal_dir.glob("*_extraction_*.json"):
                    try:
                        with open(results_file) as f:
                            data = json.load(f)
                            data['file_path'] = str(results_file)
                            data['journal_id'] = journal_dir.name
                            results.append(data)
                    except Exception as e:
                        print(f"⚠️ Could not load {results_file}: {e}")
        
        # Sort by extraction time
        results.sort(key=lambda x: x.get('extraction_time', ''), reverse=True)
        return results
    
    def calculate_health_metrics(self, days: int = 7) -> Dict:
        """Calculate health metrics for recent extractions.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Health metrics dictionary
        """
        results = self.get_all_results()
        
        # Filter to recent results
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_results = []
        
        for result in results:
            try:
                extraction_time = datetime.strptime(result['extraction_time'], '%Y%m%d_%H%M%S')
                if extraction_time >= cutoff_date:
                    recent_results.append(result)
            except:
                continue
        
        # Calculate metrics
        metrics = {
            'period_days': days,
            'total_extractions': len(recent_results),
            'journals_active': len(set(r.get('journal_id', '') for r in recent_results)),
            'total_manuscripts': sum(r.get('manuscripts_count', 0) for r in recent_results),
            'avg_manuscripts_per_extraction': 0,
            'avg_duration_seconds': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'success_rate': 0.0,
            'journal_breakdown': {},
            'daily_counts': {}
        }
        
        if recent_results:
            manuscript_counts = [r.get('manuscripts_count', 0) for r in recent_results]
            durations = [r.get('duration_seconds', 0) for r in recent_results if r.get('duration_seconds', 0) > 0]
            
            metrics['avg_manuscripts_per_extraction'] = statistics.mean(manuscript_counts)
            if durations:
                metrics['avg_duration_seconds'] = statistics.mean(durations)
            
            # Success/failure analysis
            for result in recent_results:
                if result.get('manuscripts_count', 0) > 0:
                    metrics['successful_extractions'] += 1
                else:
                    metrics['failed_extractions'] += 1
                    
                # Journal breakdown
                journal = result.get('journal_id', 'unknown')
                if journal not in metrics['journal_breakdown']:
                    metrics['journal_breakdown'][journal] = {
                        'extractions': 0,
                        'manuscripts': 0,
                        'avg_duration': 0,
                        'success_rate': 0
                    }
                
                metrics['journal_breakdown'][journal]['extractions'] += 1
                metrics['journal_breakdown'][journal]['manuscripts'] += result.get('manuscripts_count', 0)
                
                # Daily breakdown
                try:
                    date_str = result['extraction_time'][:8]  # YYYYMMDD
                    if date_str not in metrics['daily_counts']:
                        metrics['daily_counts'][date_str] = 0
                    metrics['daily_counts'][date_str] += result.get('manuscripts_count', 0)
                except:
                    continue
            
            # Calculate success rate
            total_attempts = metrics['successful_extractions'] + metrics['failed_extractions']
            if total_attempts > 0:
                metrics['success_rate'] = metrics['successful_extractions'] / total_attempts
                
            # Calculate per-journal metrics
            for journal_data in metrics['journal_breakdown'].values():
                journal_results = [r for r in recent_results if r.get('journal_id') == journal]
                if journal_results:
                    durations = [r.get('duration_seconds', 0) for r in journal_results if r.get('duration_seconds', 0) > 0]
                    if durations:
                        journal_data['avg_duration'] = statistics.mean(durations)
                    
                    successes = sum(1 for r in journal_results if r.get('manuscripts_count', 0) > 0)
                    journal_data['success_rate'] = successes / len(journal_results)
        
        return metrics
    
    def show_dashboard(self, days: int = 7):
        """Show monitoring dashboard.
        
        Args:
            days: Number of days to analyze
        """
        print(f"\n📊 EXTRACTION MONITORING DASHBOARD")
        print(f"{'=' * 60}")
        print(f"Period: Last {days} days")
        print()
        
        # Get health metrics
        metrics = self.calculate_health_metrics(days)
        
        # Overall summary
        print(f"📈 OVERALL METRICS")
        print(f"{'-' * 30}")
        print(f"Total Extractions: {metrics['total_extractions']}")
        print(f"Active Journals: {metrics['journals_active']}")
        print(f"Total Manuscripts: {metrics['total_manuscripts']}")
        print(f"Success Rate: {metrics['success_rate']*100:.1f}%")
        print(f"Avg Manuscripts/Extraction: {metrics['avg_manuscripts_per_extraction']:.1f}")
        print(f"Avg Duration: {metrics['avg_duration_seconds']:.1f}s")
        print()
        
        # Journal breakdown
        if metrics['journal_breakdown']:
            print(f"📋 JOURNAL BREAKDOWN")
            print(f"{'-' * 30}")
            print(f"{'Journal':<8} | {'Runs':<4} | {'Papers':<6} | {'Success':<7} | {'Avg Time':<8}")
            print(f"{'-' * 50}")
            
            for journal, data in metrics['journal_breakdown'].items():
                success_pct = data['success_rate'] * 100
                avg_time = data['avg_duration']
                
                print(f"{journal.upper():<8} | {data['extractions']:<4} | {data['manuscripts']:<6} | "
                      f"{success_pct:>6.1f}% | {avg_time:>7.1f}s")
            print()
        
        # Recent results
        recent_results = self.get_all_results()[:10]  # Last 10
        
        if recent_results:
            print(f"🕐 RECENT EXTRACTIONS")
            print(f"{'-' * 30}")
            print(f"{'Time':<15} | {'Journal':<6} | {'Papers':<6} | {'Duration':<8} | {'Status'}")
            print(f"{'-' * 60}")
            
            for result in recent_results:
                time_str = result.get('extraction_time', 'unknown')[:13]  # YYYYMMDD_HHMM
                journal = result.get('journal_id', 'unknown').upper()
                papers = result.get('manuscripts_count', 0)
                duration = result.get('duration_seconds', 0)
                status = "✅ OK" if papers > 0 else "❌ FAIL"
                
                print(f"{time_str:<15} | {journal:<6} | {papers:<6} | {duration:>7.1f}s | {status}")
        print()
        
        # Daily trend (last 7 days)
        if metrics['daily_counts']:
            print(f"📅 DAILY MANUSCRIPT COUNTS")
            print(f"{'-' * 30}")
            
            # Get last 7 days
            dates = sorted(metrics['daily_counts'].keys(), reverse=True)[:7]
            for date in dates:
                count = metrics['daily_counts'][date]
                formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                print(f"{formatted_date}: {count:3} manuscripts")
        print()
    
    def check_health(self) -> Tuple[bool, List[str]]:
        """Check system health.
        
        Returns:
            Tuple of (is_healthy, list_of_issues)
        """
        issues = []
        
        # Check if results directory exists
        if not self.results_dir.exists():
            issues.append("Results directory does not exist")
            return False, issues
        
        # Check recent activity
        metrics = self.calculate_health_metrics(days=1)  # Last 24 hours
        
        if metrics['total_extractions'] == 0:
            issues.append("No extractions in the last 24 hours")
        
        if metrics['success_rate'] < 0.5:  # Less than 50% success
            issues.append(f"Low success rate: {metrics['success_rate']*100:.1f}%")
        
        # Check for working journals
        working_journals = ['mf', 'mor']
        active_journals = list(metrics['journal_breakdown'].keys())
        
        for journal in working_journals:
            if journal not in active_journals:
                issues.append(f"Journal {journal.upper()} has not run recently")
        
        # Check average duration (flag if > 10 minutes)
        if metrics['avg_duration_seconds'] > 600:
            issues.append(f"Extractions taking too long: {metrics['avg_duration_seconds']:.1f}s avg")
        
        is_healthy = len(issues) == 0
        return is_healthy, issues
    
    def export_to_csv(self, output_file: str = None):
        """Export results to CSV for analysis.
        
        Args:
            output_file: Output CSV file path
        """
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"extraction_results_{timestamp}.csv"
        
        results = self.get_all_results()
        
        if not results:
            print("No results to export")
            return
        
        # CSV headers
        headers = [
            'extraction_time', 'journal', 'journal_name', 'manuscripts_count',
            'duration_seconds', 'success', 'file_path'
        ]
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for result in results:
                row = [
                    result.get('extraction_time', ''),
                    result.get('journal', ''),
                    result.get('journal_name', ''),
                    result.get('manuscripts_count', 0),
                    result.get('duration_seconds', 0),
                    1 if result.get('manuscripts_count', 0) > 0 else 0,
                    result.get('file_path', '')
                ]
                writer.writerow(row)
        
        print(f"📊 Exported {len(results)} results to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extraction Monitoring Dashboard")
    parser.add_argument('--dashboard', '-d', action='store_true',
                       help="Show monitoring dashboard")
    parser.add_argument('--health', action='store_true',
                       help="Check system health")
    parser.add_argument('--export', '-e', action='store_true',
                       help="Export results to CSV")
    parser.add_argument('--days', type=int, default=7,
                       help="Number of days to analyze (default: 7)")
    parser.add_argument('--results-dir', default="results",
                       help="Results directory (default: results)")
    parser.add_argument('--output', '-o',
                       help="Output CSV file (for --export)")
    
    args = parser.parse_args()
    
    monitor = ExtractionMonitor(args.results_dir)
    
    if args.dashboard:
        monitor.show_dashboard(args.days)
        
    elif args.health:
        print("\n🏥 EXTRACTION SYSTEM HEALTH CHECK")
        print("=" * 40)
        
        is_healthy, issues = monitor.check_health()
        
        if is_healthy:
            print("✅ System is healthy")
        else:
            print("⚠️ Issues detected:")
            for issue in issues:
                print(f"  • {issue}")
        print()
        
    elif args.export:
        monitor.export_to_csv(args.output)
        
    else:
        # Show quick status
        results = monitor.get_all_results()
        if results:
            latest = results[0]
            print(f"\n📊 QUICK STATUS")
            print(f"Latest extraction: {latest.get('journal_id', 'unknown').upper()} "
                  f"({latest.get('extraction_time', 'unknown')})")
            print(f"Total historical results: {len(results)}")
        else:
            print("\n📊 No extraction results found")
            print("Run some extractions first: python3 run_extractors.py --all")
        
        parser.print_help()


if __name__ == "__main__":
    main()