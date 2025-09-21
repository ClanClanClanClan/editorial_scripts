#!/usr/bin/env python3
"""
Implement Enhanced Affiliation Parsing
======================================

Priority #1 implementation: Parse existing affiliation strings to extract
institution + department + geographical hints.

This is LOW effort, MEDIUM-HIGH impact according to our analysis.
"""

import json
from pathlib import Path


def parse_affiliation_string(affiliation_string):
    """Parse affiliation string into components."""

    if not affiliation_string:
        return {}

    # Clean the string
    affiliation = affiliation_string.strip().replace("<br>", "").replace("<br/>", "")

    # Split by comma for basic parsing
    parts = [part.strip() for part in affiliation.split(",") if part.strip()]

    result = {
        "full_affiliation": affiliation,
        "institution": None,
        "department": None,
        "faculty": None,
        "country_hints": [],
        "city_hints": [],
    }

    if not parts:
        return result

    # Enhanced parsing logic
    for i, part in enumerate(parts):
        part_lower = part.lower()

        # Institution detection (usually first, or contains "university", "college", etc.)
        if (
            i == 0
            or any(
                keyword in part_lower
                for keyword in ["university", "college", "institute", "school"]
            )
            and not any(
                dept_word in part_lower for dept_word in ["department", "faculty", "division"]
            )
        ):
            if not result["institution"]:
                result["institution"] = part

        # Department detection
        elif any(
            keyword in part_lower for keyword in ["department", "dept", "school of", "division"]
        ):
            if not result["department"]:
                result["department"] = part

        # Faculty detection
        elif "faculty" in part_lower:
            if not result["faculty"]:
                result["faculty"] = part

        # City/Country hints
        elif len(part) < 20:  # Short strings might be locations
            # Common city patterns
            if any(
                pattern in part_lower
                for pattern in ["london", "paris", "berlin", "tokyo", "new york"]
            ):
                result["city_hints"].append(part)
            # Common country patterns
            elif any(
                pattern in part_lower for pattern in ["uk", "usa", "france", "germany", "japan"]
            ):
                result["country_hints"].append(part)

    # If we didn't find institution in first pass, use first part
    if not result["institution"] and parts:
        result["institution"] = parts[0]

    # Infer country from institution name
    if result["institution"]:
        inst_lower = result["institution"].lower()
        if "warwick" in inst_lower or "oxford" in inst_lower or "cambridge" in inst_lower:
            result["country_hints"].append("United Kingdom")
        elif "berkeley" in inst_lower or "stanford" in inst_lower or "mit" in inst_lower:
            result["country_hints"].append("United States")
        elif "sorbonne" in inst_lower or "paris" in inst_lower:
            result["country_hints"].append("France")

    return result


def enhance_referee_affiliations(data):
    """Enhance all referee affiliations with parsed components."""

    print("🔧 Enhancing Referee Affiliations with Parsed Components")
    print("=" * 60)

    enhanced_count = 0
    total_referees = 0

    for manuscript in data:
        print(f"\n📄 Processing {manuscript['id']}")

        for referee in manuscript.get("referees", []):
            total_referees += 1
            name = referee.get("name")
            current_affiliation = referee.get("affiliation", "")

            # Parse the affiliation
            parsed = parse_affiliation_string(current_affiliation)

            if parsed["institution"] or parsed["department"]:
                print(f"\n   👤 {name}:")
                print(f"      Original: '{current_affiliation}'")

                # Add parsed components to referee data
                if parsed["institution"]:
                    referee["institution_parsed"] = parsed["institution"]
                    print(f"      Institution: {parsed['institution']}")

                if parsed["department"]:
                    referee["department_parsed"] = parsed["department"]
                    print(f"      Department: {parsed['department']}")

                if parsed["faculty"]:
                    referee["faculty_parsed"] = parsed["faculty"]
                    print(f"      Faculty: {parsed['faculty']}")

                if parsed["country_hints"]:
                    referee["country_hints"] = parsed["country_hints"]
                    print(f"      Country hints: {parsed['country_hints']}")

                if parsed["city_hints"]:
                    referee["city_hints"] = parsed["city_hints"]
                    print(f"      City hints: {parsed['city_hints']}")

                enhanced_count += 1
            else:
                print(f"   ❌ {name}: Could not parse '{current_affiliation}'")

    enhancement_rate = (enhanced_count / total_referees * 100) if total_referees > 0 else 0
    print("\n📊 Enhancement Results:")
    print(f"   Total referees: {total_referees}")
    print(f"   Enhanced affiliations: {enhanced_count}")
    print(f"   Enhancement rate: {enhancement_rate:.1f}%")

    return data


def demonstrate_parsing_examples():
    """Demonstrate parsing on various affiliation string formats."""

    print("\n🧪 Affiliation Parsing Examples")
    print("=" * 60)

    test_cases = [
        "University of Warwick, Department of Statistics",
        "Harvard University, School of Medicine",
        "ETH Zurich, Department of Mathematics, Switzerland",
        "Sorbonne University, Faculty of Science and Engineering",
        "MIT, Computer Science and Artificial Intelligence Laboratory",
        "University of California Berkeley, Department of Mathematics",
        "Le Mans University",
        "Liang, Gechun",  # Name-only case
    ]

    for affiliation in test_cases:
        print(f"\n📝 Input: '{affiliation}'")
        parsed = parse_affiliation_string(affiliation)

        print(f"   Institution: {parsed['institution']}")
        print(f"   Department: {parsed['department']}")
        print(f"   Faculty: {parsed['faculty']}")
        print(f"   Country hints: {parsed['country_hints']}")
        print(f"   City hints: {parsed['city_hints']}")


def main():
    """Main enhancement implementation."""
    print("🚀 Enhanced Affiliation Parsing Implementation")
    print("=" * 60)
    print("Priority #1: LOW effort, MEDIUM-HIGH impact\n")

    # Demonstrate parsing examples
    demonstrate_parsing_examples()

    # Load latest results and enhance them
    results_file = "mf_comprehensive_20250723_134148.json"

    if not Path(results_file).exists():
        print(f"\n❌ Results file not found: {results_file}")
        print("   This demo shows the parsing logic that would be applied")
        return

    with open(results_file) as f:
        data = json.load(f)

    # Enhance the data
    enhanced_data = enhance_referee_affiliations(data)

    # Save enhanced results
    output_file = "mf_comprehensive_enhanced_affiliations.json"
    with open(output_file, "w") as f:
        json.dump(enhanced_data, f, indent=2)

    print(f"\n💾 Enhanced data saved to: {output_file}")

    print("\n🎯 IMMEDIATE IMPACT:")
    print("=" * 40)
    print("✅ Extracted departments from existing affiliation strings")
    print("✅ Separated institution from department fields")
    print("✅ Added geographical hints for country inference")
    print("✅ Zero additional website scraping required")
    print("✅ Ready for integration with online lookup APIs")

    print("\n🚀 NEXT STEPS:")
    print("=" * 40)
    print("1. 🪟 Implement popup extraction for review content")
    print("2. 📧 Parse multiple email addresses")
    print("3. 📊 Extract person details from popups")
    print("4. 🌐 Combine with online API enrichment")


if __name__ == "__main__":
    main()
