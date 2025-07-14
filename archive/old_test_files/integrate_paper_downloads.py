#!/usr/bin/env python3
"""
Integrate paper download capability into all existing journals.
This script updates journal classes to include paper and referee report downloads.
"""

import os
import re
from pathlib import Path
from typing import List, Dict

class JournalIntegrator:
    """Integrates paper download functionality into journal classes"""
    
    def __init__(self):
        self.journals_dir = Path("journals")
        self.updated_files = []
    
    def add_paper_download_imports(self, file_path: Path) -> bool:
        """Add paper downloader imports to a journal file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if import already exists
            if 'from core.paper_downloader import' in content:
                print(f"Paper downloader already imported in {file_path}")
                return False
            
            # Find the import section
            import_section = []
            lines = content.split('\n')
            
            # Find where to insert the import
            insert_position = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('from core.') or line.strip().startswith('import '):
                    insert_position = i + 1
                elif line.strip() and not line.startswith('#') and not line.startswith('from') and not line.startswith('import'):
                    break
            
            # Insert the import
            lines.insert(insert_position, 'from core.paper_downloader import get_paper_downloader')
            
            # Write back the file
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"Added paper downloader import to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error adding imports to {file_path}: {e}")
            return False
    
    def add_paper_download_to_init(self, file_path: Path) -> bool:
        """Add paper downloader initialization to journal __init__"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if already added
            if 'self.paper_downloader' in content:
                print(f"Paper downloader already initialized in {file_path}")
                return False
            
            # Find the __init__ method
            init_pattern = r'def __init__\(self[^)]*\):'
            init_match = re.search(init_pattern, content)
            
            if not init_match:
                print(f"No __init__ method found in {file_path}")
                return False
            
            # Find the end of the __init__ method
            lines = content.split('\n')
            init_line = None
            
            for i, line in enumerate(lines):
                if re.match(r'\s*def __init__\(self', line):
                    init_line = i
                    break
            
            if init_line is None:
                return False
            
            # Find a good place to insert the paper downloader initialization
            insert_line = init_line + 1
            while insert_line < len(lines) and (lines[insert_line].strip().startswith('super(') or 
                                              lines[insert_line].strip().startswith('self.') or
                                              lines[insert_line].strip() == ''):
                insert_line += 1
            
            # Insert the paper downloader initialization
            indent = '        '  # Assume 8 spaces for method body
            lines.insert(insert_line, f'{indent}self.paper_downloader = get_paper_downloader()')
            
            # Write back the file
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"Added paper downloader initialization to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error adding initialization to {file_path}: {e}")
            return False
    
    def add_download_method(self, file_path: Path) -> bool:
        """Add download_manuscripts method to journal class"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if method already exists
            if 'def download_manuscripts' in content:
                print(f"Download method already exists in {file_path}")
                return False
            
            # Get the journal class name
            class_match = re.search(r'class (\w+)\(', content)
            if not class_match:
                print(f"No class found in {file_path}")
                return False
            
            class_name = class_match.group(1)
            journal_name = class_name.replace('Journal', '').upper()
            
            # Create the download method
            download_method = f'''
    def download_manuscripts(self, manuscripts: List[Dict]) -> List[Dict]:
        """Download papers and referee reports for manuscripts"""
        if not hasattr(self, 'paper_downloader'):
            self.paper_downloader = get_paper_downloader()
        
        enhanced_manuscripts = []
        
        for manuscript in manuscripts:
            enhanced_ms = manuscript.copy()
            enhanced_ms['downloads'] = {{
                'paper': None,
                'reports': []
            }}
            
            try:
                manuscript_id = manuscript.get('Manuscript #', manuscript.get('manuscript_id', ''))
                title = manuscript.get('Title', manuscript.get('title', ''))
                
                if manuscript_id and title:
                    # Try to find paper download links
                    paper_links = self.paper_downloader.find_paper_links(self.driver, "{journal_name}")
                    
                    for link in paper_links:
                        if link['type'] == 'href':
                            paper_path = self.paper_downloader.download_paper(
                                manuscript_id, title, link['url'], "{journal_name}", self.driver
                            )
                            if paper_path:
                                enhanced_ms['downloads']['paper'] = str(paper_path)
                                break
                    
                    # Try to find referee report links
                    report_links = self.paper_downloader.find_report_links(self.driver, "{journal_name}")
                    
                    for link in report_links:
                        if link['type'] == 'href':
                            report_path = self.paper_downloader.download_referee_report(
                                manuscript_id, link['text'], link['url'], "{journal_name}", self.driver
                            )
                            if report_path:
                                enhanced_ms['downloads']['reports'].append(str(report_path))
                
            except Exception as e:
                print(f"Error downloading for manuscript {{manuscript_id}}: {{e}}")
            
            enhanced_manuscripts.append(enhanced_ms)
        
        return enhanced_manuscripts
'''
            
            # Append the method to the end of the class
            content += download_method
            
            # Write back the file
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"Added download method to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error adding download method to {file_path}: {e}")
            return False
    
    def update_scrape_method(self, file_path: Path) -> bool:
        """Update scrape_manuscripts_and_emails to include downloads"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if already updated
            if 'download_manuscripts' in content and 'enhanced_manuscripts' in content:
                print(f"Scrape method already updated in {file_path}")
                return False
            
            # Find the scrape_manuscripts_and_emails method
            scrape_pattern = r'def scrape_manuscripts_and_emails\(self\):'
            scrape_match = re.search(scrape_pattern, content)
            
            if not scrape_match:
                print(f"No scrape_manuscripts_and_emails method found in {file_path}")
                return False
            
            # Find the return statement
            lines = content.split('\n')
            return_lines = []
            
            for i, line in enumerate(lines):
                if 'return ' in line and ('manuscripts' in line or 'ms_' in line or '[]' in line):
                    return_lines.append(i)
            
            if not return_lines:
                print(f"No return statement found in scrape method in {file_path}")
                return False
            
            # Update the last return statement
            last_return = return_lines[-1]
            original_return = lines[last_return]
            
            # Extract the variable being returned
            return_var = original_return.strip().replace('return ', '')
            
            # Replace the return statement
            indent = '        '  # Assume 8 spaces
            lines[last_return] = f'{indent}# Download papers and reports'
            lines.insert(last_return + 1, f'{indent}enhanced_manuscripts = self.download_manuscripts({return_var})')
            lines.insert(last_return + 2, f'{indent}return enhanced_manuscripts')
            
            # Write back the file
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"Updated scrape method in {file_path}")
            return True
            
        except Exception as e:
            print(f"Error updating scrape method in {file_path}: {e}")
            return False
    
    def integrate_journal(self, journal_file: Path) -> bool:
        """Integrate paper download capability into a journal file"""
        print(f"\\nIntegrating paper downloads into {journal_file}")
        
        success = True
        
        # Add imports
        if not self.add_paper_download_imports(journal_file):
            success = False
        
        # Add initialization
        if not self.add_paper_download_to_init(journal_file):
            success = False
        
        # Add download method
        if not self.add_download_method(journal_file):
            success = False
        
        # Update scrape method
        if not self.update_scrape_method(journal_file):
            success = False
        
        if success:
            self.updated_files.append(journal_file)
        
        return success
    
    def integrate_all_journals(self) -> List[Path]:
        """Integrate paper download capability into all journal files"""
        journal_files = list(self.journals_dir.glob('*.py'))
        
        # Filter out __init__.py and other non-journal files
        journal_files = [f for f in journal_files if f.name != '__init__.py' and 
                        f.name not in ['base.py', 'enhanced.py', 'hybrid.py']]
        
        print(f"Found {len(journal_files)} journal files to integrate")
        
        for journal_file in journal_files:
            try:
                self.integrate_journal(journal_file)
            except Exception as e:
                print(f"Error integrating {journal_file}: {e}")
        
        return self.updated_files
    
    def create_backup(self):
        """Create backups of journal files before modification"""
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        journal_files = list(self.journals_dir.glob('*.py'))
        
        for journal_file in journal_files:
            backup_file = backup_dir / f"{journal_file.name}.backup"
            try:
                import shutil
                shutil.copy2(journal_file, backup_file)
                print(f"Created backup: {backup_file}")
            except Exception as e:
                print(f"Error creating backup for {journal_file}: {e}")

def main():
    integrator = JournalIntegrator()
    
    # Create backups first
    print("Creating backups...")
    integrator.create_backup()
    
    # Integrate all journals
    print("\\nIntegrating paper download capability...")
    updated_files = integrator.integrate_all_journals()
    
    print(f"\\nIntegration complete! Updated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")
    
    print("\\nNote: Please review the changes and test the updated journal classes.")

if __name__ == "__main__":
    main()