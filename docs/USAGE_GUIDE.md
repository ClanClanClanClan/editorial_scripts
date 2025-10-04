# Editorial Command Center - Complete Usage Guide

**Version**: 2.0.0
**Last Updated**: October 4, 2025

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Deployment](#deployment)
3. [Running Extractors](#running-extractors)
4. [API Usage](#api-usage)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Features](#advanced-features)

---

## 🚀 Quick Start

### First-Time Setup

```bash
# 1. Clone/Navigate to project
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts

# 2. Install dependencies (already done via Poetry)
poetry install

# 3. Set up Gmail OAuth (for FS extraction and 2FA)
# See docs/GMAIL_OAUTH_SETUP.md

# 4. Load credentials
source ~/.editorial_scripts/load_all_credentials.sh

# 5. Start everything
./deploy.sh start
```

### Daily Usage

```bash
# Start services
./deploy.sh start

# Check status
./deploy.sh status

# Run extraction
python3 -m src.ecc.cli extract MF --categories "Awaiting AE Recommendation"

# Stop services
./deploy.sh stop
```

---

## 🏗️ Deployment

### Production Deployment

```bash
# Start all services
./deploy.sh start

# Output:
# ✅ Infrastructure started
# ✅ API server started (PID: 12345)
# 🚀 ECC is running!
```

### What Gets Started

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Redis | 6380 | Caching |
| Prometheus | 9092 | Metrics |
| Grafana | 3002 | Dashboards |
| pgAdmin | 5050 | DB Admin |
| FastAPI | 8000 | REST API |

### Deployment Commands

```bash
./deploy.sh start     # Start everything
./deploy.sh stop      # Stop everything
./deploy.sh restart   # Restart all services
./deploy.sh status    # Show current status
./deploy.sh logs      # View recent logs
```

---

## 📦 Running Extractors

### Method 1: Direct Python (Recommended for Development)

```python
import asyncio
from src.ecc.adapters.journals.mf import MFAdapter

async def extract_mf():
    async with MFAdapter(headless=False) as adapter:
        # Authenticate
        if await adapter.authenticate():
            # Fetch manuscripts
            manuscripts = await adapter.fetch_manuscripts(
                categories=['Awaiting AE Recommendation']
            )

            # Extract details for each
            for ms in manuscripts:
                details = await adapter.extract_manuscript_details(ms.external_id)
                print(f"✅ {details.external_id}: {details.title}")
                print(f"   Authors: {len(details.authors)}")
                print(f"   Referees: {len(details.referees)}")

asyncio.run(extract_mf())
```

### Method 2: CLI (Production)

```bash
# Extract from specific journal
python3 -m src.ecc.cli extract MF \
    --categories "Awaiting AE Recommendation" \
    --headless \
    --output results/mf_extraction.json

# Extract from multiple categories
python3 -m src.ecc.cli extract MOR \
    --categories "Awaiting AE Decision,Under Review" \
    --enrich-orcid \
    --download-files
```

### Method 3: API (Scheduled/Automated)

```bash
# Trigger extraction via API
curl -X POST http://localhost:8000/api/journals/MF/extract \
    -H "Content-Type: application/json" \
    -d '{
        "categories": ["Awaiting AE Recommendation"],
        "enrich_orcid": true,
        "download_files": true
    }'

# Check extraction status
curl http://localhost:8000/api/tasks/{task_id}/status
```

---

## 🔧 API Usage

### Health Check

```bash
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "version": "2.0.0",
  "checks": {
    "database": true,
    "cache": true,
    "ai_service": true
  }
}
```

### List Journals

```bash
curl http://localhost:8000/api/journals/

# Response:
{
  "journals": [
    {
      "id": "MF",
      "name": "Mathematical Finance",
      "platform": "ScholarOne",
      "supported": true,
      "manuscript_count": 145
    },
    ...
  ]
}
```

### List Manuscripts

```bash
# Get manuscripts from MF
curl "http://localhost:8000/api/manuscripts/?journal_id=MF&page=1&page_size=20"

# Search manuscripts
curl "http://localhost:8000/api/manuscripts/?search=referee&status=under_review"
```

### Trigger Extraction

```bash
# Start extraction task
curl -X POST http://localhost:8000/api/journals/MF/extract \
    -H "Content-Type: application/json" \
    -d '{"categories": ["Awaiting AE Recommendation"]}'

# Response:
{
  "task_id": "abc-123-def",
  "status": "pending",
  "journal_id": "MF"
}
```

### API Documentation

Interactive API docs: http://localhost:8000/docs

---

## 📊 Monitoring

### Grafana Dashboards

1. Open http://localhost:3002
2. Login: `admin` / `admin`
3. Navigate to "Dashboards"
4. Select "Editorial Command Center - Overview"

**Key Metrics**:
- Extraction success rate
- Manuscripts per journal
- Average extraction duration
- Error rates
- API request rates
- Database connections
- Cache hit rates

### Prometheus Metrics

Direct metrics: http://localhost:9092

**Available Metrics**:
```
ecc_extractions_total{journal="MF",status="success"}
ecc_extraction_duration_seconds{journal="MF"}
ecc_manuscripts_total{journal="MF"}
fastapi_requests_total{method="GET",path="/api/journals/"}
```

### Logs

```bash
# API logs
tail -f logs/api.log

# Docker logs
docker-compose logs -f

# Specific service logs
docker logs ecc_postgres
docker logs ecc_redis
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Issue: Port 5432 already in use
# Solution: Stop Homebrew PostgreSQL
brew services stop postgresql@15
./deploy.sh restart
```

#### 2. Database Connection Failed

```bash
# Check if PostgreSQL is running
docker ps | grep ecc_postgres

# If not running:
docker-compose up -d postgres

# Test connection
docker exec ecc_postgres psql -U ecc_user -d ecc_db -c "SELECT 1"
```

#### 3. Credentials Not Found

```bash
# Reload credentials
source ~/.editorial_scripts/load_all_credentials.sh

# Verify loaded
env | grep -E "(MF_|MOR_|FS_)"

# If empty, check keychain
python3 verify_all_credentials.py
```

#### 4. Extraction Hangs

```bash
# Check browser manager (Selenium/Playwright)
# Run in non-headless mode to see what's happening
python3 -c "
import asyncio
from src.ecc.adapters.journals.mf import MFAdapter

async def debug():
    async with MFAdapter(headless=False) as adapter:  # ← headless=False
        await adapter.authenticate()

asyncio.run(debug())
"
```

#### 5. OAuth Token Expired

```bash
# Delete old token
rm config/gmail_token.pickle

# Re-authorize (see docs/GMAIL_OAUTH_SETUP.md)
python3 scripts/gmail_auth.py
```

### Debug Mode

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run extractor with debug output
from src.ecc.adapters.journals.mf import MFAdapter
adapter = MFAdapter(headless=False)
# ... your code
```

---

## 🔬 Advanced Features

### ORCID Enrichment

Automatically enrich author/referee data with ORCID profiles:

```python
async with MFAdapter() as adapter:
    manuscripts = await adapter.fetch_manuscripts(['Awaiting AE Recommendation'])

    for ms in manuscripts:
        details = await adapter.extract_manuscript_details(ms.external_id)

        # ORCID enrichment happens automatically
        for author in details.authors:
            if author.orcid:
                print(f"{author.name}: {author.orcid}")
                print(f"  Institution: {author.institution}")
                print(f"  Country: {author.country}")
```

### File Downloads

Download PDFs and supplementary files:

```python
async with MFAdapter() as adapter:
    manuscripts = await adapter.fetch_manuscripts(['Under Review'])

    for ms in manuscripts:
        details = await adapter.extract_manuscript_details(ms.external_id)

        # Download all files
        files = await adapter.download_manuscript_files(details)

        for file_path in files:
            print(f"Downloaded: {file_path}")
```

### AI Analysis

Use AI to analyze manuscripts:

```python
from src.ecc.interfaces.api.ai_analysis import analyze_manuscript

# Analyze referee match quality
analysis = await analyze_manuscript(
    manuscript_id=ms.id,
    analysis_type="referee_match"
)

print(f"Match score: {analysis.score}")
print(f"Recommendation: {analysis.recommendation}")
```

### Batch Processing

Process multiple journals in parallel:

```python
import asyncio

async def extract_all():
    journals = ['MF', 'MOR', 'SICON', 'SIFIN']

    tasks = [
        extract_journal(j, categories=['Awaiting AE Recommendation'])
        for j in journals
    ]

    results = await asyncio.gather(*tasks)
    return results

asyncio.run(extract_all())
```

### Scheduled Extraction

Set up cron job for automatic extraction:

```bash
# Edit crontab
crontab -e

# Add daily extraction at 2 AM
0 2 * * * cd /path/to/editorial_scripts && ./deploy.sh start && python3 -m src.ecc.cli extract MF --headless --quiet
```

---

## 📚 Additional Resources

- **Architecture Documentation**: `ECC_MIGRATION_COMPLETE.md`
- **Gmail OAuth Setup**: `docs/GMAIL_OAUTH_SETUP.md`
- **Project State**: `PROJECT_STATE_CURRENT.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **Test Suite**: `python3 tests/test_all_extractors.py`

---

## 🆘 Getting Help

### Check Logs

```bash
# API logs
tail -100 logs/api.log

# Service logs
./deploy.sh logs
```

### Run Tests

```bash
# Test all extractors
python3 tests/test_all_extractors.py

# Test specific extractor
python3 -c "
import asyncio
from src.ecc.adapters.journals.mf import MFAdapter
async def test():
    adapter = MFAdapter(headless=True)
    print(f'✅ MF adapter instantiated: {adapter.config}')
asyncio.run(test())
"
```

### Health Checks

```bash
# Check infrastructure
./deploy.sh status

# Check database
docker exec ecc_postgres psql -U ecc_user -d ecc_db -c "\dt"

# Check API
curl http://localhost:8000/health
```

---

**Happy Extracting! 🚀**
