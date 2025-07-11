#!/usr/bin/env python3
"""
Test referee status parsing logic
"""

def parse_referee_status(cell_text: str, row_html: str) -> str:
    """Parse referee status from table cell."""
    cell_lower = cell_text.lower()
    row_lower = row_html.lower()
    
    # Check for various status indicators
    if 'declined' in cell_lower or 'declined' in row_lower:
        return 'Declined'
    elif 'report' in cell_lower or 'submitted' in cell_lower:
        return 'Report Submitted'
    elif 'accepted' in cell_lower or 'agreed' in cell_lower:
        return 'Accepted'
    elif 'invited' in cell_lower or 'pending' in cell_lower:
        return 'Invited'
    elif 'overdue' in cell_lower:
        return 'Overdue'
    else:
        # Default based on context
        if 'due' in cell_lower:
            return 'Accepted'  # Has a due date
        else:
            return 'Invited'


# Test cases from actual data
test_cases = [
    # From manuscripts_table.html snippets
    ("Ferrari (declined 1/30/24)", "", "Declined"),
    ("LI (declined 1/26/24)", "", "Declined"),
    ("daudin (declined 1/29/24)", "", "Declined"),
    ("Cohen (due 8/1/24)", "", "Accepted"),
    ("Guo (due 8/8/24)", "", "Accepted"),
    ("Ekren", "invited", "Invited"),
    ("Ren (due 8/5/24)", "", "Accepted"),
    ("daudin", "", "Invited"),
    ("Tangpi (due 8/15/24)", "", "Accepted"),
    ("Report submitted", "", "Report Submitted"),
    ("Overdue since 7/1/24", "", "Overdue"),
]

print("Testing referee status parsing:")
print("=" * 60)

for cell_text, row_context, expected in test_cases:
    result = parse_referee_status(cell_text, row_context)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{cell_text}' -> {result} (expected: {expected})")

print("\n" + "=" * 60)
print("\nActual HTML patterns to look for:")
print("- Declined: '(declined M/D/YY)'")
print("- Accepted: '(due M/D/YY)'")
print("- Report Submitted: 'report submitted' or similar")
print("- Invited: No parentheses or just the name")
print("- Overdue: 'overdue'")