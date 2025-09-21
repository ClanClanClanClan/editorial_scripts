#!/usr/bin/env python3
"""Fix the indentation issue in enrich_referee_profiles function."""

import re

# Read the file
mf_path = '../../../production/src/extractors/mf_extractor.py'
with open(mf_path, 'r') as f:
    lines = f.readlines()

# Find the problematic function
in_function = False
function_start = None
function_end = None

for i, line in enumerate(lines):
    if 'def enrich_referee_profiles' in line:
        in_function = True
        function_start = i
    elif in_function and (line.startswith('    def ') or line.startswith('class ')):
        function_end = i
        break

if function_start and function_end:
    print(f"Found function from line {function_start+1} to {function_end+1}")

    # Fix the indentation in the function
    fixed_lines = lines[:function_start]

    # Add the function definition
    fixed_lines.append(lines[function_start])  # def enrich_referee_profiles
    fixed_lines.append(lines[function_start + 1])  # docstring
    fixed_lines.append(lines[function_start + 2])  # try:
    fixed_lines.append(lines[function_start + 3])  # print statement

    # Now fix the rest with proper indentation
    # Everything inside try should be indented one more level
    i = function_start + 4
    while i < function_end:
        line = lines[i]

        # Check current indentation
        if 'enriched_count = 0' in line:
            # This should be indented inside try
            fixed_lines.append('            enriched_count = 0\n')
        elif 'publication_count = 0' in line:
            fixed_lines.append('            publication_count = 0\n')
        elif 'for referee in manuscript.get' in line:
            fixed_lines.append('            for referee in manuscript.get(\'referees\', []):\n')
        elif 'if referee.get(\'name\'):' in line:
            fixed_lines.append('                if referee.get(\'name\'):\n')
        elif line.strip().startswith('print(f"   📚'):
            # This and everything after should be indented inside the if
            fixed_lines.append('                    ' + line.strip() + '\n')
        elif 'except Exception as e:' in line:
            # This is at the right level for try
            fixed_lines.append('        except Exception as e:\n')
        elif i > function_start + 10 and i < function_end - 10:
            # Main content inside the if statement
            if line.strip() and not line.strip().startswith('#'):
                # Add proper indentation for content inside if
                fixed_lines.append('                    ' + line.strip() + '\n')
            else:
                fixed_lines.append(line)
        else:
            # Keep as is
            fixed_lines.append(line)

        i += 1

    # Add the rest of the file
    fixed_lines.extend(lines[function_end:])

    # Write back
    with open(mf_path, 'w') as f:
        f.writelines(fixed_lines)

    print("✅ Fixed indentation in enrich_referee_profiles function")
else:
    print("❌ Could not find the function")