#!/usr/bin/env python3
"""
Generic Email Utilities - Journal-agnostic email matching
"""

import logging
import re


def robust_normalize(text):
    """Simple normalization function."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower().strip())


logger = logging.getLogger(__name__)


def robust_match_email_for_referee_generic(
    ref_name, ms_id, journal_code, status, flagged_emails, starred_emails=None
):
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

            if "starred_emails" in params:
                # Functions like MF and MOR that return (acceptance_email, contact_email)
                return specific_func(ref_name, ms_id, status, flagged_emails, starred_emails or [])
            else:
                # Functions that only use flagged emails and return (date, email)
                date, email = specific_func(ref_name, ms_id, status, flagged_emails)
                if date and email:
                    email_info = {"date": date, "to": email}
                    return email_info, email_info  # Return same for both acceptance and contact
                return None, None
        except Exception as e:
            logger.warning(f"Error calling specific function {func_name}: {e}")

    # Generic fallback implementation
    return generic_email_match(
        ref_name, ms_id, journal_code, status, flagged_emails, starred_emails
    )


def generic_email_match(ref_name, ms_id, journal_code, status, flagged_emails, starred_emails=None):
    """
    Generic email matching implementation that works for most journals.
    Returns (acceptance_email_info, contact_email_info)
    """
    ref_name_norm = robust_normalize(ref_name)
    ms_id_norm = robust_normalize(ms_id)

    # Extract name parts
    if "," in ref_name:
        last_name = ref_name.split(",")[0].strip().lower()
        first_name = ref_name.split(",")[1].strip().lower() if len(ref_name.split(",")) > 1 else ""
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
        base_score = calculate_base_score(
            ms_id, ms_id_norm, journal_code, ref_name_norm, last_name, first_name, full_text
        )

        if base_score < 10:  # Minimum threshold
            continue

        # Check for acceptance indicators
        acceptance_score = base_score
        if any(
            keyword in full_text
            for keyword in [
                "agreed",
                "accepted",
                "will review",
                "has agreed",
                "accepted the invitation",
                "agreed to review",
            ]
        ):
            acceptance_score += 10
            if acceptance_score > best_acceptance_score:
                best_acceptance_score = acceptance_score
                acceptance_match = mail

        # Check for contact/invitation indicators
        contact_score = base_score
        if any(
            keyword in full_text
            for keyword in [
                "invited",
                "invitation",
                "request to review",
                "invited to review",
                "review invitation",
            ]
        ):
            contact_score += 10
            if contact_score > best_contact_score:
                best_contact_score = contact_score
                contact_match = mail

    # Extract email info from matches
    acceptance_info = (
        extract_email_info(acceptance_match, ref_name, last_name, first_name)
        if acceptance_match
        else None
    )
    contact_info = (
        extract_email_info(contact_match, ref_name, last_name, first_name)
        if contact_match
        else None
    )

    return acceptance_info, contact_info


def calculate_base_score(
    ms_id, ms_id_norm, journal_code, ref_name_norm, last_name, first_name, full_text
):
    """Calculate base score for email matching"""
    score = 0

    # Check manuscript ID (higher score for exact match)
    if ms_id_norm in full_text:
        score += 20
    elif ms_id.replace("-", "") in full_text:
        score += 15
    elif journal_code.lower() in full_text:
        # Check for partial matches (e.g., just the number part)
        ms_parts = ms_id.split("-")
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
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.[\w]+", to_field)
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
        body_emails = re.findall(r"[\w\.-]+@[\w\.-]+\.[\w]+", mail.get("body", ""))
        if body_emails:
            for email in body_emails:
                email_lower = email.lower()
                if last_name in email_lower or (first_name and first_name in email_lower):
                    email_address = email
                    break
            if not email_address:
                email_address = body_emails[0]

    return {
        "date": mail.get("date", ""),
        "to": email_address,
        "subject": mail.get("subject", ""),
        "body": mail.get("body", "")[:200] + "..."
        if len(mail.get("body", "")) > 200
        else mail.get("body", ""),
    }


def fetch_latest_verification_code(
    journal: str, max_wait: int = 300, poll_interval: int = 10, start_timestamp: float = None
) -> str:
    """
    Fetch the latest verification code from Gmail for journal 2FA.
    ONLY returns codes from emails received AFTER start_timestamp.

    Args:
        journal: Journal code (e.g., 'MF', 'MOR')
        max_wait: Maximum time to wait for email in seconds
        poll_interval: Time between checks in seconds
        start_timestamp: Unix timestamp - only return codes from emails received after this time

    Returns:
        Verification code if found, None otherwise
    """
    try:
        from .working_gmail_utils import WorkingGmailService

        gmail_service = WorkingGmailService()
        if not gmail_service.setup_service():
            logger.error("Failed to setup Gmail service for verification code fetching")
            return None

        # Search for verification emails (use shorter time window if we have start_timestamp)
        time_filter = "newer_than:10m" if start_timestamp else "newer_than:1h"
        query = f'subject:verification OR subject:"access code" OR subject:"authentication code" {time_filter}'

        import time

        search_start_time = time.time()

        if start_timestamp:
            print(
                f"   📅 Looking for codes received after {time.strftime('%H:%M:%S', time.localtime(start_timestamp))}"
            )

        while (time.time() - search_start_time) < max_wait:
            try:
                # Search for messages
                results = (
                    gmail_service.service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=20)
                    .execute()
                )

                messages = results.get("messages", [])
                print(f"   📧 Found {len(messages)} potential verification emails")

                # Sort messages by internal timestamp (most recent first)
                verified_messages = []

                for message in messages:
                    # Get message details
                    msg = (
                        gmail_service.service.users()
                        .messages()
                        .get(userId="me", id=message["id"])
                        .execute()
                    )

                    # Get email internal timestamp
                    email_timestamp = int(msg["internalDate"]) / 1000  # Convert from milliseconds

                    # Skip if we have start_timestamp and email is older (with 10 second buffer)
                    if start_timestamp and email_timestamp <= (start_timestamp - 10):
                        continue

                    # Extract subject and body
                    subject = ""
                    body = ""

                    payload = msg["payload"]
                    headers = payload.get("headers", [])

                    # Get subject
                    for header in headers:
                        if header["name"] == "Subject":
                            subject = header["value"]
                            break

                    # Get body
                    if "parts" in payload:
                        for part in payload["parts"]:
                            if part["mimeType"] == "text/plain":
                                body = part["body"]["data"]
                                break
                    else:
                        if payload.get("mimeType") == "text/plain":
                            body = payload["body"]["data"]

                    # Decode base64 body
                    if body:
                        import base64

                        body = base64.urlsafe_b64decode(body).decode("utf-8")

                    # Check if this is a verification email (be more permissive for debugging)
                    full_text = f"{subject} {body}".lower()
                    if any(
                        term in full_text
                        for term in [
                            "verification",
                            "access code",
                            "authentication",
                            "manuscript",
                            "scholarone",
                            journal.lower(),
                        ]
                    ):
                        verified_messages.append(
                            {
                                "timestamp": email_timestamp,
                                "subject": subject,
                                "body": body,
                                "full_text": f"{subject} {body}",
                            }
                        )

                # Sort by timestamp (most recent first) and get the freshest code
                verified_messages.sort(key=lambda x: x["timestamp"], reverse=True)

                for msg_data in verified_messages:
                    code = _extract_verification_code(msg_data["full_text"])
                    if code:
                        msg_time = time.strftime("%H:%M:%S", time.localtime(msg_data["timestamp"]))
                        print(
                            f"   ✅ Found FRESH verification code from email at {msg_time}: {code[:3]}***"
                        )
                        return code

                if not verified_messages:
                    print(f"   📭 No recent verification emails found for {journal}")

                # Wait before next check
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error fetching verification code: {e}")
                time.sleep(poll_interval)

        logger.warning(f"No verification code found for {journal} within {max_wait} seconds")
        return None

    except Exception as e:
        logger.error(f"Failed to fetch verification code for {journal}: {e}")
        return None


def _extract_verification_code(text: str) -> str:
    """
    Extract verification code from email text.

    Args:
        text: Email text to search

    Returns:
        Verification code if found, None otherwise
    """
    if not text:
        return None

    import re

    text_lower = text.lower()

    # Common verification code patterns (most specific first)
    patterns = [
        r"verification code[:\s]*([0-9]{4,8})",  # "verification code: 123456"
        r"verification token[:\s]*([0-9]{4,8})",  # "verification token: 123456"
        r"access code[:\s]*([0-9]{4,8})",  # "access code: 123456"
        r"authentication code[:\s]*([0-9]{4,8})",  # "authentication code: 123456"
        r"security code[:\s]*([0-9]{4,8})",  # "security code: 123456"
        r"login code[:\s]*([0-9]{4,8})",  # "login code: 123456"
        r"your code is[:\s]*([0-9]{4,8})",  # "your code is: 123456"
        r"enter the code[:\s]*([0-9]{4,8})",  # "enter the code: 123456"
        r"use this code[:\s]*([0-9]{4,8})",  # "use this code: 123456"
        r"([0-9]{4,8})\s*is your verification",  # "123456 is your verification"
        r"([0-9]{4,8})\s*is your access",  # "123456 is your access"
        r"code[:\s]*([0-9]{4,8})",  # "code: 123456"
        r"token[:\s]*([0-9]{4,8})",  # "token: 123456"
        # ScholarOne specific patterns
        r"(\d{6})\s+",  # 6 digits followed by whitespace (common ScholarOne format)
        r"\b([0-9]{6})\b",  # any 6-digit number
        r"\b([0-9]{4})\b",  # any 4-digit number
        r"\b([0-9]{8})\b",  # any 8-digit number
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            # Return the first match, ensuring it's a reasonable length
            code = matches[0]
            if 4 <= len(code) <= 8 and code.isdigit():
                return code

    return None
