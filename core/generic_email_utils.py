#!/usr/bin/env python3
"""
Generic Email Utilities - Journal-agnostic email matching
"""

import re
import sys
import logging
from .email_utils import robust_normalize

logger = logging.getLogger(__name__)


def robust_match_email_for_referee_generic(ref_name, ms_id, journal_code, status, flagged_emails, starred_emails=None):
    """
    Generic email matching for any journal.
    Tries journal-specific function first, then falls back to generic matching.
    Returns (acceptance_email_info, contact_email_info) where each is a dict with 'date' and 'to'
    """
    import inspect
    from . import email_utils
    
    # Try journal-specific function if it exists
    func_name = f"robust_match_email_for_referee_{journal_code.lower()}"
    
    if hasattr(email_utils, func_name):
        specific_func = getattr(email_utils, func_name)
        try:
            # Check function signature
            sig = inspect.signature(specific_func)
            params = list(sig.parameters.keys())
            
            if 'starred_emails' in params:
                # Functions like MF and MOR that return (acceptance_email, contact_email)
                return specific_func(ref_name, ms_id, status, flagged_emails, starred_emails or [])
            else:
                # Functions that only use flagged emails and return (date, email)
                date, email = specific_func(ref_name, ms_id, status, flagged_emails)
                if date and email:
                    email_info = {'date': date, 'to': email}
                    return email_info, email_info  # Return same for both acceptance and contact
                return None, None
        except Exception as e:
            logger.warning(f"Error calling specific function {func_name}: {e}")
    
    # Generic fallback implementation
    return generic_email_match(ref_name, ms_id, journal_code, status, flagged_emails, starred_emails)


def generic_email_match(ref_name, ms_id, journal_code, status, flagged_emails, starred_emails=None):
    """
    Generic email matching implementation that works for most journals.
    Returns (acceptance_email_info, contact_email_info)
    """
    ref_name_norm = robust_normalize(ref_name)
    ms_id_norm = robust_normalize(ms_id)
    
    # Extract name parts
    if ',' in ref_name:
        last_name = ref_name.split(',')[0].strip().lower()
        first_name = ref_name.split(',')[1].strip().lower() if len(ref_name.split(',')) > 1 else ""
    else:
        parts = ref_name.split()
        last_name = parts[-1].lower() if parts else ""
        first_name = parts[0].lower() if parts else ""
    
    # Search in all available emails
    all_emails = list(flagged_emails)
    if starred_emails:
        all_emails.extend(starred_emails)
    
    acceptance_match = None
    contact_match = None
    best_acceptance_score = 0
    best_contact_score = 0
    
    for mail in all_emails:
        subj = robust_normalize(mail.get("subject", ""))
        body = robust_normalize(mail.get("body", ""))
        full_text = subj + " " + body
        
        # Score this email
        base_score = calculate_base_score(ms_id, ms_id_norm, journal_code, ref_name_norm, last_name, first_name, full_text)
        
        if base_score < 10:  # Minimum threshold
            continue
            
        # Check for acceptance indicators
        acceptance_score = base_score
        if any(keyword in full_text for keyword in ['agreed', 'accepted', 'will review', 'has agreed', 'accepted the invitation', 'agreed to review']):
            acceptance_score += 10
            if acceptance_score > best_acceptance_score:
                best_acceptance_score = acceptance_score
                acceptance_match = mail
        
        # Check for contact/invitation indicators
        contact_score = base_score
        if any(keyword in full_text for keyword in ['invited', 'invitation', 'request to review', 'invited to review', 'review invitation']):
            contact_score += 10
            if contact_score > best_contact_score:
                best_contact_score = contact_score
                contact_match = mail
    
    # Extract email info from matches
    acceptance_info = extract_email_info(acceptance_match, ref_name, last_name, first_name) if acceptance_match else None
    contact_info = extract_email_info(contact_match, ref_name, last_name, first_name) if contact_match else None
    
    return acceptance_info, contact_info


def calculate_base_score(ms_id, ms_id_norm, journal_code, ref_name_norm, last_name, first_name, full_text):
    """Calculate base score for email matching"""
    score = 0
    
    # Check manuscript ID (higher score for exact match)
    if ms_id_norm in full_text:
        score += 20
    elif ms_id.replace('-', '') in full_text:
        score += 15
    elif journal_code.lower() in full_text:
        # Check for partial matches (e.g., just the number part)
        ms_parts = ms_id.split('-')
        if len(ms_parts) >= 3:  # e.g., ['MOR', '2023', '0376']
            if ms_parts[1] in full_text and ms_parts[2] in full_text:
                score += 8
    
    # Check referee name
    if ref_name_norm in full_text:
        score += 20
    elif last_name in full_text:
        score += 15
        if first_name and first_name in full_text:
            score += 5
    
    return score


def extract_email_info(mail, ref_name, last_name, first_name):
    """Extract email information from a mail object"""
    if not mail:
        return None
        
    # Try to extract email from 'to' field first
    to_field = mail.get("to", "")
    email_address = ""
    
    if to_field:
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', to_field)
        if emails:
            # Try to find email matching referee name
            for email in emails:
                email_lower = email.lower()
                if last_name in email_lower or (first_name and first_name in email_lower):
                    email_address = email
                    break
            # Use first email if no name match
            if not email_address:
                email_address = emails[0]
    
    # Try extracting from email body as fallback
    if not email_address:
        body_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', mail.get("body", ""))
        if body_emails:
            for email in body_emails:
                email_lower = email.lower()
                if last_name in email_lower or (first_name and first_name in email_lower):
                    email_address = email
                    break
            if not email_address:
                email_address = body_emails[0]
    
    return {
        'date': mail.get("date", ""),
        'to': email_address,
        'subject': mail.get("subject", ""),
        'body': mail.get("body", "")[:200] + "..." if len(mail.get("body", "")) > 200 else mail.get("body", "")
    }