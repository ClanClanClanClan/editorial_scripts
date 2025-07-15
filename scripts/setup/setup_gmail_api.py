#!/usr/bin/env python3
"""
Gmail API Setup Script for Editorial Scripts
Automated setup for FS and JOTA email-based journal extraction
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
from datetime import datetime

# Google APIs
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Missing Google API libraries. Installing...")
    os.system("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError


class GmailAPISetup:
    """Gmail API setup and validation for editorial scripts"""
    
    # Required scopes for editorial email analysis
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/gmail.metadata'
    ]
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.credentials_file = self.base_dir / "credentials.json"
        self.token_file = self.base_dir / "token.json"
        self.service = None
        
    def setup_credentials(self):
        """Guide user through OAuth2 credentials setup"""
        print("🔐 Gmail API Credentials Setup")
        print("=" * 50)
        
        if not self.credentials_file.exists():
            print("\n❌ credentials.json not found!")
            print("\n📋 To get credentials.json:")
            print("1. Go to: https://console.cloud.google.com/")
            print("2. Create new project or select existing")
            print("3. Enable Gmail API")
            print("4. Go to 'Credentials' > 'Create Credentials' > 'OAuth client ID'")
            print("5. Application type: 'Desktop application'")
            print("6. Download JSON file as 'credentials.json'")
            print(f"7. Save to: {self.credentials_file}")
            
            response = input("\n📁 Have you saved credentials.json? (y/n): ")
            if response.lower() != 'y':
                print("🛑 Please get credentials.json first")
                return False
                
        if not self.credentials_file.exists():
            print("❌ credentials.json still not found!")
            return False
            
        print("✅ credentials.json found")
        return True
        
    def authenticate(self):
        """Perform OAuth2 authentication flow"""
        print("\n🔓 OAuth2 Authentication")
        print("=" * 30)
        
        creds = None
        
        # Load existing token if available
        if self.token_file.exists():
            print("📱 Loading existing token...")
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
            except Exception as e:
                print(f"⚠️  Error loading token: {e}")
                
        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️  Error refreshing token: {e}")
                creds = None
                
        # Run OAuth flow if no valid credentials
        if not creds or not creds.valid:
            print("🌐 Starting OAuth2 flow...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("✅ Authentication successful!")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
                
        # Save credentials for next time
        with open(self.token_file, 'w') as token:
            token.write(creds.to_json())
            
        # Initialize Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail service initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Gmail service: {e}")
            return False
            
    def test_gmail_access(self):
        """Test basic Gmail API access"""
        print("\n📧 Testing Gmail Access")
        print("=" * 25)
        
        try:
            # Get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'unknown')
            total_messages = profile.get('messagesTotal', 0)
            
            print(f"✅ Connected to: {email}")
            print(f"📊 Total messages: {total_messages:,}")
            
            return True
            
        except Exception as e:
            print(f"❌ Gmail access test failed: {e}")
            return False
            
    def analyze_editorial_emails(self):
        """Analyze and identify journal-specific email patterns"""
        print("\n🔍 Analyzing Editorial Email Patterns")
        print("=" * 40)
        
        # Search patterns for different journals
        journal_patterns = {
            'FS': [
                'from:finance-stochastics',
                'from:springer.com subject:(Finance Stochastics)',
                'subject:"Finance and Stochastics"'
            ],
            'JOTA': [
                'from:editorialmanager.com subject:JOTA',
                'subject:"Journal of Optimization Theory"',
                'subject:"JOTA-D-"'
            ]
        }
        
        results = {}
        
        for journal, patterns in journal_patterns.items():
            print(f"\n📋 Analyzing {journal} emails...")
            
            total_messages = 0
            sample_subjects = []
            
            for pattern in patterns:
                try:
                    # Search for messages
                    response = self.service.users().messages().list(
                        userId='me',
                        q=pattern,
                        maxResults=50
                    ).execute()
                    
                    messages = response.get('messages', [])
                    pattern_count = len(messages)
                    total_messages += pattern_count
                    
                    print(f"  📊 Pattern '{pattern}': {pattern_count} messages")
                    
                    # Get sample subjects
                    for msg in messages[:3]:
                        try:
                            msg_detail = self.service.users().messages().get(
                                userId='me',
                                id=msg['id'],
                                format='metadata',
                                metadataHeaders=['Subject', 'From', 'Date']
                            ).execute()
                            
                            headers = msg_detail.get('payload', {}).get('headers', [])
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'No sender')
                            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No date')
                            
                            sample_subjects.append({
                                'subject': subject,
                                'from': from_email,
                                'date': date
                            })
                            
                        except Exception as e:
                            print(f"    ⚠️  Error getting message details: {e}")
                            
                except Exception as e:
                    print(f"    ❌ Error with pattern '{pattern}': {e}")
                    
            results[journal] = {
                'total_messages': total_messages,
                'sample_subjects': sample_subjects
            }
            
            if total_messages > 0:
                print(f"  ✅ Found {total_messages} {journal} emails")
                for sample in sample_subjects[:2]:
                    print(f"    📄 Sample: {sample['subject'][:60]}...")
            else:
                print(f"  ⚠️  No {journal} emails found")
                
        return results
        
    def test_specific_queries(self):
        """Test specific queries that the scrapers will use"""
        print("\n🔬 Testing Scraper-Specific Queries")
        print("=" * 38)
        
        # Test queries from the actual scrapers
        test_queries = {
            'FS Weekly Overview': 'subject:"Finance and Stochastics - Weekly Overview"',
            'FS Flagged': 'is:starred subject:(Finance Stochastics)',
            'JOTA Weekly Overview': 'subject:"JOTA - Weekly Overview Of Your Assignments"',
            'JOTA Flagged': 'is:starred subject:(JOTA)',
            'JOTA Invitations': 'subject:"Reviewer Invitation for"',
            'JOTA Acceptances': 'subject:"Reviewer has agreed to review"'
        }
        
        for query_name, query in test_queries.items():
            try:
                response = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=10
                ).execute()
                
                count = len(response.get('messages', []))
                print(f"📊 {query_name}: {count} messages")
                
                if count > 0:
                    print(f"  ✅ Query working: '{query}'")
                else:
                    print(f"  ⚠️  No results for: '{query}'")
                    
            except Exception as e:
                print(f"❌ Error testing '{query_name}': {e}")
                
    def create_gmail_service_config(self):
        """Create configuration for the Gmail service integration"""
        print("\n⚙️  Creating Gmail Service Configuration")
        print("=" * 42)
        
        config = {
            "gmail_api": {
                "credentials_file": str(self.credentials_file),
                "token_file": str(self.token_file),
                "scopes": self.SCOPES,
                "setup_date": datetime.now().isoformat(),
                "status": "configured"
            },
            "journals": {
                "FS": {
                    "email_queries": {
                        "weekly_overview": 'subject:"Finance and Stochastics - Weekly Overview"',
                        "flagged": 'is:starred subject:(Finance Stochastics)',
                        "general": 'from:finance-stochastics OR subject:"Finance and Stochastics"'
                    }
                },
                "JOTA": {
                    "email_queries": {
                        "weekly_overview": 'subject:"JOTA - Weekly Overview Of Your Assignments"',
                        "flagged": 'is:starred subject:(JOTA)',
                        "invitations": 'subject:"Reviewer Invitation for"',
                        "acceptances": 'subject:"Reviewer has agreed to review"'
                    }
                }
            }
        }
        
        config_file = self.base_dir / "gmail_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"✅ Configuration saved to: {config_file}")
        return config_file
        
    def run_full_setup(self):
        """Run complete Gmail API setup process"""
        print("🚀 Gmail API Setup for Editorial Scripts")
        print("=" * 50)
        print("This will set up Gmail API access for FS and JOTA email extraction")
        print()
        
        # Step 1: Setup credentials
        if not self.setup_credentials():
            return False
            
        # Step 2: Authenticate
        if not self.authenticate():
            return False
            
        # Step 3: Test access
        if not self.test_gmail_access():
            return False
            
        # Step 4: Analyze patterns
        email_results = self.analyze_editorial_emails()
        
        # Step 5: Test queries
        self.test_specific_queries()
        
        # Step 6: Create configuration
        config_file = self.create_gmail_service_config()
        
        # Final summary
        print("\n🎉 Gmail API Setup Complete!")
        print("=" * 35)
        print(f"✅ Credentials: {self.credentials_file}")
        print(f"✅ Token: {self.token_file}")
        print(f"✅ Configuration: {config_file}")
        print()
        
        # Email analysis summary
        total_fs = email_results.get('FS', {}).get('total_messages', 0)
        total_jota = email_results.get('JOTA', {}).get('total_messages', 0)
        
        print("📊 Email Analysis Summary:")
        print(f"  📧 FS emails found: {total_fs}")
        print(f"  📧 JOTA emails found: {total_jota}")
        
        if total_fs > 0 or total_jota > 0:
            print("\n✅ Ready for email-based extraction!")
        else:
            print("\n⚠️  No editorial emails found - may need to:")
            print("  1. Star relevant emails for flagged queries")
            print("  2. Ensure editorial emails are in this Gmail account")
            print("  3. Check email forwarding/filtering settings")
            
        print("\n🔧 Next steps:")
        print("  1. Test FS scraper: python -m src.infrastructure.scrapers.email_based.fs_scraper")
        print("  2. Test JOTA scraper: python -m src.infrastructure.scrapers.email_based.jota_scraper")
        print("  3. Run unified extraction with email journals enabled")
        
        return True


def main():
    """Main setup function"""
    setup = GmailAPISetup()
    
    try:
        success = setup.run_full_setup()
        if success:
            print("\n🎯 Gmail API setup completed successfully!")
            return 0
        else:
            print("\n❌ Gmail API setup failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())