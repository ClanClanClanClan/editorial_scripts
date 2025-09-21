#!/usr/bin/env python3
"""Generate comprehensive timeline report for all FS manuscripts."""

import json
from datetime import datetime
from fs_extractor import ComprehensiveFSExtractor

def generate_timeline_report():
    """Generate detailed timeline report for all FS manuscripts."""
    print("📊 FS COMPREHENSIVE TIMELINE REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    extractor = ComprehensiveFSExtractor()
    
    # Initialize Gmail
    if not extractor.setup_gmail_service():
        print("❌ Failed to initialize Gmail")
        return
    
    # Run comprehensive extraction
    print("\n🔍 Extracting all manuscripts with detailed timeline...")
    manuscripts = extractor.extract_all()
    
    if not manuscripts:
        print("❌ No manuscripts found")
        return
    
    # Create data structure
    data = {
        'journal': 'fs',
        'journal_name': 'Finance and Stochastics',
        'extraction_time': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'manuscripts_count': len(manuscripts),
        'manuscripts': manuscripts
    }
    
    # Generate report
    report = []
    report.append("=" * 80)
    report.append("FS EDITORIAL TIMELINE REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total manuscripts: {data['manuscripts_count']}")
    report.append("")
    
    # Current manuscripts (starred)
    current_manuscripts = [m for m in manuscripts if m.get('is_current')]
    historical_manuscripts = [m for m in manuscripts if not m.get('is_current')]
    
    report.append(f"Current manuscripts (under review): {len(current_manuscripts)}")
    report.append(f"Historical manuscripts: {len(historical_manuscripts)}")
    report.append("")
    
    # Process current manuscripts first
    if current_manuscripts:
        report.append("=" * 80)
        report.append("CURRENT MANUSCRIPTS (YOUR RESPONSIBILITY)")
        report.append("=" * 80)
        
        for ms in sorted(current_manuscripts, key=lambda x: x['id']):
            report.append("")
            report.append(f"📄 {ms['id']}: {ms['title'][:60]}...")
            report.append("-" * 70)
            report.append(f"Status: {ms['status']}")
            report.append(f"Editor: {ms.get('editor', 'Unknown')}")
            report.append(f"Total emails: {ms.get('total_emails', 0)}")
            
            # Referees
            referees = ms.get('referees', [])
            report.append(f"\n🧑‍⚖️ REFEREES ({len(referees)} total):")
            
            for ref in referees:
                report.append(f"  • {ref['name']}")
                report.append(f"    Email: {ref.get('email', 'Unknown')}")
                report.append(f"    Institution: {ref.get('institution', 'Unknown')}")
                report.append(f"    Response: {ref.get('response', 'Unknown')}")
                
                if ref.get('response') == 'Accepted' and ref.get('response_date'):
                    report.append(f"    Accepted on: {ref['response_date'][:10]}")
                    
                if ref.get('report_submitted'):
                    report.append(f"    ✅ Report submitted: {ref.get('report_date', 'Unknown')[:10]}")
                elif ref.get('response') == 'Accepted':
                    report.append(f"    ⏳ Awaiting report")
                elif ref.get('response') == 'Declined':
                    report.append(f"    ❌ Declined on: {ref.get('response_date', 'Unknown')[:10]}")
            
            # Reports
            reports = ms.get('referee_reports', [])
            if reports:
                report.append(f"\n📎 REPORTS ({len(reports)} submitted):")
                for rpt in reports:
                    report.append(f"  • {rpt['filename']}")
                    report.append(f"    Date: {rpt['date'][:10]}")
                    report.append(f"    Referee: {rpt.get('referee', 'Unknown')}")
            
            # Key timeline events
            timeline = ms.get('timeline', [])
            if timeline:
                report.append(f"\n⏰ KEY EVENTS:")
                
                # Find key events
                submission = next((e for e in timeline if 'submission' in e.get('type', '').lower()), None)
                if submission:
                    report.append(f"  • Submission: {submission['date'][:10]}")
                
                invitations = [e for e in timeline if 'invitation' in e.get('type', '').lower()]
                if invitations:
                    report.append(f"  • Referee invitations sent: {len(invitations)}")
                
                acceptances = [e for e in timeline if e.get('details', {}).get('referee_accepted')]
                if acceptances:
                    for acc in acceptances:
                        report.append(f"  • {acc['details']['referee_accepted']} accepted: {acc['date'][:10]}")
                
                declines = [e for e in timeline if e.get('details', {}).get('referee_declined')]
                if declines:
                    for dec in declines:
                        report.append(f"  • {dec['details']['referee_declined']} declined: {dec['date'][:10]}")
                
                report_submissions = [e for e in timeline if e.get('details', {}).get('report_submitted_by')]
                if report_submissions:
                    for sub in report_submissions:
                        report.append(f"  • Report from {sub['details']['report_submitted_by']}: {sub['date'][:10]}")
            
            report.append("")
    
    # Process historical manuscripts
    if historical_manuscripts:
        report.append("=" * 80)
        report.append("HISTORICAL MANUSCRIPTS")
        report.append("=" * 80)
        
        for ms in sorted(historical_manuscripts, key=lambda x: x['id'], reverse=True):
            report.append("")
            report.append(f"📄 {ms['id']}: {ms['title'][:60]}...")
            report.append(f"   Status: {ms['status']} | Referees: {len(ms.get('referees', []))} | Reports: {len(ms.get('referee_reports', []))}")
    
    # Summary statistics
    report.append("")
    report.append("=" * 80)
    report.append("SUMMARY STATISTICS")
    report.append("=" * 80)
    
    total_referees = sum(len(m.get('referees', [])) for m in manuscripts)
    total_accepted = sum(sum(1 for r in m.get('referees', []) if r.get('response') == 'Accepted') for m in manuscripts)
    total_declined = sum(sum(1 for r in m.get('referees', []) if r.get('response') == 'Declined') for m in manuscripts)
    total_reports = sum(len(m.get('referee_reports', [])) for m in manuscripts)
    
    report.append(f"Total manuscripts tracked: {len(manuscripts)}")
    report.append(f"Total referees contacted: {total_referees}")
    report.append(f"  • Accepted: {total_accepted}")
    report.append(f"  • Declined: {total_declined}")
    report.append(f"  • Pending: {total_referees - total_accepted - total_declined}")
    report.append(f"Total reports received: {total_reports}")
    
    # Referee workload
    referee_counts = {}
    for ms in manuscripts:
        for ref in ms.get('referees', []):
            name = ref['name']
            if name not in referee_counts:
                referee_counts[name] = {'total': 0, 'accepted': 0, 'reports': 0}
            referee_counts[name]['total'] += 1
            if ref.get('response') == 'Accepted':
                referee_counts[name]['accepted'] += 1
            if ref.get('report_submitted'):
                referee_counts[name]['reports'] += 1
    
    if referee_counts:
        report.append("")
        report.append("REFEREE WORKLOAD:")
        for name, stats in sorted(referee_counts.items(), key=lambda x: x[1]['total'], reverse=True):
            report.append(f"  • {name}: {stats['total']} assignments, {stats['accepted']} accepted, {stats['reports']} reports")
    
    # Write report to file
    report_text = "\n".join(report)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"fs_timeline_report_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write(report_text)
    
    print(report_text)
    print("")
    print(f"💾 Report saved to: {report_filename}")
    
    # Also save JSON data
    json_filename = f"fs_timeline_data_{timestamp}.json"
    with open(json_filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"💾 JSON data saved to: {json_filename}")

if __name__ == '__main__':
    generate_timeline_report()