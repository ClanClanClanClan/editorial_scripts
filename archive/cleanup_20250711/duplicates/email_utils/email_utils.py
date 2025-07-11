import os
import re
import logging
import base64
import unicodedata
import json
from datetime import datetime, timedelta, date
from email.header import decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

GMAIL_USER = os.environ.get("GMAIL_USER")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# === Gmail API AUTH ===
def get_gmail_service():
    """Authenticate and return a Gmail API service using 'token.json'."""
    creds = None
    token_path = 'token.json'
    creds_path = 'credentials.json'
    # Load token if it exists
    if os.path.exists(token_path):
        try:
            # Try JSON format first
            with open(token_path, 'r') as token:
                token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except (json.JSONDecodeError, ValueError):
            # Fall back to pickle format
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
    # If no (valid) creds, start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

# === Robust fuzzy matching and normalization ===

def robust_normalize(s):
    """Unicode/diacritic and punctuation-insensitive lowercasing/spacing."""
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def robust_match_email_for_referee_fs(*args, **kwargs):
    """For FS, we never do email crossmatch."""
    return ("", "")

def robust_match_email_for_referee(ref_name, ms_id, status, flagged_emails):
    ref_name_norm = robust_normalize(ref_name)
    names = ref_name_norm.split()
    name_patterns = []
    if len(names) == 2:
        first, last = names
        name_patterns = [
            f"{first} {last}",
            f"{last} {first}",
            f"{first[0]} {last}",
            last,
            first,
        ]
    else:
        name_patterns = [ref_name_norm] + names

    ms_id_norm = robust_normalize(ms_id)
    ms_id_digits = re.sub(r"[^0-9]", "", ms_id)
    ms_id_variants = [ms_id_norm]
    if ms_id_digits:
        ms_id_variants.append(ms_id_digits)
        ms_id_variants.append("m" + ms_id_digits)

    ACCEPTED_PHRASES = [
        "agreed to review", "has agreed to review", "accepted to review", "has accepted to review",
        "agreed to referee", "has agreed to referee", "has agreed", "agreed"
    ]
    CONTACTED_PHRASES = [
        "hoping you'll be willing", "invited to referee", "please decide", "would you be willing",
        "you have been invited", "has been invited", "contacted you", "please consider"
    ]

    def mail_matches(mail, patterns, ms_patterns, phrases):
        subj = robust_normalize(mail.get("subject", ""))
        body = robust_normalize(mail.get("body", ""))
        if not any(p in subj or p in body for p in patterns):
            return False
        if not any(ms in subj or ms in body for ms in ms_patterns):
            return False
        body_lc = mail.get("body", "").lower()
        if status == "Accepted":
            if not any(phrase in body_lc for phrase in ACCEPTED_PHRASES):
                return False
        if status == "Contacted":
            if not any(phrase in body_lc for phrase in CONTACTED_PHRASES):
                return False
        return True

    for mail in flagged_emails:
        if mail_matches(mail, name_patterns, ms_id_variants, ACCEPTED_PHRASES if status == "Accepted" else CONTACTED_PHRASES):
            return mail.get("date", "")
    last = names[-1] if names else ref_name_norm
    for mail in flagged_emails:
        if mail_matches(mail, [last], ms_id_variants, ACCEPTED_PHRASES if status == "Accepted" else CONTACTED_PHRASES):
            return mail.get("date", "")
    for mail in flagged_emails:
        subj = robust_normalize(mail.get("subject", ""))
        body = robust_normalize(mail.get("body", ""))
        if any(ms in subj or ms in body for ms in ms_id_variants):
            body_lc = mail.get("body", "").lower()
            if status == "Accepted" and any(phrase in body_lc for phrase in ACCEPTED_PHRASES):
                return mail.get("date", "")
            if status == "Contacted" and any(phrase in body_lc for phrase in CONTACTED_PHRASES):
                return mail.get("date", "")
    return ""

def robust_match_email_for_referee_mf(ref_name, ms_id, status, flagged_emails):
    def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s or '').lower())
    # Handle "Last, First" format properly
    if ',' in ref_name:
        parts = ref_name.split(',')
        last_name = norm(parts[0].strip())
        first_name = norm(parts[1].strip()) if len(parts) > 1 else ""
    else:
        name_parts = [x for x in re.split(r'\s+', ref_name.strip()) if x]
        if not name_parts:
            return "", ""
        last_name = norm(name_parts[-1])
        first_name = norm(name_parts[0]) if len(name_parts) > 0 else ""
    full_name = norm(ref_name)
    ms_id_base = re.sub(r"\.R\d+$", "", ms_id or "")
    ms_id_digits = re.sub(r"[^0-9]", "", ms_id_base)
    ms_id_pattern = ms_id_digits if ms_id_digits else norm(ms_id_base)

    for mail in flagged_emails:
        subject = mail.get("subject", "") or ""
        body = mail.get("body", "") or ""
        to = mail.get("to", "") or ""
        subj_norm = norm(subject)
        body_norm = norm(body)
        to_norm = norm(to)

        ms_id_hit = False
        if ms_id_digits:
            ms_id_hit = (ms_id_digits in subj_norm or ms_id_digits in body_norm or 
                         ('mafi'+ms_id_digits) in subj_norm or ('mafi'+ms_id_digits) in body_norm)
        else:
            ms_id_hit = ms_id_pattern in subj_norm or ms_id_pattern in body_norm
        if not ms_id_hit:
            continue

        name_hit = (last_name in subj_norm or last_name in body_norm or last_name in to_norm or 
                    full_name in subj_norm or full_name in body_norm or
                    first_name in to_norm)  # Check first name in email address
        if not name_hit:
            continue

        status_hit = True
        if status == "Accepted":
            status_hit = any(
                phrase in subject.lower() or phrase in body.lower()
                for phrase in [
                    "thank you for agreeing to review",
                    "agreed to review",
                    "now in your reviewer center"
                ]
            )
        if status == "Contacted":
            status_hit = any(
                phrase in subject.lower() or phrase in body.lower()
                for phrase in [
                    "invitation to review", "invite you to review"
                ]
            )
        if ms_id_hit and name_hit and status_hit:
            # Extract best-matching referee email address from 'To'
            best_email = ""
            to_field = mail.get("to", "") or ""
            possible_addrs = re.split(r'[;, ]+', to_field)
            for addr in possible_addrs:
                addr = addr.strip()
                if not addr or '@' not in addr:
                    continue
                local_part = addr.split('@')[0].lower()
                if last_name and last_name in local_part:
                    best_email = addr
                    break
                if full_name and full_name in local_part:
                    best_email = addr
                    break
            if not best_email and possible_addrs:
                best_email = possible_addrs[0]
            return mail.get("date", ""), best_email
    return "", ""

def robust_match_email_for_referee_jota(ref_name, ms_id, status, flagged_emails):
    """
    Match JOTA reviewer-agreed/assignment emails (Gmail API).
    Returns (date, email) for the referee if found, else ("", "").
    """
    ref_name_norm = robust_normalize(ref_name)
    ms_id_norm = robust_normalize(ms_id)
    last_name = ref_name_norm.split()[-1] if ref_name_norm else ""
    ms_id_pattern = ms_id_norm.replace("jota", "").replace("-", "")
    # Typical subject: "JOTA - Reviewer has agreed to review JOTA-D-25-00081R1"
    for mail in flagged_emails:
        subj = robust_normalize(mail.get("subject", ""))
        body = robust_normalize(mail.get("body", ""))
        full = subj + " " + body
        if ms_id_norm in full or ms_id_pattern in full:
            if last_name in full or ref_name_norm in full:
                # For "Accepted" look for "agreed to take on this assignment"
                if status == "Accepted":
                    if "agreed to take on this assignment" in body or "agreed to review" in subj:
                        # Try to extract email from mail['body'] (the body, not header)
                        emails = re.findall(r"[\w\.-]+@[\w\.-]+", mail.get("body", ""))
                        found_email = emails[0] if emails else ""
                        return mail.get("date", ""), found_email
                # For "Contacted", look for invitation
                if status == "Contacted":
                    if "invitation" in subj or "invited to review" in subj:
                        emails = re.findall(r"[\w\.-]+@[\w\.-]+", mail.get("body", ""))
                        found_email = emails[0] if emails else ""
                        return mail.get("date", ""), found_email
    return "", ""

def robust_match_email_for_referee_mafe(ref_name, ms_id, status, flagged_emails):
    """
    Match MAFE reviewer-agreed/assignment emails (Gmail API).
    Returns (date, email) for the referee if found, else ("", "").
    """
    ref_name_norm = robust_normalize(ref_name)
    ms_id_norm = robust_normalize(ms_id)
    last_name = ref_name_norm.split()[-1] if ref_name_norm else ""
    ms_id_pattern = ms_id_norm.replace("mafe", "").replace("-", "")
    # Typical subject: "MAFE - Reviewer has agreed to review MAFE-D-23-00109R2"
    for mail in flagged_emails:
        subj = robust_normalize(mail.get("subject", ""))
        body = robust_normalize(mail.get("body", ""))
        full = subj + " " + body
        if ms_id_norm in full or ms_id_pattern in full:
            if last_name in full or ref_name_norm in full:
                if status == "Accepted":
                    if "agreed to take on this assignment" in body or "agreed to review" in subj:
                        emails = re.findall(r"[\w\.-]+@[\w\.-]+", mail.get("body", ""))
                        found_email = emails[0] if emails else ""
                        return mail.get("date", ""), found_email
                if status == "Contacted":
                    if "invitation" in subj or "invited to review" in subj:
                        emails = re.findall(r"[\w\.-]+@[\w\.-]+", mail.get("body", ""))
                        found_email = emails[0] if emails else ""
                        return mail.get("date", ""), found_email
    return "", ""

def extract_body_from_email(msg_payload):
    """Extract the plain text body from a Gmail API message payload."""
    if 'parts' in msg_payload:
        for part in msg_payload['parts']:
            if part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif part.get('mimeType') == 'multipart/alternative':
                return extract_body_from_email(part)
    if 'body' in msg_payload and 'data' in msg_payload['body']:
        return base64.urlsafe_b64decode(msg_payload['body']['data']).decode('utf-8', errors='replace')
    return ""

def robust_match_email_for_referee_mor(ref_name, ms_id, status, flagged_emails):
    ms_id_core = re.sub(r"\.R\d+$", "", ms_id or "").lower()
    def norm(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s or '').lower())
    ref_name_norm = norm(ref_name)
    # Handle "Last, First" format properly
    if ',' in ref_name:
        parts = ref_name.split(',')
        last_name = norm(parts[0].strip())
        first_name = norm(parts[1].strip()) if len(parts) > 1 else ""
    else:
        name_parts = [x for x in re.split(r'\s+', ref_name.strip()) if x]
        if not name_parts:
            return "", ""
        last_name = norm(name_parts[-1])
        first_name = norm(name_parts[0]) if len(name_parts) > 0 else ""
    # Create initials from first name
    initials = first_name[0] if first_name else ''
    initials_last = initials + last_name if initials else last_name

    for mail in flagged_emails:
        subject = (mail.get("subject", "") or "")
        body = (mail.get("body", "") or "")
        to_field = (mail.get("to", "") or "")
        subj = subject.lower()
        if ms_id_core not in subj and ms_id_core not in body.lower():
            continue
        all_addrs = re.split(r'[;, ]+', to_field)
        for addr in all_addrs:
            addr = addr.strip()
            if not addr or '@' not in addr:
                continue
            local_part = addr.split('@')[0].lower()
            if local_part in {"katyascheinberg", "editor", "managingeditor", "siam"}:
                continue
            if (last_name in local_part or initials_last in local_part or ref_name_norm in local_part):
                return mail.get("date", ""), addr.lower()
        bsn = body.lower() + " " + subject.lower()
        if (last_name in bsn or ref_name_norm in bsn):
            found_email = ""
            email_matches = re.findall(r'[\w\.-]+@[\w\.-]+', body)
            if email_matches:
                found_email = email_matches[0]
            return mail.get("date", ""), found_email
    return "", ""

def decode_header_field(field):
    if not field:
        return ""
    try:
        return str(make_header(decode_header(field)))
    except Exception:
        return field

def fetch_starred_emails(journal, gmail_user=None, gmail_password=None, custom_subject=None):
    """Fetch starred emails for a given journal using Gmail API."""
    service = get_gmail_service()
    user_id = 'me'

    flagged_emails = []
    search_subj = {
        'SICON': 'SICON manuscript #',
        'SIFIN': 'SIAM J. Financial Mathematics manuscript #',
        'MOR': 'Mathematics of Operations Research',
        'MF': 'Mathematical Finance',
        'JOTA': 'JOTA - Reviewer has agreed to review',
        'MAFE': 'MAFE - Reviewer has agreed to review'
    }.get(journal, journal if journal else "")
    search_pattern = (custom_subject.lower() if custom_subject else search_subj.lower())

    # Gmail API search: label:starred newer_than:2y, etc.
    query = 'is:starred'
    if search_pattern:
        query += f' "{search_pattern}"'
    try:
        # Limit to 50 messages for better performance
        results = service.users().messages().list(userId=user_id, q=query, maxResults=50).execute()
        msg_ids = results.get('messages', [])
        logging.info(f"Found {len(msg_ids)} messages to process for {journal}")
    except Exception as e:
        logging.error(f"Gmail API error fetching messages: {e}")
        return []
    for m in msg_ids:
        try:
            msg = service.users().messages().get(userId=user_id, id=m['id'], format='full').execute()
        except Exception as e:
            logging.warning(f"Failed to fetch email id {m['id']}: {e}")
            continue
        headers = msg['payload'].get('headers', [])
        msg_dict = {h['name'].lower(): h['value'] for h in headers}
        subject = decode_header_field(msg_dict.get("subject", ""))
        from_ = msg_dict.get("from", "")
        to_ = msg_dict.get("to", "")
        date = msg_dict.get("date", "")
        body = extract_body_from_email(msg['payload'])
        entry = {
            "subject": subject,
            "from": from_,
            "to": to_,
            "date": date,
            "body": body,
            "raw_msg": base64.urlsafe_b64decode(msg['raw']).decode('utf-8', errors='replace') if 'raw' in msg else None,
            "id": m['id']
        }
        # Pattern filter for each journal (mirrors your IMAP logic)
        if journal == 'MF':
            if 'mathematical finance' in subject.lower() or 'mafi-' in subject.lower():
                flagged_emails.append(entry)
        elif journal == 'MOR':
            if 'mathematics of operations research' in subject.lower() or 'mor-' in subject.lower():
                flagged_emails.append(entry)
        elif journal == 'JOTA':
            if 'jota - reviewer has agreed to review' in subject.lower() or 'jota - reviewer invitation' in subject.lower():
                flagged_emails.append(entry)
        elif journal == 'MAFE':
            if 'mafe - reviewer has agreed to review' in subject.lower() or 'mafe - reviewer invitation' in subject.lower():
                flagged_emails.append(entry)
        else:
            if search_pattern in subject.lower():
                flagged_emails.append(entry)
    flagged_emails.sort(key=lambda x: x["date"], reverse=True)
    return flagged_emails

def fetch_latest_verification_code(journal="MOR", max_wait=120, poll_interval=5):
    """
    Fetch the latest verification code from Gmail for MF/MOR journals.
    Polls Gmail for new verification emails and extracts the code.
    
    Args:
        journal: Journal name (MOR, MF, etc.)
        max_wait: Maximum time to wait for email in seconds (default 120s = 2 minutes)
        poll_interval: Time between checks in seconds (default 5s)
    """
    import time
    
    service = get_gmail_service()
    user_id = 'me'
    
    # Journal-specific patterns for verification emails
    search_patterns = {
        'MF': ['mathematical finance', 'mafi', 'manuscript central', 'verification'],
        'MOR': ['mathematics of operations research', 'mor', 'manuscript central', 'verification'],
        'SICON': ['sicon', 'manuscript central', 'verification'],
        'SIFIN': ['sifin', 'manuscript central', 'verification']
    }
    
    patterns = search_patterns.get(journal, ['verification', 'code', 'manuscript central'])
    
    # First, wait a bit for the email to arrive
    logging.info(f"Waiting {poll_interval} seconds for verification email to arrive...")
    time.sleep(poll_interval)
    
    # Look for recent emails with verification codes
    start_time = time.time()
    latest_code = None
    latest_timestamp = None
    
    while time.time() - start_time < max_wait:
        try:
            # Search for very recent emails (last 2 minutes) with verification-related content
            query = 'newer_than:2m'
            
            # Add journal-specific terms
            for pattern in patterns:
                query += f' OR "{pattern}"'
            
            results = service.users().messages().list(userId=user_id, q=query, maxResults=10).execute()
            msg_ids = results.get('messages', [])
            
            for m in msg_ids:
                try:
                    msg = service.users().messages().get(userId=user_id, id=m['id'], format='full').execute()
                    headers = msg['payload'].get('headers', [])
                    msg_dict = {h['name'].lower(): h['value'] for h in headers}
                    subject = decode_header_field(msg_dict.get("subject", ""))
                    body = extract_body_from_email(msg['payload'])
                    
                    # Check if this is a verification email
                    is_verification = False
                    subject_lower = subject.lower()
                    body_lower = body.lower()
                    
                    verification_keywords = [
                        'verification code', 'verification token', 'access code',
                        'authentication code', 'security code', 'login code',
                        'two-factor', '2fa', 'token', 'verify your account'
                    ]
                    
                    for keyword in verification_keywords:
                        if keyword in subject_lower or keyword in body_lower:
                            is_verification = True
                            break
                    
                    # Also check for journal-specific verification patterns
                    if journal == 'MF' and ('mathematical finance' in subject_lower or 'mafi' in subject_lower):
                        is_verification = True
                    elif journal == 'MOR' and ('mathematics of operations research' in subject_lower or 'mor' in subject_lower):
                        is_verification = True
                    elif journal in ['SICON', 'SIFIN'] and ('manuscript central' in subject_lower):
                        is_verification = True
                    
                    if is_verification:
                        # Get email timestamp
                        email_date = msg_dict.get("date", "")
                        try:
                            from email.utils import parsedate_to_datetime
                            email_timestamp = parsedate_to_datetime(email_date).timestamp()
                        except:
                            email_timestamp = time.time()
                        
                        # Extract verification code from body
                        code = extract_verification_code_from_text(body)
                        if code:
                            # Update if this is newer than our latest
                            if latest_timestamp is None or email_timestamp > latest_timestamp:
                                latest_code = code
                                latest_timestamp = email_timestamp
                                logging.info(f"Found newer verification code for {journal}: {code} (timestamp: {email_date})")
                        
                        # Also try extracting from subject
                        if not code:
                            code = extract_verification_code_from_text(subject)
                            if code and (latest_timestamp is None or email_timestamp > latest_timestamp):
                                latest_code = code
                                latest_timestamp = email_timestamp
                                logging.info(f"Found newer verification code in subject for {journal}: {code}")
                
                except Exception as e:
                    logging.warning(f"Error processing message {m['id']}: {e}")
                    continue
            
            # If we found a code, return it immediately
            if latest_code:
                logging.info(f"Returning latest verification code for {journal}: {latest_code}")
                return latest_code
            
            # Wait before next poll
            logging.info(f"No code found yet, waiting {poll_interval} seconds before next check...")
            time.sleep(poll_interval)
            
        except Exception as e:
            logging.error(f"Error polling Gmail for verification code: {e}")
            time.sleep(poll_interval)
    
    # Return any code we found, even if loop ended
    if latest_code:
        logging.info(f"Returning latest verification code for {journal}: {latest_code}")
        return latest_code
    
    logging.warning(f"No verification code found for {journal} within {max_wait} seconds")
    return None

def extract_verification_code_from_text(text):
    """
    Extract verification code from email text using various patterns.
    Returns the first code found or None.
    """
    if not text:
        return None
    
    # Common patterns for verification codes
    patterns = [
        r'verification code[:\s]*([0-9]{4,8})',      # "verification code: 123456"
        r'verification token[:\s]*([0-9]{4,8})',     # "verification token: 123456"
        r'access code[:\s]*([0-9]{4,8})',            # "access code: 123456"
        r'authentication code[:\s]*([0-9]{4,8})',    # "authentication code: 123456"
        r'security code[:\s]*([0-9]{4,8})',          # "security code: 123456"
        r'login code[:\s]*([0-9]{4,8})',             # "login code: 123456"
        r'code[:\s]*([0-9]{4,8})',                   # "code: 123456"
        r'token[:\s]*([0-9]{4,8})',                  # "token: 123456"
        r'your code is[:\s]*([0-9]{4,8})',           # "your code is: 123456"
        r'enter the code[:\s]*([0-9]{4,8})',         # "enter the code: 123456"
        r'use this code[:\s]*([0-9]{4,8})',          # "use this code: 123456"
        r'([0-9]{4,8})\s*is your verification',      # "123456 is your verification"
        r'([0-9]{4,8})\s*is your access',            # "123456 is your access"
        r'\b([0-9]{4,8})\b(?=\s*(?:verification|access|authentication|security|login|code|token))',  # standalone numbers before keywords
        r'(?:verification|access|authentication|security|login|code|token)\s*[:\-]*\s*([0-9]{4,8})',  # keywords followed by numbers
        r'\b([0-9]{6})\b',                           # any 6-digit number (common for verification codes)
        r'\b([0-9]{4})\b',                           # any 4-digit number
        r'\b([0-9]{8})\b',                           # any 8-digit number
    ]
    
    text_lower = text.lower()
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            # Return the first match, ensuring it's a reasonable length
            code = matches[0]
            if 4 <= len(code) <= 8 and code.isdigit():
                return code
    
    return None

def send_digest_email(html_content, subject="Editorial Digest", recipient=None,
                     gmail_user=None, gmail_password=None):
    """
    Sends HTML (and plain) digest email via Gmail API.
    """
    gmail_user = gmail_user or GMAIL_USER
    recipient = recipient or RECIPIENT_EMAIL
    plain_content = strip_html(html_content)
    msg = MIMEMultipart("alternative")
    msg['From'] = gmail_user
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(plain_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    # --- Use Gmail API to send (no smtplib fallback) ---
    service = get_gmail_service()
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message = {'raw': raw_message}
    try:
        sent = service.users().messages().send(userId="me", body=message).execute()
        logging.info("Digest email sent successfully via Gmail API.")
    except HttpError as e:
        logging.error(f"Failed to send digest email: {e}")
        raise

def strip_html(html):
    """
    Strips all HTML tags. Uses BeautifulSoup if available, otherwise regex.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n")
    except ImportError:
        import re
        return re.sub(r'<[^>]+>', '', html)