# 🧹 GIANT CLEANUP PLAN - EDITORIAL SCRIPTS

**Date**: July 15, 2025
**Current Size**: 1.8GB → **Target Size**: ~50MB
**Files to Remove**: ~23,000+ → **Target**: ~200

---

## 🎯 CLEANUP OBJECTIVES

1. **ONE implementation** - Keep only `editorial_scripts_ultimate/`
2. **ONE virtual environment** - Keep only `venv/`
3. **ONE documentation set** - Consolidate into `docs/`
4. **ONE data directory** - Merge all into `data/`
5. **ZERO clutter** - Archive or delete everything else

---

## 📋 PHASE 1: BACKUP CRITICAL FILES

### **Before we destroy anything, backup:**
```bash
# Create backup directory with timestamp
mkdir -p ~/editorial_scripts_backup_20250715

# Backup any credentials or configs
cp .env ~/editorial_scripts_backup_20250715/
cp config/*.yaml ~/editorial_scripts_backup_20250715/
cp -r editorial_scripts_ultimate ~/editorial_scripts_backup_20250715/

# Create a tar archive of current state (just in case)
tar -czf ~/editorial_scripts_backup_20250715/full_backup.tar.gz .
```

---

## 🗑️ PHASE 2: MASSIVE DELETIONS

### **A. Delete Virtual Environments** (Save 1.5GB+)
```bash
# Remove extra venvs (keep only venv/)
rm -rf venv_fresh/
rm -rf .venv*/  # Any hidden venvs

# Clean the kept venv of caches
find venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find venv -name "*.pyc" -delete
```

### **B. Delete Test Result Directories** (Save 100MB+)
```bash
# All those ultra_enhanced directories
rm -rf ultra_enhanced_sicon_20250713_*/
rm -rf ultra_enhanced_sifin_20250713_*/
rm -rf working_siam_sifin_20250713_*/
rm -rf crosscheck_results_20250713_*/
rm -rf verification_results/
rm -rf test_results_*/
```

### **C. Delete Competing Implementations** (Save 50MB+)
```bash
# Archive these first if you want
tar -czf ~/editorial_scripts_backup_20250715/old_implementations.tar.gz \
    final_implementation/ \
    production/ \
    unified_system/ \
    src/

# Then delete
rm -rf final_implementation/
rm -rf production/
rm -rf unified_system/
rm -rf src/  # If not actively used
```

### **D. Delete Cache and Temporary Directories**
```bash
rm -rf __pycache__/
rm -rf cache/
rm -rf test_cache/
rm -rf ai_analysis_cache/
rm -rf CLEANUP_STAGING/
rm -rf test_storage/
rm -rf test_pdfs/
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete
```

### **E. Delete Legacy and Backup Directories**
```bash
rm -rf legacy_20250710_*/
rm -rf downloads/  # If empty or has old data
rm -rf attachments/  # If empty or has old data
```

---

## 📁 PHASE 3: ORGANIZE REMAINING FILES

### **A. Create Proper Directory Structure**
```bash
# Create organized structure
mkdir -p scripts/setup
mkdir -p scripts/utilities
mkdir -p scripts/testing
mkdir -p docs/archives
mkdir -p docs/reports
mkdir -p docs/specifications
```

### **B. Move Scripts to Proper Locations**
```bash
# Move setup scripts
mv setup_*.py scripts/setup/
mv secure_credential_manager.py scripts/setup/
mv store_credentials_securely.py scripts/setup/

# Move utility scripts
mv run_*.py scripts/utilities/
mv extract.py scripts/utilities/
mv debug_*.py scripts/testing/

# Move any other .py files in root
mv *.py scripts/utilities/ 2>/dev/null || true
```

### **C. Consolidate Documentation**
```bash
# Move all audit/plan documents
mv *AUDIT*.md docs/archives/
mv *PLAN*.md docs/archives/
mv *REPORT*.md docs/reports/
mv *SUMMARY*.md docs/reports/
mv *STATUS*.md docs/reports/

# Move specification documents
mv *SPECIFICATION*.md docs/specifications/
mv *SPECS*.md docs/specifications/

# Keep only essential docs in root
# Keep: README.md, LICENSE, CONTRIBUTING.md (if exists)
```

### **D. Consolidate Data Directories**
```bash
# Merge all data directories
mkdir -p data/extractions
mkdir -p data/exports
mkdir -p data/pdfs
mkdir -p data/logs

# Move content from scattered directories
mv extractions/* data/extractions/ 2>/dev/null || true
mv output/* data/exports/ 2>/dev/null || true
mv logs/* data/logs/ 2>/dev/null || true
mv final_logs/* data/logs/ 2>/dev/null || true

# Remove empty directories
rmdir extractions output logs final_logs 2>/dev/null || true
```

---

## 🗜️ PHASE 4: ARCHIVE OLD CONTENT

### **Compress the archive folder**
```bash
# The archive folder is already 226MB
cd archive
tar -czf ../archive_compressed_20250715.tar.gz .
cd ..
rm -rf archive/
mkdir archive
mv archive_compressed_20250715.tar.gz archive/
echo "Compressed archives from before 2025-07-15" > archive/README.md
```

---

## 🔧 PHASE 5: FIX GIT TRACKING

### **Create Proper .gitignore**
```bash
cat > .gitignore << 'EOF'
# Virtual Environments
venv/
venv_*/
.venv*/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.*
!.env.example
credentials.yaml
!credentials.yaml.example

# Data and Outputs
data/
!data/.gitkeep
*.log
*.pdf
*.csv
*.json
!requirements*.json
!package*.json

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/
.hypothesis/

# Temporary
tmp/
temp/
cache/
*_cache/
EOF
```

### **Clean Git Status**
```bash
# Add gitignore
git add .gitignore

# Remove tracked files that should be ignored
git rm -r --cached venv/ 2>/dev/null || true
git rm -r --cached __pycache__/ 2>/dev/null || true
git rm -r --cached *.pyc 2>/dev/null || true
git rm -r --cached .env 2>/dev/null || true

# Remove deleted files from git
git add -u
```

---

## 📝 PHASE 6: CREATE CLEAN DOCUMENTATION

### **Create New README.md**
```markdown
# Editorial Scripts

A unified system for extracting manuscript and referee data from editorial systems.

## Quick Start

1. **Setup Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Credentials**
   ```bash
   python scripts/setup/secure_credential_manager.py --setup
   ```

3. **Run Extraction**
   ```bash
   cd editorial_scripts_ultimate
   python main.py sicon --test
   ```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [API Documentation](docs/api.md)
- [Development Guide](docs/development.md)

## Directory Structure

```
editorial_scripts/
├── editorial_scripts_ultimate/   # Main implementation
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
├── data/                         # Data outputs (git ignored)
├── tests/                        # Test suite
├── config/                       # Configuration files
└── venv/                         # Virtual environment (git ignored)
```
```

---

## 🎯 FINAL STRUCTURE

After cleanup, you should have:

```
editorial_scripts/
├── editorial_scripts_ultimate/   # The ONE implementation (50MB)
│   ├── core/
│   ├── extractors/
│   ├── main.py
│   └── requirements.txt
├── scripts/                      # All utilities organized
│   ├── setup/
│   ├── utilities/
│   └── testing/
├── docs/                         # All documentation
│   ├── archives/
│   ├── reports/
│   ├── specifications/
│   └── *.md (guides)
├── data/                         # All data (gitignored)
│   ├── extractions/
│   ├── exports/
│   ├── pdfs/
│   └── logs/
├── config/                       # Configuration
│   ├── credentials.yaml.example
│   └── settings.yaml
├── tests/                        # Test suite
├── archive/                      # Compressed old stuff
│   ├── archive_compressed_20250715.tar.gz
│   └── README.md
├── venv/                         # Virtual environment
├── .env.example                  # Example environment
├── .gitignore                    # Proper ignores
├── README.md                     # Clear documentation
├── requirements.txt              # Dependencies
└── Makefile                      # Automation commands
```

---

## ⚡ QUICK CLEANUP COMMANDS

**Run these in order:**

```bash
# 1. Backup
mkdir -p ~/editorial_scripts_backup_20250715
cp -r editorial_scripts_ultimate ~/editorial_scripts_backup_20250715/
tar -czf ~/editorial_scripts_backup_20250715/full_backup.tar.gz .

# 2. Nuclear delete
rm -rf venv_fresh/ ultra_enhanced_* working_siam_* crosscheck_* \
       final_implementation/ production/ unified_system/ src/ \
       test_results_* verification_results/ __pycache__/ cache/ \
       test_cache/ ai_analysis_cache/ CLEANUP_STAGING/ test_storage/ \
       test_pdfs/ legacy_* downloads/ attachments/

# 3. Clean caches
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete

# 4. Organize
mkdir -p scripts/{setup,utilities,testing} docs/{archives,reports,specifications}
mv setup_*.py secure_credential_manager.py store_credentials_securely.py scripts/setup/
mv run_*.py extract.py debug_*.py scripts/utilities/
mv *AUDIT*.md *PLAN*.md docs/archives/
mv *REPORT*.md *SUMMARY*.md *STATUS*.md docs/reports/

# 5. Check result
du -sh .
ls -la
```

---

## ⏱️ ESTIMATED TIME: 10 minutes

## 💾 SPACE SAVED: ~1.75GB (97% reduction!)

## 🎉 RESULT: A clean, organized, single-source-of-truth codebase!
