# Editorial Scripts

A unified system for extracting manuscript and referee data from editorial systems.

## 🚀 Quick Start

### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Credentials
```bash
python scripts/setup/secure_credential_manager.py --setup
```

### 3. Run Extraction
```bash
python run_extraction.py sicon --headless
```

## 📁 Directory Structure

```
editorial_scripts/
├── editorial_assistant/          # Main implementation
│   ├── core/                    # Core models and utilities
│   ├── extractors/              # Journal-specific extractors
│   ├── cli/                     # Command-line interface
│   └── utils/                   # Utilities and helpers
├── run_extraction.py            # Primary entry point
├── scripts/                      # Utility scripts
│   ├── setup/                   # Setup and configuration
│   ├── utilities/               # Helper scripts
│   └── testing/                 # Debug and test scripts
├── docs/                         # Documentation
│   ├── archives/                # Historical documentation
│   ├── reports/                 # System reports
│   └── specifications/          # Technical specifications
├── data/                         # Data outputs (gitignored)
│   ├── extractions/             # Extraction results
│   ├── exports/                 # Exported data
│   ├── pdfs/                    # Downloaded PDFs
│   └── logs/                    # System logs
├── config/                       # Configuration files
├── tests/                        # Test suite
├── database/                     # Database setup
└── venv/                         # Virtual environment (gitignored)
```

## 🎯 Supported Journals

### Active Journals (with current manuscripts)
- **SICON** - SIAM Journal on Control and Optimization
- **SIFIN** - SIAM Journal on Financial Mathematics  
- **MF** - Mathematical Finance (ScholarOne)
- **MOR** - Mathematics of Operations Research (ScholarOne)
- **FS** - Finance and Stochastics (Editorial Manager)

### Additional Journals (configured but no current manuscripts)
- **JOTA** - Journal of Optimization Theory and Applications
- **MAFE** - Mathematics and Financial Economics
- **NACO** - North American Congress on Optimization

## 📊 Features

- ✅ Automated manuscript extraction
- ✅ Referee data collection with email addresses
- ✅ PDF download of manuscripts and reports
- ✅ Browser pooling for concurrent processing
- ✅ Intelligent caching with change detection
- ✅ Comprehensive error handling and retry logic
- ✅ Performance monitoring and baseline testing

## 🔧 Configuration

### Environment Variables
Set your credentials using environment variables or the secure credential manager:
```bash
export ORCID_EMAIL="your.email@example.com"
export ORCID_PASSWORD="your_password"
```

### Configuration Files
- `config/credentials.yaml.example` - Example credential structure
- `.env.example` - Example environment configuration

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Test a specific journal:
```bash
python run_extraction.py sicon --headless
```

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [API Documentation](docs/api.md)
- [Development Guide](docs/development.md)

## 🛠️ Development

1. **Clone the repository**
2. **Create a virtual environment**
3. **Install dependencies**: `pip install -r requirements-dev.txt`
4. **Run tests**: `pytest`
5. **Check code quality**: `make lint`

## 📈 Current Baseline Performance (July 15, 2025)

### Active Journals
- **SICON**: 13 referees (8 accepted, 5 declined), 4 manuscripts, 3 cover letters, 4 referee reports (3 PDFs, 1 written)
- **SIFIN**: 14 referees (8 accepted, 6 declined), 4 manuscripts, 3 cover letters, 2 referee reports (1 PDF, 1 written)  
- **MF**: 6 referees (4 accepted, 2 declined), 2 manuscripts
- **MOR**: 7 referees (6 accepted, 1 declined), 3 manuscripts, 1 referee report
- **FS**: 6 referees (all accepted), 3 manuscripts, 1 PDF referee report

### Inactive Journals (no current manuscripts)
- **JOTA**: 0 manuscripts
- **MAFE**: 0 manuscripts  
- **NACO**: 0 manuscripts

### Overall Targets
- **Total Referees**: 46 (35 accepted, 11 declined)
- **Total Manuscripts**: 16
- **Total Cover Letters**: 6
- **Total Referee Reports**: 8 (5 PDFs, 3 written)
- **Success Rate**: 95%+ expected

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For issues or questions:
- Check the [troubleshooting guide](docs/troubleshooting.md)
- Review [known issues](docs/known-issues.md)
- Contact the development team

---

**Current Version**: 2.0.0 (Ultimate System)  
**Last Updated**: July 15, 2025