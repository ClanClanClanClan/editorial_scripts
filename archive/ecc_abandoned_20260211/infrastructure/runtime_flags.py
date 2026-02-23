"""Runtime flags/toggles for optional dependencies.

Usage:
  - If ECC_REAL_DEPS=1, missing deps should raise errors rather than using stubs.
"""

import os


def use_real_deps() -> bool:
    return os.getenv("ECC_REAL_DEPS", "0").strip() in ("1", "true", "TRUE", "yes", "YES")
