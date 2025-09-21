#!/usr/bin/env python3
"""
MF Extractor Development Runner

This script runs the MF extractor in a contained development environment,
ensuring all outputs, logs, and debug files are isolated from the main codebase.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add production source to path
sys.path.insert(0, "../../production/src")


def setup_dev_environment():
    """Set up isolated development environment"""
    dev_dir = Path(__file__).parent

    # Ensure directories exist
    (dev_dir / "outputs").mkdir(exist_ok=True)
    (dev_dir / "logs").mkdir(exist_ok=True)
    (dev_dir / "debug").mkdir(exist_ok=True)
    (dev_dir / "tests").mkdir(exist_ok=True)

    return dev_dir


def run_mf_extractor(dev_dir):
    """Run MF extractor with contained outputs"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set environment variables for contained execution
    env = os.environ.copy()
    env.update(
        {
            "MF_OUTPUT_DIR": str(dev_dir / "outputs"),
            "MF_LOG_DIR": str(dev_dir / "logs"),
            "MF_DEBUG_DIR": str(dev_dir / "debug"),
            "MF_DEV_MODE": "true",
            "MF_SESSION_ID": f"dev_{timestamp}",
        }
    )

    print("🧪 Running MF Extractor in Development Mode")
    print(f"📁 Outputs: {dev_dir / 'outputs'}")
    print(f"📋 Logs: {dev_dir / 'logs'}")
    print(f"🐛 Debug: {dev_dir / 'debug'}")
    print(f"🔗 Session: dev_{timestamp}")
    print("-" * 50)

    # Run extractor with contained environment
    try:
        result = subprocess.run(
            [sys.executable, "../../production/src/extractors/mf_extractor.py"],
            env=env,
            cwd=str(dev_dir),
        )

        if result.returncode == 0:
            print("✅ MF extraction completed successfully")
            print(f"📂 Check outputs in: {dev_dir / 'outputs'}")
        else:
            print(f"❌ MF extraction failed with code: {result.returncode}")
            print(f"📋 Check logs in: {dev_dir / 'logs'}")

    except Exception as e:
        print(f"💥 Error running MF extractor: {e}")


def main():
    """Main development runner"""
    print("🧪 MF Extractor Development Environment")
    print("=" * 50)

    # Setup isolated environment
    dev_dir = setup_dev_environment()
    print(f"📁 Development directory: {dev_dir}")

    # Check if production extractor exists
    extractor_path = Path("../../production/src/extractors/mf_extractor.py")
    if not extractor_path.exists():
        print(f"❌ Production MF extractor not found: {extractor_path}")
        sys.exit(1)

    # Run in development mode
    run_mf_extractor(dev_dir)


if __name__ == "__main__":
    main()
