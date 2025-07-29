# 🚀 Editorial Scripts - Setup Guide

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (for production)
- Redis (optional, for caching)
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd editorial_scripts
```

### 2. Set Up Environment

#### Option A: Using Make (Recommended)
```bash
make setup
```

#### Option B: Using Scripts
```bash
chmod +x setup_environment.sh
./setup_environment.sh
```

#### Option C: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/editorial_scripts

# API Keys
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-secret-key-here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### 4. Set Up Database

```bash
# Create database
createdb editorial_scripts

# Run migrations
alembic upgrade head
```

### 5. Test Installation

```bash
# Test all imports
python test_all_imports.py

# Run tests
pytest tests/

# Or using Make
make test-imports
make test
```

### 6. Run the Application

```bash
# Start API server
uvicorn src.api.main:app --reload

# Or using Make
make run
```

The API will be available at `http://localhost:8000`

## Development Workflow

### Common Commands

```bash
# Format code
make format

# Run linting
make lint

# Run all checks
make check

# Clean environment
make clean

# Full refresh
make refresh
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_ai_services.py

# With coverage
pytest --cov=src --cov-report=html

# Specific markers
pytest -m "not slow"
```

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Import Errors

If you encounter import errors:

1. Ensure virtual environment is activated:
   ```bash
   which python  # Should show venv/bin/python
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

3. Check Python path:
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   ```

### Database Connection Issues

1. Check PostgreSQL is running:
   ```bash
   pg_isready
   ```

2. Verify connection string in `.env`

3. Test connection:
   ```bash
   python -c "from src.infrastructure.database.engine import get_engine; print('Connected!')"
   ```

### Missing Dependencies

Run the import test:
```bash
python test_all_imports.py
```

This will show exactly which dependencies are missing.

## Project Structure

```
editorial_scripts/
├── src/                    # Main application code
│   ├── api/               # FastAPI application
│   ├── ai/                # AI services
│   ├── core/              # Core domain logic
│   └── infrastructure/    # Database, external services
├── analytics/             # Analytics modules
├── journals/              # Journal-specific implementations
├── tests/                 # Test suite
├── alembic/              # Database migrations
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── setup_environment.sh   # Setup script
├── clean_environment.sh   # Cleanup script
├── test_all_imports.py    # Import testing
├── Makefile              # Development commands
└── pyproject.toml        # Python project configuration
```

## Advanced Configuration

### Using Docker

```bash
# Build image
docker build -t editorial-scripts .

# Run container
docker-compose up
```

### Production Deployment

1. Use production requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Set production environment:
   ```env
   ENVIRONMENT=production
   DEBUG=false
   ```

3. Run with gunicorn:
   ```bash
   gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## Getting Help

- Check logs in `logs/` directory
- Run tests with `-v` for verbose output
- Use `make help` for available commands
- Review `PHASE_1_COMPLETION_REPORT.md` for architecture details

## License

See LICENSE file for details.