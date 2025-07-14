# Database Setup Guide

This directory contains all the necessary files to set up the PostgreSQL database for the Editorial Scripts system.

## Prerequisites

1. PostgreSQL 13+ installed and running
2. Python environment with asyncpg installed
3. Database admin credentials

## Installation Options

### Option 1: Using Docker (Recommended for Development)

```bash
# Start PostgreSQL container
docker run -d \
  --name editorial-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=editorial_scripts \
  -e POSTGRES_USER=postgres \
  -p 5432:5432 \
  postgres:13

# Wait for container to start, then run setup
python database/setup_simple.py
```

### Option 2: Local PostgreSQL Installation

```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# CentOS/RHEL
sudo yum install postgresql postgresql-server
sudo systemctl start postgresql
```

## Database Setup Steps

### 1. Run Database Setup Script

```bash
# Activate virtual environment
source venv_clean/bin/activate

# Run setup with default settings
python database/setup_simple.py

# Or with custom settings
python database/setup_simple.py \
  --admin-password your_postgres_password \
  --db-name editorial_scripts \
  --db-user editorial \
  --db-password your_secure_password
```

### 2. Verify Setup

The setup script will automatically verify that:
- Database and user are created
- All tables are created successfully
- Basic queries work
- Indexes and constraints are in place

### 3. Load Sample Data (Optional)

```bash
# Load test data for development
python database/sample_data.py
```

## Database Schema

The system uses the following main tables:

### Core Tables
- **manuscripts**: Manuscript submissions and metadata
- **referees**: Referee information and expertise
- **reviews**: Review assignments and outcomes

### Analytics Tables
- **referee_analytics**: Referee performance metrics
- **journal_analytics**: Journal-specific statistics
- **ai_analysis_cache**: Cached AI analysis results

### System Tables
- **system_metrics**: System performance metrics

## Configuration

Update your `.env` file with the database connection details:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://editorial:password@localhost:5432/editorial_scripts
DB_HOST=localhost
DB_PORT=5432
DB_NAME=editorial_scripts
DB_USER=editorial
DB_PASSWORD=your_secure_password
```

## Migrations

The system uses Alembic for database migrations:

```bash
# Initialize Alembic (first time only)
alembic init migrations

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## Backup and Restore

### Backup
```bash
pg_dump -h localhost -U editorial editorial_scripts > backup.sql
```

### Restore
```bash
psql -h localhost -U editorial editorial_scripts < backup.sql
```

## Troubleshooting

### Connection Issues
1. Ensure PostgreSQL is running: `sudo systemctl status postgresql`
2. Check if port 5432 is open: `netstat -an | grep 5432`
3. Verify user permissions: `psql -U postgres -c "\\du"`

### Permission Issues
```sql
-- Grant additional permissions if needed
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO editorial;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO editorial;
```

### Reset Database
```bash
# Drop and recreate database
python database/setup_simple.py --reset
```

## Schema Diagram

```
manuscripts
├── id (UUID, PK)
├── title
├── abstract
├── journal_code (ENUM)
└── ai_analysis (JSONB)

referees
├── id (UUID, PK)
├── name
├── expertise_areas (TEXT[])
├── journals (ENUM[])
└── quality_score

reviews
├── id (UUID, PK)
├── manuscript_id (FK)
├── referee_id (FK)
├── decision (ENUM)
└── quality_score

referee_analytics
├── id (UUID, PK)
├── referee_id (FK)
├── journal_code (ENUM)
├── period_start/end
└── performance_metrics (JSONB)
```

## Performance Tuning

The schema includes optimized indexes for:
- Manuscript searches by journal and status
- Referee expertise matching
- Analytics queries by time periods
- AI cache lookups

## Security Considerations

1. Use strong passwords for database users
2. Limit network access to database
3. Enable SSL connections in production
4. Regular security updates for PostgreSQL
5. Monitor database access logs