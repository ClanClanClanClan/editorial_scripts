"""Text processing utilities extracted from legacy extractor."""

import re
from difflib import SequenceMatcher


def normalize_name(name: str) -> str:
    """
    Convert name from 'Last, First' format to 'First Last' format.

    Args:
        name: Name string in any format

    Returns:
        Normalized name in 'First Last' format

    Examples:
        >>> normalize_name("Smith, John")
        'John Smith'
        >>> normalize_name("John Smith")
        'John Smith'
        >>> normalize_name("  Smith , John  ")
        'John Smith'
    """
    if not name:
        return ""

    name = name.strip()

    # Handle 'Last, First' format
    if "," in name:
        parts = name.split(",", 1)
        if len(parts) == 2:
            return f"{parts[1].strip()} {parts[0].strip()}"

    return name


def is_same_person_name(name1: str, name2: str) -> bool:
    """
    Check if two names refer to the same person, handling different formats.

    Handles:
    - Different ordering (First Last vs Last, First)
    - Middle initials
    - Common variations

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        True if names likely refer to same person

    Examples:
        >>> is_same_person_name("John Smith", "Smith, John")
        True
        >>> is_same_person_name("John A. Smith", "John Smith")
        True
        >>> is_same_person_name("J. Smith", "John Smith")
        True
    """
    if not name1 or not name2:
        return False

    # Normalize both names
    n1 = normalize_name(name1).lower()
    n2 = normalize_name(name2).lower()

    # Direct match
    if n1 == n2:
        return True

    # Split into parts
    parts1 = n1.split()
    parts2 = n2.split()

    if not parts1 or not parts2:
        return False

    # Check last names match
    if parts1[-1] != parts2[-1]:
        return False

    # Check first names (handle initials)
    first1 = parts1[0] if parts1 else ""
    first2 = parts2[0] if parts2 else ""

    # Handle initials (J. vs John)
    if first1.endswith("."):
        first1 = first1[:-1]
    if first2.endswith("."):
        first2 = first2[:-1]

    # Check if one is initial of the other
    if len(first1) == 1 or len(first2) == 1:
        return first1[0] == first2[0]

    # Check if first names match
    return first1 == first2


def parse_affiliation_string(affiliation: str) -> dict[str, str]:
    """
    Parse affiliation string into components.

    Args:
        affiliation: Raw affiliation string

    Returns:
        Dictionary with parsed components:
        - institution: Main institution name
        - department: Department if present
        - city: City if present
        - country: Country if present

    Examples:
        >>> parse_affiliation_string("MIT, Department of Mathematics, Cambridge, MA, USA")
        {'institution': 'MIT', 'department': 'Department of Mathematics',
         'city': 'Cambridge', 'country': 'USA'}
    """
    if not affiliation:
        return {}

    result = {"institution": "", "department": "", "city": "", "country": ""}

    # Clean up the string
    affiliation = affiliation.strip()

    # Common country patterns at the end
    country_patterns = [
        r",\s*(USA|US|United States)$",
        r",\s*(UK|United Kingdom|England)$",
        r",\s*(France|Germany|Switzerland|Canada|Australia|Japan|China)$",
    ]

    for pattern in country_patterns:
        match = re.search(pattern, affiliation, re.IGNORECASE)
        if match:
            result["country"] = match.group(1)
            affiliation = affiliation[: match.start()]
            break

    # Split by commas
    parts = [p.strip() for p in affiliation.split(",")]

    if parts:
        # First part is usually the institution
        result["institution"] = parts[0]

        # Look for department
        for part in parts[1:]:
            if any(dept in part.lower() for dept in ["department", "dept", "school", "institute"]):
                result["department"] = part
                break

        # Last part before country might be city
        if len(parts) > 1 and not result["department"]:
            result["city"] = parts[-1]

    return result


def extract_email_domain(email: str) -> str | None:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain part of email or None

    Examples:
        >>> extract_email_domain("john@mit.edu")
        'mit.edu'
        >>> extract_email_domain("invalid-email")
        None
    """
    if not email or "@" not in email:
        return None

    parts = email.split("@")
    if len(parts) == 2:
        return parts[1].strip().lower()

    return None


def infer_institution_from_email(email: str) -> str | None:
    """
    Infer institution from email domain.

    Args:
        email: Email address

    Returns:
        Inferred institution name or None

    Examples:
        >>> infer_institution_from_email("john@mit.edu")
        'Massachusetts Institute of Technology'
        >>> infer_institution_from_email("jane@stanford.edu")
        'Stanford University'
    """
    domain = extract_email_domain(email)
    if not domain:
        return None

    # Common academic domain mappings
    known_institutions = {
        "mit.edu": "Massachusetts Institute of Technology",
        "stanford.edu": "Stanford University",
        "harvard.edu": "Harvard University",
        "princeton.edu": "Princeton University",
        "yale.edu": "Yale University",
        "columbia.edu": "Columbia University",
        "berkeley.edu": "University of California, Berkeley",
        "caltech.edu": "California Institute of Technology",
        "cornell.edu": "Cornell University",
        "upenn.edu": "University of Pennsylvania",
        "cam.ac.uk": "University of Cambridge",
        "ox.ac.uk": "University of Oxford",
        "imperial.ac.uk": "Imperial College London",
        "ucl.ac.uk": "University College London",
        "ethz.ch": "ETH Zurich",
        "epfl.ch": "EPFL",
        "ens.fr": "École Normale Supérieure",
        "polytechnique.fr": "École Polytechnique",
        "mpg.de": "Max Planck Institute",
        "tum.de": "Technical University of Munich",
    }

    # Direct match
    if domain in known_institutions:
        return known_institutions[domain]

    # Try to infer from domain structure
    # Remove common suffixes
    base = domain.replace(".edu", "").replace(".ac.uk", "").replace(".org", "")

    # Handle subdomains (e.g., math.berkeley.edu)
    if "." in base:
        parts = base.split(".")
        base = parts[-1]  # Use the main domain part

    # Capitalize and add "University" if it looks like a university domain
    if base and len(base) > 2:
        return f"{base.title()} University"

    return None


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text

    Examples:
        >>> clean_text("  Multiple   spaces   and\\nnewlines  ")
        'Multiple spaces and newlines'
    """
    if not text:
        return ""

    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def similarity_score(text1: str, text2: str) -> float:
    """
    Calculate similarity score between two strings.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0 and 1

    Examples:
        >>> similarity_score("John Smith", "John Smith")
        1.0
        >>> similarity_score("John Smith", "Jon Smith") > 0.8
        True
    """
    if not text1 or not text2:
        return 0.0

    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
