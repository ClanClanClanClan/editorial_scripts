#!/usr/bin/env python3

import datetime

def test_digest_generation():
    print('=== TESTING DIGEST GENERATION AND EMAIL SENDING ===')

    # Create mock manuscript data similar to what we found in real tests
    mock_manuscripts = [
        {
            'Manuscript #': 'M172838',
            'Title': 'Constrained Mean-Field Control with Singular Control: Existence, Stochastic Maximum Principle and Constrained FBSDE',
            'Contact Author': 'Test Author 1',
            'Current Stage': 'All Referees Assigned',
            'Submission Date': '2024-12-15',
            'Referees': [
                {'Referee Name': 'Juan Li', 'Status': 'Accepted', 'Due Date': '2025-01-15', 'Email': 'juanli@sdu.edu.cn'}
            ],
            'ai_suggestions': {
                'status': 'completed',
                'suggestions': [
                    {'referee_name': 'Expert in Control Theory', 'confidence': 0.8}
                ]
            },
            'journal': 'SICON'
        },
        {
            'Manuscript #': 'MOR-2024-0804',
            'Title': 'Semi-static variance-optimal hedging with self-exciting jumps',
            'Contact Author': 'Giorgia Callegaro',
            'Current Stage': 'Awaiting Reviewer Reports',
            'Submission Date': '2024-06-07',
            'Referees': [
                {'Referee Name': 'Jan Kallsen', 'Status': 'Accepted', 'Due Date': '2024-12-20', 'Email': 'jan.kallsen@uni-kiel.de'},
                {'Referee Name': 'Alessandra Creatarola', 'Status': 'Accepted', 'Due Date': '2024-12-25', 'Email': 'a.creatarola@univ.it'}
            ],
            'journal': 'MOR'
        }
    ]

    # Generate the digest
    print('Generating HTML digest...')
    html_digest = generate_html_digest(mock_manuscripts)

    # Save digest to file for inspection
    with open('test_digest.html', 'w', encoding='utf-8') as f:
        f.write(html_digest)

    print('✓ HTML digest generated and saved to test_digest.html')

    # Test email digest functionality
    print('\nTesting email digest functionality...')
    try:
        subject = f'Editorial Digest - {datetime.datetime.now().strftime("%Y-%m-%d")}'
        print(f'Subject: {subject}')
        print(f'Content length: {len(html_digest)} characters')
        print('✓ Email digest prepared successfully')
        
        # Note: Actual sending would require proper Gmail API setup
        print('(Actual email sending skipped to avoid spam)')
        
    except Exception as e:
        print(f'❌ Email preparation failed: {e}')

    print('\n=== DIGEST SUMMARY ===')
    print(f'📊 Total Manuscripts: {len(mock_manuscripts)}')
    print(f'📚 Journals Covered: {len(set(m.get("journal", "Unknown") for m in mock_manuscripts))}')
    print(f'👥 Total Referees: {sum(len(m.get("Referees", [])) for m in mock_manuscripts)}')
    print(f'🤖 AI Analyses: {len([m for m in mock_manuscripts if "ai_suggestions" in m])}')
    print(f'📄 Digest Size: {len(html_digest)} characters')

    print('\n=== DIGEST GENERATION AND EMAIL TEST COMPLETED ===')

def generate_html_digest(manuscripts):
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_manuscripts = len(manuscripts)
    sicon_count = len([m for m in manuscripts if m.get('journal') == 'SICON'])
    mor_count = len([m for m in manuscripts if m.get('journal') == 'MOR'])
    mf_count = len([m for m in manuscripts if m.get('journal') == 'MF'])
    sifin_count = len([m for m in manuscripts if m.get('journal') == 'SIFIN'])
    total_referees = sum(len(m.get('Referees', [])) for m in manuscripts)
    ai_analyses = len([m for m in manuscripts if 'ai_suggestions' in m])
    
    html = f'''
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .manuscript {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }}
            .referee {{ background: #e8f5e8; padding: 8px; margin: 5px 0; border-radius: 4px; }}
            .ai-analysis {{ background: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 4px; }}
            .stats {{ background: #d4edda; padding: 15px; margin: 20px 0; border-radius: 8px; }}
        </style>
    </head>
    <body>
    <h1>📊 Editorial Digest</h1>
    <p><strong>Generated:</strong> {current_time}</p>
    
    <div class="stats">
        <h2>📈 Summary Statistics</h2>
        <ul>
            <li><strong>Total Manuscripts:</strong> {total_manuscripts}</li>
            <li><strong>SICON Manuscripts:</strong> {sicon_count}</li>
            <li><strong>MOR Manuscripts:</strong> {mor_count}</li>
            <li><strong>MF Manuscripts:</strong> {mf_count}</li>
            <li><strong>SIFIN Manuscripts:</strong> {sifin_count}</li>
            <li><strong>Total Referees:</strong> {total_referees}</li>
            <li><strong>AI Analyses:</strong> {ai_analyses}</li>
        </ul>
    </div>
    '''
    
    # Group manuscripts by journal
    journals = {}
    for manuscript in manuscripts:
        journal = manuscript.get('journal', 'Unknown')
        if journal not in journals:
            journals[journal] = []
        journals[journal].append(manuscript)
    
    for journal, journal_manuscripts in journals.items():
        html += f'<h2>📚 {journal} Journal ({len(journal_manuscripts)} manuscripts)</h2>'
        
        for manuscript in journal_manuscripts:
            ms_id = manuscript.get('Manuscript #', 'N/A')
            title = manuscript.get('Title', 'N/A')
            author = manuscript.get('Contact Author', 'N/A')
            stage = manuscript.get('Current Stage', 'N/A')
            submitted = manuscript.get('Submission Date', 'N/A')
            referees = manuscript.get('Referees', [])
            
            html += f'''
            <div class="manuscript">
                <h3>{ms_id}: {title}</h3>
                <p><strong>Contact Author:</strong> {author}</p>
                <p><strong>Stage:</strong> {stage}</p>
                <p><strong>Submitted:</strong> {submitted}</p>
                
                <h4>👥 Referees ({len(referees)})</h4>
            '''
            
            for referee in referees:
                ref_name = referee.get('Referee Name', 'N/A')
                ref_status = referee.get('Status', 'N/A')
                ref_due = referee.get('Due Date', '')
                ref_email = referee.get('Email', '')
                
                html += f'<div class="referee"><strong>{ref_name}</strong> - {ref_status}'
                
                if ref_due:
                    html += f' | Due: {ref_due}'
                if ref_email:
                    html += f' | Email: {ref_email}'
                    
                html += '</div>'
            
            if 'ai_suggestions' in manuscript:
                ai_data = manuscript['ai_suggestions']
                suggestions = ai_data.get('suggestions', [])
                ai_status = ai_data.get('status', 'N/A')
                
                html += f'''
                <div class="ai-analysis">
                    <h4>🤖 AI Analysis</h4>
                    <p><strong>Status:</strong> {ai_status}</p>
                    <p><strong>Suggestions:</strong> {len(suggestions)} referee recommendations</p>
                </div>
                '''
            
            html += '</div>'
    
    html += '''
    <hr>
    <p><em>Generated by Editorial Management System with AI Integration</em></p>
    </body>
    </html>
    '''
    
    return html

if __name__ == "__main__":
    test_digest_generation()