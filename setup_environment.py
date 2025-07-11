#!/usr/bin/env python3
"""
Setup script to fix environment and install dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {description}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Setup the environment"""
    print("🚀 EDITORIAL SCRIPTS ENVIRONMENT SETUP")
    print("=" * 60)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Use system Python for setup
    python_cmd = "/usr/bin/python3"
    
    # Create requirements.txt with all needed dependencies
    requirements = """# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.1
pydantic==2.5.0
pydantic[email]
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.12.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Monitoring
prometheus-fastapi-instrumentator==6.1.0

# Redis cache (optional for now)
# redis==5.0.1
# aioredis==2.0.1

# Utilities
python-dotenv==1.0.0
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    print("✅ Created requirements.txt")
    
    # Install dependencies using system pip
    print("\n📦 Installing dependencies...")
    install_cmd = f"{python_cmd} -m pip install -r requirements.txt"
    
    if not run_command(install_cmd, "Installing Python packages"):
        print("\n⚠️  Trying with --user flag...")
        install_cmd_user = f"{python_cmd} -m pip install --user -r requirements.txt"
        if not run_command(install_cmd_user, "Installing Python packages (user)"):
            print("\n❌ Failed to install dependencies")
            return False
    
    # Create .env file if it doesn't exist
    env_file = project_dir / ".env"
    if not env_file.exists():
        env_content = """# Database
DATABASE_URL=postgresql://dylanpossamai:@localhost:5432/editorial_scripts
DB_HOST=localhost
DB_PORT=5432
DB_USER=dylanpossamai
DB_PASSWORD=
DB_NAME=editorial_scripts

# API Settings
ENVIRONMENT=development
DEBUG=true
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Redis (optional)
REDIS_URL=redis://localhost:6379

# OpenAI (for future AI features)
OPENAI_API_KEY=your-api-key-here
"""
        with open(env_file, "w") as f:
            f.write(env_content)
        print("✅ Created .env file")
    
    # Create a simple run script
    run_script = """#!/usr/bin/env python3
import subprocess
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run uvicorn
subprocess.run([
    sys.executable, "-m", "uvicorn", 
    "src.api.main:app", 
    "--reload", 
    "--host", "0.0.0.0", 
    "--port", "8000"
])
"""
    
    with open("run_api_direct.py", "w") as f:
        f.write(run_script)
    os.chmod("run_api_direct.py", 0o755)
    print("✅ Created run_api_direct.py")
    
    # Check if PostgreSQL is accessible
    print("\n🔍 Checking PostgreSQL connection...")
    try:
        check_pg = f"{python_cmd} -c \"import psycopg2; conn = psycopg2.connect('postgresql://dylanpossamai:@localhost:5432/editorial_scripts'); print('Connected!'); conn.close()\""
        run_command(check_pg, "PostgreSQL connection test")
    except:
        print("⚠️  PostgreSQL connection failed - make sure PostgreSQL is running")
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE!")
    print("="*60)
    print("\nTo run the API:")
    print("  /usr/bin/python3 run_api_direct.py")
    print("\nTo run tests:")
    print("  /usr/bin/python3 test_api_quick.py")
    print("  /usr/bin/python3 test_api_referee_paranoid.py")
    

if __name__ == "__main__":
    main()