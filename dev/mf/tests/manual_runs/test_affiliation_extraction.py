#!/usr/bin/env python3
"""Test affiliation extraction including departments."""

import sys
import json

sys.path.insert(0, "src/core")
from orcid_client import ORCIDClient


def test_affiliation_extraction():
    """Test affiliation extraction comprehensively."""
    print("🧪 TESTING AFFILIATION EXTRACTION")
    print("=" * 60)

    client = ORCIDClient()
    test_orcid = "0000-0003-0752-0773"

    # Test 1: Get full profile
    print(f"\n1️⃣ Getting full profile for {test_orcid}")
    profile = client.get_full_profile(test_orcid)

    if profile:
        # Extract affiliations using the method
        affiliations = client._extract_affiliations_from_profile(profile)
        print(f"   Simple affiliations: {affiliations}")

    # Test 2: Get detailed affiliations
    print(f"\n2️⃣ Getting detailed affiliations")
    detailed_affiliations = client.get_affiliations(test_orcid)

    if detailed_affiliations:
        print(f"   Found {len(detailed_affiliations)} affiliations:")
        for i, affil in enumerate(detailed_affiliations[:5], 1):
            print(f"\n   {i}. {affil.get('organization', 'Unknown')}")
            print(f"      • Type: {affil.get('type', 'Unknown')}")
            print(f"      • Department: {affil.get('department', 'NOT FOUND')}")
            print(f"      • Role: {affil.get('role', 'NOT FOUND')}")
            print(
                f"      • Period: {affil.get('start_date', 'Unknown')} - {affil.get('end_date', 'Present')}"
            )
            print(f"      • Current: {'YES' if affil.get('current') else 'NO'}")
    else:
        print("   ❌ No detailed affiliations found")

    # Test 3: Test enrichment to see what gets included
    print(f"\n3️⃣ Testing full enrichment")
    test_person = {"name": "Gechun Liang", "institution": "University of Warwick"}

    enriched = client.enrich_person_profile(test_person)

    print(f"\n   Enrichment results:")
    print(f"   • ORCID: {enriched.get('orcid', 'NOT FOUND')}")
    print(f"   • Country: {enriched.get('country', 'NOT FOUND')}")
    print(f"   • Current affiliation: {enriched.get('current_affiliation', {})}")

    if enriched.get("affiliation_history"):
        print(f"   • Affiliation history: {len(enriched['affiliation_history'])} entries")
        for i, affil in enumerate(enriched["affiliation_history"][:3], 1):
            print(f"\n     {i}. {affil.get('organization', 'Unknown')}")
            print(f"        - Department: {affil.get('department', 'NOT FOUND')}")
            print(f"        - Role: {affil.get('role', 'NOT FOUND')}")
            print(f"        - Current: {'YES' if affil.get('current') else 'NO'}")

    # Test 4: Direct API call to employments endpoint
    print(f"\n4️⃣ Testing direct employments API call")
    import requests

    employment_url = f"https://pub.orcid.org/v3.0/{test_orcid}/employments"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {client.access_token}"}

    try:
        response = requests.get(employment_url, headers=headers, timeout=10)
        if response.status_code == 200:
            employments_data = response.json()

            # Save raw data for inspection
            with open("debug_employments_raw.json", "w") as f:
                json.dump(employments_data, f, indent=2)
            print("   Raw employments data saved to debug_employments_raw.json")

            # Check structure
            print(f"   Employment data keys: {list(employments_data.keys())}")

            # Check for affiliation-group structure
            if "affiliation-group" in employments_data:
                groups = employments_data["affiliation-group"]
                print(f"   Found {len(groups)} affiliation groups")

                for group in groups[:2]:
                    summaries = group.get("summaries", [])
                    for summary in summaries:
                        emp_summary = summary.get("employment-summary", {})
                        org = emp_summary.get("organization", {})
                        dept = emp_summary.get("department-name", "")
                        role = emp_summary.get("role-title", "")
                        print(f"\n   • {org.get('name', 'Unknown')}")
                        print(f"     - Department: {dept if dept else 'NOT FOUND'}")
                        print(f"     - Role: {role if role else 'NOT FOUND'}")

        else:
            print(f"   API call failed: {response.status_code}")

    except Exception as e:
        print(f"   Exception: {e}")


if __name__ == "__main__":
    test_affiliation_extraction()
