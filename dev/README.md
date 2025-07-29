# 🧪 Development Environment

## 🚨 IMPORTANT: DEVELOPMENT ISOLATION

**All development work MUST be contained in this `/dev/` directory to prevent polluting the clean codebase.**

## 📁 Structure

```
dev/
├── mf/                    # MF extractor development
│   ├── tests/            # All MF test files
│   ├── outputs/          # All MF extraction results  
│   ├── logs/             # All MF debug logs
│   ├── debug/            # Debug HTML files, screenshots
│   └── run_mf_dev.py     # Development runner
├── sicon/                # SICON development (future)
├── mor/                  # MOR development (future)  
└── README.md             # This file
```

## 🎯 Development Rules

### ✅ DO:
- Create all test files in `dev/{journal}/tests/`
- Save all results to `dev/{journal}/outputs/`
- Store all logs in `dev/{journal}/logs/`
- Use development runners in `dev/{journal}/`
- Work iteratively within dev environment

### ❌ DON'T:
- Create test files in project root
- Save results to project root 
- Create debug files outside dev/
- Pollute the clean codebase structure
- Mix development with production code

## 🚀 Usage

### MF Development
```bash
cd dev/mf
python3 run_mf_dev.py  # Uses isolated environment
```

### Running Tests
```bash
cd dev/mf/tests
python3 test_whatever.py  # All contained
```

### Results Location
All outputs automatically go to:
- `dev/mf/outputs/` - Extraction results
- `dev/mf/logs/` - Debug logs  
- `dev/mf/debug/` - HTML files, screenshots

## 📋 Development Workflow

1. **Start Development**: Work in `dev/{journal}/`
2. **Test Iteratively**: All outputs contained
3. **Debug Issues**: Files saved to `debug/`
4. **Ready for Production**: Move to `production/`
5. **Clean Development**: Remove dev files when done

## 🧹 Cleanup

When development is complete:
```bash
rm -rf dev/mf/  # Remove entire development environment
```

The production code remains clean and unaffected!