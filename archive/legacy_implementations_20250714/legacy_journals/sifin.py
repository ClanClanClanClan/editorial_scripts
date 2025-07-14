#!/usr/bin/env python3
"""
SIFIN (SIAM Journal on Financial Mathematics) Extractor
Production-ready implementation with all features
"""

from typing import List, Dict
from datetime import datetime

from journals.siam_base import SIAMJournalExtractor


class SIFIN(SIAMJournalExtractor):
    """SIFIN journal extractor with all production features"""
    
    def __init__(self):
        """Initialize SIFIN extractor"""
        super().__init__('SIFIN')
        # SIFIN has a different folder ID than SICON
        self.folder_id = '1802'  # To be verified with actual SIFIN site
        self.logger.info("Initialized SIFIN extractor with enhanced features")
    
    def post_process(self, manuscripts: List[dict]) -> List[dict]:
        """SIFIN-specific post-processing"""
        # Add any SIFIN-specific logic here
        for manuscript in manuscripts:
            # Calculate days in system
            if manuscript.get('submission_date'):
                submission = datetime.strptime(manuscript['submission_date'], '%Y-%m-%d')
                days_in_system = (datetime.now() - submission).days
                manuscript['days_in_system'] = days_in_system
            
            # Add SIFIN-specific metadata
            manuscript['journal'] = 'SIFIN'
            manuscript['journal_full_name'] = 'SIAM Journal on Financial Mathematics'
            
            # Flag manuscripts needing attention
            manuscript['needs_attention'] = self._check_needs_attention(manuscript)
        
        return manuscripts
    
    def _check_needs_attention(self, manuscript: dict) -> bool:
        """Check if manuscript needs editorial attention"""
        # Check for overdue reviews
        for referee in manuscript.get('referees', []):
            if referee.get('status') == 'Accepted' and referee.get('due_date'):
                try:
                    due_date = datetime.strptime(referee['due_date'], '%Y-%m-%d')
                    if due_date.date() < datetime.now().date():
                        return True
                except:
                    pass
        
        # Check if manuscript has been in system too long
        if manuscript.get('days_in_system', 0) > 150:  # SIFIN might have faster turnaround
            return True
        
        # Check if not enough referees accepted
        accepted_count = sum(
            1 for ref in manuscript.get('referees', [])
            if ref.get('status') == 'Accepted'
        )
        if accepted_count < 2:
            return True
        
        return False
    
    def extract(self) -> Dict:
        """Main extraction method for integration with weekly system"""
        # Run the full extraction workflow
        digest_data = self.run_extraction()
        
        # Format for weekly system compatibility
        return self._format_for_weekly_system(digest_data)
    
    def _format_for_weekly_system(self, digest_data: dict) -> dict:
        """Format extraction results for weekly system"""
        return {
            'journal': 'SIFIN',
            'extraction_time': datetime.now().isoformat(),
            'manuscripts': self.manuscripts_data,
            'changes': digest_data.get('changes', {}),
            'summary': digest_data.get('summary', {}),
            'status': 'success',
            'errors': []
        }
    
    def generate_report(self) -> str:
        """Generate detailed extraction report"""
        report = f"""
SIFIN Extraction Report
{'=' * 50}
Extraction Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Manuscripts: {len(self.manuscripts_data)}

Changes Detected:
- New Manuscripts: {len(self.changes['new_manuscripts'])}
- Status Changes: {len(self.changes['status_changes'])}
- New Reports: {len(self.changes['new_reports'])}
- New Referees: {len(self.changes['new_referees'])}
- Overdue Reviews: {len(self.changes['overdue_reviews'])}
- Approaching Deadlines: {len(self.changes['approaching_deadlines'])}

Manuscript Details:
"""
        
        for ms in self.manuscripts_data:
            report += f"""
{'-' * 40}
ID: {ms['id']}
Title: {ms['title'][:60]}...
Submitted: {ms['submitted']}
Days in System: {ms.get('days_in_system', 'N/A')}
Paper Type: {ms.get('paper_type', 'general')}
Priority: {ms.get('priority', 'normal')}
Needs Attention: {'YES' if ms.get('needs_attention') else 'No'}

Referees ({len(ms['referees'])}):
"""
            
            # Group by status
            by_status = {}
            for ref in ms['referees']:
                status = ref['status']
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(ref)
            
            for status, refs in by_status.items():
                report += f"  {status} ({len(refs)}):\n"
                for ref in refs:
                    email_verified = "✓" if ref.get('email_verification', {}).get('verified') else ""
                    report += f"    - {ref['name']} {email_verified}\n"
                    if ref.get('due_date'):
                        report += f"      Due: {ref['due_date']}\n"
        
        return report


# For backward compatibility
def run_sifin_extraction():
    """Convenience function to run SIFIN extraction"""
    extractor = SIFIN()
    return extractor.extract()


if __name__ == "__main__":
    # Run extraction when called directly
    sifin = SIFIN()
    results = sifin.extract()
    
    # Print summary
    print(f"\nSIFIN Extraction Complete!")
    print(f"Manuscripts: {len(results['manuscripts'])}")
    print(f"Changes: {results['summary']}")
    
    # Generate and save report
    report = sifin.generate_report()
    report_file = sifin.output_dir / 'extraction_report.txt'
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\nDetailed report saved to: {report_file}")
