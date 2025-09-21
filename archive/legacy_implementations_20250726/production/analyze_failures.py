import os
import sys

import yaml

sys.path.append(os.path.join(os.getcwd(), "src"))

from converter import eng2kor, kor2eng

with open("data/korean.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def norm(s):
    import unicodedata

    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:], strict=False)), set(zip(b, b[1:], strict=False))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


# Collect ALL failures
all_failures = []
for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))

    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)

    # Check eng→kor failure
    match = ko == ko_exp
    if not match:
        all_failures.append((k, "eng→kor", rr, ko_exp, ko))
        continue

    # Check roundtrip failure
    rr2 = kor2eng(ko, rr) or ""
    if dice(norm(rr), norm(rr2)) < 0.97:
        all_failures.append((k, "roundtrip", rr, ko, rr2))

print(f"Total failures: {len(all_failures)}")

# Skip known hard cases
skip_cases = [
    "RareInitials",
    "Ri_Young-Chul",
    "Huh_June",
    "Huh_Junghan",
    "Moon_Sukja",
    "Cheong_Munho",
]

eng_kor_new = []
for name, fail_type, inp, expected, got in all_failures:
    if fail_type == "eng→kor" and not any(skip in name for skip in skip_cases):
        eng_kor_new.append((name, inp, expected, got))

print(f"\nNew fixable Eng→Kor failures: {len(eng_kor_new)}")
for name, inp, expected, got in eng_kor_new[:15]:
    if got is None:
        print(f"  {name}: {inp} -> None (missing mapping)")
    else:
        print(f"  {name}: {inp} -> expected {expected}, got {got}")
