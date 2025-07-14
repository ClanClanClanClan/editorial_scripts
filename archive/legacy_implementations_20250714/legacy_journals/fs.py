import os
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any
from core.base import JournalBase
from core.email_utils import fetch_starred_emails

import base64
import pickle
from core.paper_downloader import get_paper_downloader
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Import enhanced PDF parser
try:
    from pdf_parser import UltraEnhancedPDFParser
    HAS_ENHANCED_PDF_PARSER = True
except ImportError:
    HAS_ENHANCED_PDF_PARSER = False

# Import Grobid client
try:
    from grobid_client.grobid_client import GrobidClient
    HAS_GROBID = True
except ImportError:
    HAS_GROBID = False

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

KNOWN_EDITORS = {
    "touzi@ceremade.dauphine.fr", "nt2635@nyu.edu", "cvitanic@caltech.edu",
    "finasto@math.ethz.ch", "martin.schweizer@math.ethz.ch", "peter.tankov@ensae.fr",
    "fukasawa.m.es@osaka-u.ac.jp", "aschied@uwaterloo.ca", "paolo.guasoni@dcu.ie"
}

KNOWN_EDITOR_NAMES = {
    "nizar touzi", "touzi", "jerome cvitanic", "cvitanic", 
    "martin schweizer", "schweizer", "peter tankov", "tankov",
    "masaaki fukasawa", "fukasawa", "alexander schied", "schied",
    "paolo guasoni", "guasoni", "stefan weber", "weber"
}

# Common referee names that are often misidentified as authors
KNOWN_REFEREE_NAMES = {
    "yufei zhang", "zhang", "xuefeng gao", "gao"
}

USERNAME_ALIASES = {
    'gxf1240': 'xfgao',  # group gxf1240@gmail.com and xfgao@se.cuhk.edu.hk
    # Add more mappings here if you encounter similar cases
}

def gmail_api_authenticate():
    creds = None
    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def gmail_search_messages(service, query, max_results=100):
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    full_messages = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        full_messages.append(msg_data)
    return full_messages

def extract_pdf_attachments_from_gmail_message(service, message, download_dir="attachments"):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    attachments = []
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    for part in parts:
        filename = part.get('filename')
        body = part.get('body', {})
        if filename and filename.lower().endswith('.pdf'):
            att_id = body.get('attachmentId')
            if att_id:
                att = service.users().messages().attachments().get(
                    userId='me', messageId=message['id'], id=att_id).execute()
                data = att.get('data')
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                filepath = os.path.join(download_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                attachments.append(filepath)
    return attachments

def canonicalize_fs_id(subject):
    if not subject:
        return None
    m = re.search(r'FS[\s\-:]*([0-9][0-9\s\-]+)', subject, re.IGNORECASE)
    if not m:
        return None
    digits = ''.join(re.findall(r'\d', m.group(1)))
    if len(digits) < 5:
        return None
    return digits.zfill(6)

def display_fs_id(fs_id_str):
    fs_id_str = fs_id_str.zfill(6)
    return f"FS-{fs_id_str[:2]}-{fs_id_str[2:4]}-{fs_id_str[4:6]}"

def extract_body_from_gmail_message(payload):
    """Extract plain text body from Gmail message payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
            elif part.get('mimeType') == 'multipart/alternative':
                # Recurse into multipart
                body = extract_body_from_gmail_message(part)
                if body:
                    break
    elif payload.get('body', {}).get('data'):
        # Simple message with body directly in payload
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    return body

def extract_name_from_header(header):
    if not header:
        return ""
    name_match = re.match(r'"?([^"<]+)"?\s*<.*>', header)
    if name_match:
        name = name_match.group(1)
        if "," in name:
            last, first = [part.strip() for part in name.split(",", 1)]
            return f"{first} {last}"
        return name
    if '<' in header and '>' in header:
        header = header.split('<')[1].split('>')[0]
    if '@' in header:
        parts = header.split('@')[0]
        parts = re.split(r'[._]', parts)
        if len(parts) > 1:
            return " ".join(str(word).capitalize() for word in parts)
        else:
            return str(parts).capitalize()
    return str(header)

def extract_email_only(header):
    match = re.search(r'<([^>]+)>', header)
    if match:
        return match.group(1).strip()
    if '@' in header:
        return header.strip().replace('"', '').replace("'", "")
    return ""

def plausible_human_name(s):
    s = s.strip()
    if not s or len(s) < 5: return False
    if re.search(r'\d', s): return False
    words = s.split()
    if len(words) < 2 or len(words) > 5: return False
    if len(words) == 1 and words[0].isupper(): return False
    if any(len(w) > 15 for w in words): return False
    badwords = set(['abstract', 'keywords', 'introduction', 'theorem', 'proof', 'section', 'university', 'department', 'optimization', 'portfolio', 'regularized', 'variance', 'mean', 'jumps', 'email'])
    if any(w.lower() in badwords for w in words): return False
    upperlike = [w for w in words if w and w[0].isupper()]
    if len(upperlike) < 1: return False
    return True

def titlecase_human_name(s):
    return " ".join([w.capitalize() for w in s.strip().split()])

def improve_sentence_case(title):
    """Convert title to proper sentence case - only first word capitalized, rest lowercase except proper nouns"""
    if not title:
        return title
    
    # First clean up the title
    title = title.strip()
    
    # Split into words
    words = title.split()
    if not words:
        return title
    
    # Convert to sentence case: first word capitalized, rest lowercase
    result = []
    for i, word in enumerate(words):
        if i == 0:
            # First word: capitalize first letter, lowercase the rest
            result.append(word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper())
        else:
            # All other words: lowercase (except proper nouns which we'll handle separately)
            result.append(word.lower())
    
    return " ".join(result)

def ocr_pdf_first_author(pdf_path):
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        text = pytesseract.image_to_string(images[0])
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            clean_line = re.sub(r'\d+', ' ', line)
            if plausible_human_name(clean_line):
                return titlecase_human_name(clean_line)
        return ""
    except Exception:
        return ""

def parse_pdf_title_author_grobid(pdf_path):
    """Parse PDF using Grobid service"""
    if not HAS_GROBID:
        return None, None
    
    try:
        print(f"[PDF_DEBUG] Attempting Grobid parsing for {pdf_path}")
        
        # Initialize Grobid client
        client = GrobidClient(grobid_server="http://localhost:8070")
        
        # Create a temporary output directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Process header (title and authors)
            client.process("processHeaderDocument", pdf_path, temp_dir, consolidate_citations=False)
            
            # Look for the generated XML file
            import os
            xml_files = [f for f in os.listdir(temp_dir) if f.endswith('.xml')]
            if not xml_files:
                print(f"[PDF_DEBUG] No XML output from Grobid")
                return None, None
            
            xml_path = os.path.join(temp_dir, xml_files[0])
            
            # Parse the XML to extract title and authors
            from xml.etree import ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Define namespace
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            # Extract title
            title_elem = root.find('.//tei:title[@type="main"]', ns)
            title = title_elem.text if title_elem is not None else ""
            
            # Extract authors
            authors = []
            author_elems = root.findall('.//tei:author', ns)
            for author_elem in author_elems:
                forename = author_elem.find('.//tei:forename', ns)
                surname = author_elem.find('.//tei:surname', ns)
                if forename is not None and surname is not None:
                    authors.append(f"{forename.text} {surname.text}")
            
            first_author = authors[0] if authors else ""
            
            print(f"[PDF_DEBUG] Grobid extracted - Title: {title}, Authors: {first_author}")
            
            if title and first_author:
                # Clean up title and ensure proper sentence case
                title = title.strip()
                title = improve_sentence_case(title)
                return title, first_author
            
    except Exception as e:
        print(f"[PDF_DEBUG] Grobid parsing failed: {e}")
    
    return None, None

def parse_pdf_title_author_enhanced(pdf_path):
    """Enhanced PDF parsing using multiple methods"""
    # Try Grobid first if available
    if HAS_GROBID:
        grobid_title, grobid_author = parse_pdf_title_author_grobid(pdf_path)
        if grobid_title and grobid_author:
            return grobid_title, grobid_author
    
    # Try enhanced parser
    if HAS_ENHANCED_PDF_PARSER:
        try:
            parser = UltraEnhancedPDFParser()
            metadata = parser.extract_metadata(pdf_path)
            
            title = metadata.title if metadata.title != "Unknown Title" else ""
            authors = metadata.authors if metadata.authors != "Unknown" else ""
            
            print(f"[PDF_DEBUG] Enhanced parser - Title: {title}, Authors: {authors}")
            
            # Clean up title and ensure proper sentence case
            if title:
                title = title.strip()
                title = improve_sentence_case(title)
            
            # Extract first author and ensure it's not an editor
            if authors:
                first_author = extract_first_author(authors)
                # Check if this is actually an editor (common mistake)
                if is_likely_editor(first_author):
                    print(f"[PDF_DEBUG] Detected editor name '{first_author}', searching for real author")
                    # Try to find real author in the text
                    real_author = find_real_author_in_pdf_text(pdf_path)
                    if real_author:
                        first_author = real_author
                        print(f"[PDF_DEBUG] Found real author: {first_author}")
                return title, first_author
            
            return title, ""
            
        except Exception as e:
            print(f"[PDF_DEBUG] Enhanced PDF parsing failed: {e}")
            # Fall back to original method
            pass
    
    # Fallback to original method
    print(f"[PDF_DEBUG] Using fallback PDF parser for {pdf_path}")
    return parse_pdf_title_author_fallback(pdf_path)

def parse_pdf_title_author_fallback(pdf_path):
    """Original PDF parsing method as fallback"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages[:2]):
            t = page.extract_text()
            text += (t or "") + "\n"
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        print(f"[PDF_DEBUG] First 10 lines of PDF text:")
        for i, line in enumerate(lines[:10]):
            print(f"[PDF_DEBUG] Line {i}: {line}")
        title_lines = []
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check if this looks like a title line (uppercase or title case, not author-like)
            if (line_clean.isupper() or (line_clean[0].isupper() and not re.search(r"[\d@]", line_clean) and len(line_clean) > 10)):
                # Don't include lines that look like author names
                if not plausible_human_name(line_clean):
                    if len(title_lines) < 5:  # Allow up to 5 lines for title
                        title_lines.append(line_clean)
                    continue
                else:
                    # If we encounter an author name, stop collecting title lines
                    break
            else:
                break
        
        # Join title lines and clean up
        title = " ".join(title_lines).replace("  ", " ").strip(" :;")
        
        # Handle all-caps titles by converting to proper sentence case
        if title.isupper():
            title = improve_sentence_case(title)
        elif title:
            # Ensure proper sentence case even for mixed case titles
            title = improve_sentence_case(title)
        author_line = ""
        for line in lines[len(title_lines):len(title_lines)+5]:
            if line:
                candidate = re.sub(r'\d+', ' ', line)
                split_auth = re.split(r'\band\b', candidate, flags=re.IGNORECASE)
                first_candidate = split_auth[0].strip()
                first_candidate = re.sub(r'[,;:]+$', '', first_candidate)
                first_candidate = re.sub(r'\s+', ' ', first_candidate)
                if plausible_human_name(first_candidate) and not is_likely_editor(first_candidate):
                    author_line = first_candidate
                    break
        if not author_line:
            for line in lines[:40]:
                candidate = re.sub(r'\d+', ' ', line)
                split_auth = re.split(r'\band\b', candidate, flags=re.IGNORECASE)
                first_candidate = split_auth[0].strip()
                first_candidate = re.sub(r'[,;:]+$', '', first_candidate)
                first_candidate = re.sub(r'\s+', ' ', first_candidate)
                if plausible_human_name(first_candidate) and not is_likely_editor(first_candidate):
                    author_line = first_candidate
                    break
        if not author_line:
            author_line = ocr_pdf_first_author(pdf_path)
        author_line = titlecase_human_name(author_line)
        if not title:
            title = "PDF_NOT_PARSED"
        return title, author_line
    except Exception:
        return "PDF_NOT_PARSED", ""

def extract_first_author(authors_string):
    """Extract the first author from an authors string"""
    if not authors_string:
        return ""
    
    # Split on common separators
    separators = [' and ', ' & ', '; ', ', ']
    first_author = authors_string
    
    for sep in separators:
        if sep in authors_string:
            first_author = authors_string.split(sep)[0].strip()
            break
    
    return titlecase_human_name(first_author)

def is_likely_editor(name):
    """Check if a name is likely an editor rather than paper author"""
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # Check against known editors
    for editor_name in KNOWN_EDITOR_NAMES:
        if editor_name in name_lower or name_lower in editor_name:
            return True
    
    # Check for common editor titles
    editor_titles = ['editor', 'prof.', 'professor', 'dr.', 'director']
    for title in editor_titles:
        if title in name_lower:
            return True
    
    return False

def is_likely_referee(name, referee_emails):
    """Check if a name is likely a referee rather than paper author"""
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # Check against known referee names
    for referee_name in KNOWN_REFEREE_NAMES:
        if referee_name in name_lower or name_lower in referee_name:
            return True
    
    # Check if name matches any referee email username
    for ref_email in referee_emails:
        if '@' in ref_email:
            username = ref_email.split('@')[0].lower()
            username_parts = re.split(r'[._]', username)
            
            # Check if any part of the username appears in the name
            for part in username_parts:
                if len(part) > 2 and part in name_lower.replace(' ', ''):
                    return True
    
    return False

def find_real_author_in_pdf_text(pdf_path, referee_emails=None):
    """Try to find the real paper author when editor was incorrectly identified"""
    if referee_emails is None:
        referee_emails = set()
    
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages[:3]):  # Check first 3 pages
            t = page.extract_text()
            text += (t or "") + "\n"
        
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Look for author patterns after title but before abstract
        for i, line in enumerate(lines[3:30], 3):  # Skip first few lines (title area)
            if line.lower().startswith('abstract'):
                break
                
            # Look for name patterns
            name_candidates = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
            for candidate in name_candidates:
                if (plausible_human_name(candidate) and 
                    not is_likely_editor(candidate) and
                    not is_likely_referee(candidate, referee_emails) and
                    len(candidate.split()) == 2):  # Prefer simple "First Last" format
                    return titlecase_human_name(candidate)
        
    except Exception:
        pass
    
    return ""

def parse_email_date(date_str):
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        if not dt.tzinfo:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def is_real_referee(email, name):
    if not email:
        return False
    if email.lower() in KNOWN_EDITORS:
        return False
    if "dylansmb@gmail.com" in email.lower() or "dylan.possamai@math.ethz.ch" in email.lower():
        return False
    return True

def pick_best_name(names_set, uname):
    """Pick the best name from a set, handling email aliases properly"""
    def score(n):
        n = n or ""
        if not n.strip(): return -100
        if n.startswith("["): return -10
        
        # Penalty for single names that look like usernames
        words = n.strip().split()
        if len(words) == 1 and (n.lower() == uname.lower() or len(n) < 3):
            return -50
        
        # High score for proper names
        if len(words) >= 2 and all(w[0].isupper() for w in words if w): 
            return 100 + len(words)
        if len(words) >= 2: 
            return 80 + len(words)
        
        # Lower score for single names
        return len(words) * 10
    
    candidates = [n for n in names_set if plausible_human_name(n)]
    if candidates:
        best = max(candidates, key=score)
        # If the best name is still just a username, try to construct from email
        if best.lower() == uname.lower() and len(best.split()) == 1:
            constructed_name = construct_name_from_username(uname)
            if constructed_name:
                return constructed_name
        return titlecase_human_name(best)
    
    # Fallback: try to construct name from username
    constructed_name = construct_name_from_username(uname)
    if constructed_name:
        return constructed_name
    
    return titlecase_human_name(uname)

def construct_name_from_username(username):
    """Try to construct a proper name from a username"""
    if not username:
        return ""
    
    # Handle common patterns in usernames
    username = username.lower()
    
    # Pattern: firstlast or first.last or first_last
    if '.' in username:
        parts = username.split('.')
    elif '_' in username:
        parts = username.split('_')
    else:
        # Try to split camelCase or identify common name patterns
        # For now, just capitalize the username
        parts = [username]
    
    # Capitalize each part
    capitalized_parts = []
    for part in parts:
        if len(part) > 1:
            capitalized_parts.append(part.capitalize())
    
    if len(capitalized_parts) >= 2:
        return ' '.join(capitalized_parts[:2])  # Take first two parts as first and last name
    elif len(capitalized_parts) == 1 and len(capitalized_parts[0]) > 2:
        return capitalized_parts[0]
    
    return ""

def gather_thread_referee_clusters(emails, my_emails, known_editors):
    clusters = {}
    for mail in emails:
        for field in ('from', 'to'):
            addr = extract_email_only(mail.get(field, ""))
            name = extract_name_from_header(mail.get(field, ""))
            if addr:
                addr_l = addr.lower()
                if addr_l not in my_emails and addr_l not in known_editors:
                    uname = addr.split('@')[0].lower()
                    uname = USERNAME_ALIASES.get(uname, uname)  # Apply alias
                    
                    
                    clusters.setdefault(uname, {'addresses': set(), 'names': set()})
                    clusters[uname]['addresses'].add(addr_l)
                    if name: clusters[uname]['names'].add(name)
        cc_field = mail.get('cc') or mail.get('Cc') or mail.get('CC')
        if cc_field:
            for part in cc_field.split(','):
                addr = extract_email_only(part.strip())
                name = extract_name_from_header(part.strip())
                if addr:
                    addr_l = addr.lower()
                    if addr_l not in my_emails and addr_l not in known_editors:
                        uname = addr.split('@')[0].lower()
                        uname = USERNAME_ALIASES.get(uname, uname)  # Apply alias
                        clusters.setdefault(uname, {'addresses': set(), 'names': set()})
                        clusters[uname]['addresses'].add(addr_l)
                        if name: clusters[uname]['names'].add(name)
    return clusters

def deduplicate_referees_by_username(clusters, accepteds, contacts, contact_date):
    """Deduplicate referees and determine their status by analyzing full email chain"""
    merged_referees = []
    for uname, data in clusters.items():
        best_name = pick_best_name(data['names'], uname)
        all_addresses = sorted(data['addresses'])
        main_email = all_addresses[0]
        alt_emails = ", ".join(all_addresses[1:])
        status, accepted_date, due_date = "Unknown", "", ""
        
        
        # First check ALL emails for report submission (highest priority)
        for mail in accepteds + contacts:
            # Check if this email involves this referee
            involved = False
            for field in ['from', 'to', 'cc']:
                email_addr = extract_email_only(mail.get(field, "")).lower()
                if email_addr in data['addresses']:
                    involved = True
                    break
            
            if involved:
                # Check email body for report submission indicators
                body = (mail.get("body", "") or "").lower()
                subject = (mail.get("subject", "") or "").lower()
                
                
                # Check for report submission patterns (specific to COMPLETED reports, not future promises)
                report_patterns = [
                    "report submitted", "report completed", "review submitted", "review completed",
                    "submitted my report", "completed my review", "finished my review", 
                    "review is complete", "report is complete", "here is my report",
                    "report is attached", "attached is my report", "submitting my report",
                    "completed the review", "finished the review", "review done",
                    "report done", "i have completed", "i have finished",
                    "review attached", "attached review", "review is attached",
                    "attached please find the report", "please find the report attached",
                    "sending the report", "report attached", "with the report attached"
                ]
                
                for pattern in report_patterns:
                    if pattern in body or pattern in subject:
                        status = "Report Submitted"
                        sdate = parse_email_date(mail.get("date"))
                        accepted_date = sdate.strftime("%d/%m/%Y") if sdate else ""
                        due_date = ""  # No due date for completed reports
                        break
                
                if status == "Report Submitted":
                    break
        
        # If no report found, check for acceptance
        if status != "Report Submitted":
            for r in accepteds:
                ref_email = extract_email_only(r.get("from", "")).lower()
                if ref_email in data['addresses']:
                    status = "Accepted"
                    adate = parse_email_date(r.get("date"))
                    accepted_date = adate.strftime("%d/%m/%Y") if adate else ""
                    due_date = (adate + relativedelta(months=3)).strftime("%d/%m/%Y") if adate else ""
                    break
        
        # If not found in accepteds, check ALL emails for acceptance indicators
        if status != "Accepted":
            # Check all emails in the thread for acceptance phrases
            for mail in accepteds + contacts:
                # Check if this email involves this referee
                involved = False
                for field in ['from', 'to', 'cc']:
                    email_addr = extract_email_only(mail.get(field, "")).lower()
                    if email_addr in data['addresses']:
                        involved = True
                        break
                
                if involved:
                    # Check email body for acceptance indicators
                    body = (mail.get("body", "") or "").lower()
                    subject = (mail.get("subject", "") or "").lower()
                    from_email = extract_email_only(mail.get("from", "")).lower()
                    to_email = extract_email_only(mail.get("to", "")).lower()
                    
                    
                    acceptance_phrases = [
                        "i accept", "i am happy to", "i will review", "i agree to",
                        "i would be happy to", "i can review", "i'll review",
                        "yes, i will", "yes i will", "happy to review",
                        "agree to review", "willing to review", "pleased to review",
                        "i am willing", "i'd be happy", "count me in",
                        "i accept the invitation", "accept your invitation",
                        "yes i can", "sure i will", "i'll be happy", "i'm happy to"
                    ]
                    
                    # Check for report completion/submission phrases
                    report_completion_phrases = [
                        "report submitted", "report completed", "review submitted", "review completed",
                        "my report", "attached report", "report attached", "submitted my report",
                        "completed my review", "finished my review", "review is complete",
                        "report is complete", "please find my report", "here is my report",
                        "my review is attached", "report is attached", "sending my report",
                        "submitting my report", "final report", "review report", "referee report"
                    ]
                    
                    # First check for report completion (higher priority than acceptance)
                    for phrase in report_completion_phrases:
                        if phrase in body:
                            status = "Report Submitted"
                            adate = parse_email_date(mail.get("date"))
                            accepted_date = adate.strftime("%d/%m/%Y") if adate else ""
                            due_date = ""  # No due date for completed reports
                            break
                    
                    # Only check for acceptance if no report completion found
                    if status != "Report Submitted":
                        for phrase in acceptance_phrases:
                            if phrase in body:
                                status = "Accepted"
                                adate = parse_email_date(mail.get("date"))
                                accepted_date = adate.strftime("%d/%m/%Y") if adate else ""
                                due_date = (adate + relativedelta(months=3)).strftime("%d/%m/%Y") if adate else ""
                                break
                    
                    if status == "Accepted":
                        break
        
        # If still not accepted or report submitted, check if contacted
        if status not in ["Accepted", "Report Submitted"]:
            for r in contacts:
                ref_email = extract_email_only(r.get("to", "")).lower()
                if ref_email in data['addresses']:
                    status = "Contacted"
                    break
        
        
        merged_referees.append({
            "Referee Name": best_name,
            "Referee Email": main_email,
            "Alt Emails": alt_emails,
            "Status": status,
            "Contacted Date": contact_date.strftime("%d/%m/%Y") if contact_date else "",
            "Accepted Date": accepted_date,
            "Due Date": due_date,
        })
    return merged_referees

class FSJournal(JournalBase):
    def __init__(self, driver=None, debug=True):
        self.driver = driver

        self.paper_downloader = get_paper_downloader()
    def get_url(self):
        return None

    def login(self):
        pass

    def scrape_manuscripts_and_emails(self):
        MY_EMAILS = {"dylansmb@gmail.com", "dylan.possamai@math.ethz.ch"}
        MY_NAMES = {"dylan possamai", "dylan possamaï"}

        try:
            starred = fetch_starred_emails('FS')
        except Exception:
            return []

        id_to_emails = {}
        all_ms_ids = set()
        for mail in starred:
            ids = set()
            for field in ("subject",):
                can_id = canonicalize_fs_id(mail.get(field, ""))
                if can_id:
                    ids.add(can_id)
            for id_str in ids:
                if not id_str: continue
                id_to_emails.setdefault(id_str, []).append(mail)
                all_ms_ids.add(id_str)

        try:
            service = gmail_api_authenticate()
        except Exception:
            return []
        ms_id_strings = set(all_ms_ids)
        # Fetch sent emails from me
        query = 'from:(dylansmb@gmail.com OR dylan.possamai@math.ethz.ch) subject:FS- newer_than:1y'
        try:
            sent_messages = gmail_search_messages(service, query, max_results=200)
        except Exception:
            sent_messages = []
        
        # Collect referee emails from multiple sources
        referee_emails = set()
        
        # 1. From starred emails
        for mail in starred:
            from_email = extract_email_only(mail.get("from", "")).lower()
            to_email = extract_email_only(mail.get("to", "")).lower()
            if from_email and from_email not in MY_EMAILS:
                referee_emails.add(from_email)
            if to_email and to_email not in MY_EMAILS:
                referee_emails.add(to_email)

        sent_emails = []
        for msg in sent_messages:
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_ = next((h['value'] for h in headers if h['name'] == 'From'), '')
            to_ = next((h['value'] for h in headers if h['name'] == 'To'), '')
            cc_ = next((h['value'] for h in headers if h['name'] == 'Cc'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract body content
            body = extract_body_from_gmail_message(msg['payload'])
            
            # Also collect referee emails from sent messages
            to_email = extract_email_only(to_).lower()
            if to_email and to_email not in MY_EMAILS and to_email not in KNOWN_EDITORS:
                referee_emails.add(to_email)
            
            for ms_id in ms_id_strings:
                if ms_id in (''.join(re.findall(r'\d', subject))):
                    sent_emails.append({
                        'raw_msg': None,
                        'subject': subject,
                        'date': date,
                        'from': from_,
                        'to': to_,
                        'cc': cc_,
                        'body': body,
                        'gmail_msg': msg,
                    })
                    break
        for mail in sent_emails:
            ids = set()
            for field in ("subject",):
                can_id = canonicalize_fs_id(mail.get(field, ""))
                if can_id:
                    ids.add(can_id)
            for id_str in ids:
                if not id_str: continue
                id_to_emails.setdefault(id_str, []).append(mail)
        
        # Now add email associations based on USERNAME_ALIASES
        email_associations = {}
        for username, alias in USERNAME_ALIASES.items():
            # For each alias mapping, link the email domains
            email_associations[f'{username}@gmail.com'] = f'{alias}@se.cuhk.edu.hk'
            email_associations[f'{alias}@se.cuhk.edu.hk'] = f'{username}@gmail.com'
        
        # Add associated emails
        additional_emails = set()
        for ref_email in referee_emails:
            if ref_email in email_associations:
                additional_emails.add(email_associations[ref_email])
        referee_emails.update(additional_emails)
        
        # Fetch emails from all referee addresses (including associated ones)
        received_messages = []
        for ref_email in referee_emails:
            try:
                query = f'from:{ref_email} subject:FS- newer_than:1y'
                ref_msgs = gmail_search_messages(service, query, max_results=50)
                received_messages.extend(ref_msgs)
            except Exception as e:
                continue
        
        # Process received messages from referees
        for msg in received_messages:
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_ = next((h['value'] for h in headers if h['name'] == 'From'), '')
            to_ = next((h['value'] for h in headers if h['name'] == 'To'), '')
            cc_ = next((h['value'] for h in headers if h['name'] == 'Cc'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract body content
            body = extract_body_from_gmail_message(msg['payload'])
            
            # Check if this email relates to any manuscript
            for ms_id in ms_id_strings:
                if ms_id in (''.join(re.findall(r'\d', subject))):
                    mail_entry = {
                        'raw_msg': None,
                        'subject': subject,
                        'date': date,
                        'from': from_,
                        'to': to_,
                        'cc': cc_,
                        'body': body,
                        'gmail_msg': msg,
                    }
                    id_to_emails.setdefault(ms_id, []).append(mail_entry)
                    break

        manuscripts = []
        for id_str, emails in id_to_emails.items():
            ms_id = display_fs_id(id_str)
            contacts = []
            accepteds = []
            for mail in emails:
                from_addr = (mail.get("from") or "").lower()
                from_addr_normalized = from_addr.replace("ï", "i").replace("ı", "i")
                is_mine = (
                    any(addr in from_addr for addr in MY_EMAILS)
                    or any(addr in from_addr_normalized for addr in MY_EMAILS)
                    or any(name in from_addr_normalized for name in MY_NAMES)
                )
                if is_mine:
                    contacts.append(mail)
                else:
                    ref_email = extract_email_only(mail.get("from", ""))
                    ref_name = extract_name_from_header(mail.get("from", ""))
                    if is_real_referee(ref_email, ref_name):
                        accepteds.append(mail)

            title, first_author, contact_date = "", "", None
            
            # Get contact date from earliest email
            for mail in sorted(contacts, key=lambda m: m.get("date", ""), reverse=True):
                if not contact_date:
                    contact_date = parse_email_date(mail.get("date"))
                    break
            
            # For FS journal, ONLY extract title and author from PDF attachments
            # Email subjects/bodies are not reliable for FS journal
            print(f"[PDF_DEBUG] Extracting title and author from PDF only for {ms_id}")
            
            # Collect all referee emails to check against
            referee_emails = set()
            for mail in emails:
                from_email = extract_email_only(mail.get("from", "")).lower()
                to_email = extract_email_only(mail.get("to", "")).lower()
                if from_email and from_email not in MY_EMAILS and from_email not in KNOWN_EDITORS:
                    referee_emails.add(from_email)
                if to_email and to_email not in MY_EMAILS and to_email not in KNOWN_EDITORS:
                    referee_emails.add(to_email)
            
            for mail in sorted(contacts, key=lambda m: m.get("date", ""), reverse=True):
                if mail.get("gmail_msg"):
                    try:
                        pdf_paths = extract_pdf_attachments_from_gmail_message(service, mail["gmail_msg"])
                        if pdf_paths:
                            print(f"[PDF_DEBUG] Found {len(pdf_paths)} PDF attachments")
                            pdf_title, pdf_author = parse_pdf_title_author_enhanced(pdf_paths[0])
                            if pdf_title and pdf_title != "PDF_NOT_PARSED":
                                title = pdf_title
                                print(f"[PDF_DEBUG] Using PDF title: {title}")
                            if pdf_author and pdf_author != "PDF_NOT_PARSED":
                                # Double-check that this isn't an editor or referee
                                if not is_likely_editor(pdf_author) and not is_likely_referee(pdf_author, referee_emails):
                                    first_author = pdf_author
                                    print(f"[PDF_DEBUG] Using PDF author: {first_author}")
                                else:
                                    print(f"[PDF_DEBUG] Skipping likely editor or referee: {pdf_author}")
                                    # Try to find the real author in the PDF text
                                    real_author = find_real_author_in_pdf_text(pdf_paths[0], referee_emails)
                                    if real_author and not is_likely_editor(real_author) and not is_likely_referee(real_author, referee_emails):
                                        first_author = real_author
                                        print(f"[PDF_DEBUG] Found real author: {first_author}")
                            if title and first_author:  # Both found, no need to continue
                                break
                    except Exception as e:
                        print(f"[PDF_DEBUG] PDF parsing failed for {ms_id}: {e}")
                        pass

            clusters = gather_thread_referee_clusters(emails, MY_EMAILS, KNOWN_EDITORS)
            referee_records = deduplicate_referees_by_username(
                clusters, accepteds, contacts, contact_date
            )

            n_accepted = sum(1 for r in referee_records if r["Status"] == "Accepted")
            n_reports_submitted = sum(1 for r in referee_records if r["Status"] == "Report Submitted")
            n_total_referees = len(referee_records)
            
            # New logic: check if ALL referees have submitted reports
            if n_total_referees > 0 and n_reports_submitted == n_total_referees:
                current_stage = "All Reports Received"
            elif n_reports_submitted > 0 and n_reports_submitted < n_total_referees:
                current_stage = "Partial Reports Received"
            elif n_accepted >= 2:
                current_stage = "All Referees Assigned"
            else:
                current_stage = "Pending Referee Assignments"
            
            # Filter referees based on current stage for digest display
            filtered_referees = referee_records
            if current_stage == "All Reports Received":
                # Show all referees with their completed status for transparency
                filtered_referees = referee_records
            elif current_stage == "Partial Reports Received":
                # Show only pending referees (not the ones who submitted reports)
                filtered_referees = [r for r in referee_records if r["Status"] != "Report Submitted"]
            
            # Add default values if title/author still not found
            if not title:
                title = f"[Title Not Found - Check PDF] {ms_id}"
                print(f"[WARNING] No title found for {ms_id}")
            if not first_author:
                first_author = "[Author Not Found - Check PDF]"
                print(f"[WARNING] No author found for {ms_id}")
            
            manuscripts.append({
                "Manuscript #": ms_id,
                "Title": title,
                "Contact Author": first_author,
                "Current Stage": current_stage,
                "Referees": filtered_referees,
            })
        # Download papers and reports with AI analysis
        enhanced_manuscripts = self.download_and_analyze_manuscripts(manuscripts)
        return enhanced_manuscripts
    def download_manuscripts(self, manuscripts: List[Dict]) -> List[Dict]:
        """Download papers and referee reports for manuscripts"""
        if not hasattr(self, 'paper_downloader'):
            self.paper_downloader = get_paper_downloader()
        
        enhanced_manuscripts = []
        
        for manuscript in manuscripts:
            enhanced_ms = manuscript.copy()
            enhanced_ms['downloads'] = {
                'paper': None,
                'reports': []
            }
            
            try:
                manuscript_id = manuscript.get('Manuscript #', manuscript.get('manuscript_id', ''))
                title = manuscript.get('Title', manuscript.get('title', ''))
                
                if manuscript_id and title:
                    # Try to find paper download links
                    paper_links = self.paper_downloader.find_paper_links(self.driver, "FS")
                    
                    for link in paper_links:
                        if link['type'] == 'href':
                            paper_path = self.paper_downloader.download_paper(
                                manuscript_id, title, link['url'], "FS", self.driver
                            )
                            if paper_path:
                                enhanced_ms['downloads']['paper'] = str(paper_path)
                                break
                    
                    # Try to find referee report links
                    report_links = self.paper_downloader.find_report_links(self.driver, "FS")
                    
                    for link in report_links:
                        if link['type'] == 'href':
                            report_path = self.paper_downloader.download_referee_report(
                                manuscript_id, link['text'], link['url'], "FS", self.driver
                            )
                            if report_path:
                                enhanced_ms['downloads']['reports'].append(str(report_path))
                
            except Exception as e:
                print(f"Error downloading for manuscript {manuscript_id}: {e}")
            
            enhanced_manuscripts.append(enhanced_ms)
        
        return enhanced_manuscripts