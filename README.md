# Editorial Assistant 📚

A professional-grade system for extracting and managing referee data from academic journal submission systems.

## Features ✨

- **Multi-Journal Support**: Extract data from 8 major academic journals (MF, MOR, JFE, MS, RFS, RAPS, JF, JFI)
- **Robust Extraction**: Comprehensive error handling with retry mechanisms and checkpoint recovery
- **PDF Management**: Automatic download and organization of manuscript and referee report PDFs
- **Data Analysis**: Built-in conflict of interest detection and statistical analysis
- **Professional CLI**: Beautiful command-line interface with progress tracking
- **Extensible Architecture**: Easy to add support for new journals and platforms

## Quick Start 🚀

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/editorial-assistant.git
cd editorial-assistant

# Install the package
pip install -e .
```

### Configuration

1. Initialize configuration files:
```bash
editorial-assistant init
```

2. Edit `config/credentials.yaml` with your journal credentials:
```yaml
journals:
  MF:
    username: "your.email@example.com"
    password: "your_password"
  MOR:
    username: "your.email@example.com"
    password: "your_password"
```

3. Verify configuration:
```bash
editorial-assistant config
```

### Basic Usage

Extract data from a single journal:
```bash
editorial-assistant extract MF
```

Extract from all configured journals:
```bash
editorial-assistant extract --all
```

Generate a report:
```bash
editorial-assistant report MF --format md
```

## Architecture 🏗️

```
editorial_assistant/
├── core/               # Core functionality (browser, PDF, data models)
├── extractors/         # Platform-specific extractors
├── parsers/           # Data parsing utilities
├── handlers/          # External integrations (email, storage)
├── analytics/         # Analysis and reporting tools
├── utils/             # Utility functions
└── cli/               # Command-line interface
```

## Supported Journals 📖

| Journal | Code | Platform | Status |
|---------|------|----------|---------|
| Mathematical Finance | MF | ScholarOne | ✅ Fully Supported |
| Mathematics of Operations Research | MOR | ScholarOne | ✅ Fully Supported |
| Journal of Financial Economics | JFE | Editorial Manager | 🚧 In Development |
| Management Science | MS | ScholarOne | 🚧 In Development |
| Review of Financial Studies | RFS | ScholarOne | 🚧 In Development |
| Review of Asset Pricing Studies | RAPS | ScholarOne | 🚧 In Development |
| Journal of Finance | JF | Editorial Manager | 🚧 In Development |
| Journal of Financial Intermediation | JFI | Editorial Manager | 🚧 In Development |

## Advanced Features 🔧

### Headless Mode
Run extractions without displaying the browser:
```bash
editorial-assistant extract MF --headless
```

### Checkpoint Recovery
The system automatically saves checkpoints during extraction. If interrupted, it will resume from the last checkpoint:
```bash
editorial-assistant extract MOR --checkpoint-dir ./checkpoints
```

### Parallel Extraction
Extract multiple journals simultaneously:
```bash
editorial-assistant extract --all --parallel
```

### Data Analysis
Analyze extracted data for conflicts of interest:
```bash
editorial-assistant analyze results.json --conflicts
```

## Data Output 📊

Extracted data is saved in structured JSON format:
```json
{
  "journal": {
    "code": "MF",
    "name": "Mathematical Finance"
  },
  "manuscripts": [
    {
      "manuscript_id": "MAFI-2024-0167",
      "title": "Competitive optimal portfolio selection",
      "referees": [
        {
          "name": "Smith, John",
          "institution": "Harvard University",
          "status": "agreed",
          "dates": {
            "invited": "2025-05-01",
            "agreed": "2025-05-03",
            "due": "2025-07-30"
          }
        }
      ]
    }
  ]
}
```

## Development 💻

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black editorial_assistant/
flake8 editorial_assistant/
```

### Adding a New Journal

1. Add journal configuration to `config/journals.yaml`
2. Create extractor in `editorial_assistant/extractors/implementations/`
3. Update CLI to recognize the new journal

## Troubleshooting 🔍

### Chrome Driver Issues
If you encounter Chrome driver problems:
1. Ensure Chrome is installed and up to date
2. The system will automatically download compatible drivers
3. Use `--visible` flag to debug browser interactions

### 2FA Authentication
The system integrates with Gmail API for automatic 2FA code retrieval:
1. Set up Gmail API credentials
2. Configure in `config/credentials.yaml`
3. The system will automatically handle verification codes

## Contributing 🤝

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact the maintainers
- Check the documentation

---

Built with ❤️ for the academic community