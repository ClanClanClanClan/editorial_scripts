# Editorial Scripts Refactoring Plan 2025

## Executive Summary

This document outlines a comprehensive refactoring strategy to transform the editorial scripts codebase from its current state into a clean, maintainable, and scalable system aligned with modern software engineering practices.

## Current State Analysis

### File Organization Issues
- **200+ files in root directory** causing navigation difficulties
- **50+ debug scripts** (debug_*.py) scattered throughout
- **20+ SIAM extractor variants** showing iterative development without cleanup
- **Duplicate journal implementations** in `/journals/` and `/editorial_assistant/extractors/`
- **Test files mixed with production code** instead of organized test structure

### Technical Debt
- Using **Selenium** instead of modern **Playwright** (as specified in v2.0 specs)
- **SQLite** database instead of production-ready **PostgreSQL**
- **Synchronous code** where async operations would improve performance
- **Hardcoded values** throughout (credentials, paths, configurations)
- **No dependency injection** making testing and maintenance difficult

### Architecture Problems
- **No clear separation of concerns** - business logic mixed with infrastructure
- **Multiple competing base classes** (base.py, enhanced_base.py, siam_base.py)
- **Inconsistent patterns** across different journal implementations
- **Missing abstraction layers** between domain logic and external services

## Refactoring Strategy

### Phase 1: Immediate Cleanup (Week 1)

#### 1.1 Archive Obsolete Files
```bash
mkdir -p archive/2025_cleanup/{debug,legacy_extractors,old_tests}
mv debug_*.py archive/2025_cleanup/debug/
mv extract_siam_*.py archive/2025_cleanup/legacy_extractors/
mv test_*.py archive/2025_cleanup/old_tests/  # Keep only organized tests
```

#### 1.2 Organize Directory Structure
```
editorial_scripts/
├── src/
│   ├── domain/           # Business entities and rules
│   │   ├── models/      # Manuscript, Referee, Review
│   │   ├── services/    # Business logic
│   │   └── exceptions/  # Domain exceptions
│   ├── application/     # Use cases
│   │   ├── commands/    # Write operations
│   │   ├── queries/     # Read operations
│   │   └── handlers/    # Command/Query handlers
│   ├── infrastructure/  # External services
│   │   ├── scrapers/    # Web automation (Playwright)
│   │   ├── database/    # PostgreSQL repositories
│   │   ├── ai/          # AI service integrations
│   │   └── config/      # Configuration management
│   └── presentation/    # User interfaces
│       ├── api/         # REST API (FastAPI)
│       ├── cli/         # Command line (Typer)
│       └── web/         # Web dashboard
├── tests/
│   ├── unit/           # Domain logic tests
│   ├── integration/    # Service integration tests
│   ├── e2e/           # End-to-end tests
│   └── fixtures/      # Test data and utilities
├── scripts/           # Utility scripts
├── docs/             # Documentation
└── deploy/           # Deployment configurations
```

#### 1.3 Consolidate Journal Implementations
- Merge `/journals/` and `/editorial_assistant/extractors/`
- Create single source of truth for each journal
- Remove duplicate implementations

### Phase 2: Clean Architecture Implementation (Weeks 2-4)

#### 2.1 Domain Layer
```python
# src/domain/models/manuscript.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

@dataclass
class Manuscript:
    """Core manuscript entity - no external dependencies"""
    id: UUID
    journal_id: str
    external_id: str
    title: str
    authors: List['Author']
    submission_date: datetime
    status: 'ManuscriptStatus'

    def assign_referee(self, referee: 'Referee') -> None:
        """Business rule: manuscript assignment logic"""
        if self.status != ManuscriptStatus.AWAITING_REFEREE:
            raise InvalidStateError("Cannot assign referee in current state")
        # Domain logic here

# src/domain/services/referee_matcher.py
class RefereeMatcher:
    """Domain service for matching referees to manuscripts"""

    def find_best_matches(
        self,
        manuscript: Manuscript,
        available_referees: List[Referee]
    ) -> List[RefereeMatch]:
        """Pure business logic - no external dependencies"""
        # Matching algorithm here
```

#### 2.2 Application Layer
```python
# src/application/commands/assign_referee.py
from dataclasses import dataclass
from uuid import UUID

@dataclass
class AssignRefereeCommand:
    manuscript_id: UUID
    referee_id: UUID
    due_date: datetime

# src/application/handlers/assign_referee_handler.py
class AssignRefereeHandler:
    def __init__(
        self,
        manuscript_repo: ManuscriptRepository,
        referee_repo: RefereeRepository,
        notification_service: NotificationService
    ):
        self.manuscript_repo = manuscript_repo
        self.referee_repo = referee_repo
        self.notification_service = notification_service

    async def handle(self, command: AssignRefereeCommand) -> None:
        manuscript = await self.manuscript_repo.get(command.manuscript_id)
        referee = await self.referee_repo.get(command.referee_id)

        manuscript.assign_referee(referee)

        await self.manuscript_repo.save(manuscript)
        await self.notification_service.send_assignment(referee, manuscript)
```

#### 2.3 Infrastructure Layer
```python
# src/infrastructure/scrapers/playwright_scraper.py
from playwright.async_api import async_playwright
from src.domain.ports import JournalScraper

class PlaywrightJournalScraper(JournalScraper):
    """Playwright implementation of journal scraper port"""

    async def login(self, credentials: Credentials) -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # Modern async scraping

# src/infrastructure/database/sqlalchemy_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.ports import ManuscriptRepository

class SQLAlchemyManuscriptRepository(ManuscriptRepository):
    """PostgreSQL implementation of manuscript repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID) -> Manuscript:
        # Async database query
```

### Phase 3: Technology Stack Modernization (Weeks 5-6)

#### 3.1 Migration Checklist
- [ ] Selenium → Playwright migration
- [ ] SQLite → PostgreSQL migration
- [ ] Sync → Async operations
- [ ] Add comprehensive type hints
- [ ] Implement dependency injection
- [ ] Add structured logging
- [ ] Create configuration management

#### 3.2 Key Migrations

**Playwright Migration:**
```python
# Old (Selenium)
from selenium import webdriver
driver = webdriver.Chrome()
driver.get(url)
element = driver.find_element(By.ID, "login")

# New (Playwright)
from playwright.async_api import async_playwright
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto(url)
    await page.click("#login")
```

**Database Migration:**
```python
# Old (SQLite)
conn = sqlite3.connect('referees.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM referees")

# New (PostgreSQL + AsyncSQLAlchemy)
async with AsyncSession(engine) as session:
    result = await session.execute(
        select(Referee).where(Referee.active == True)
    )
    referees = result.scalars().all()
```

### Phase 4: Performance & Quality (Weeks 7-8)

#### 4.1 Performance Optimizations
- **Connection pooling** for database and browser instances
- **Redis caching** for frequently accessed data
- **Concurrent processing** for multiple journals
- **Query optimization** with proper indexes
- **Lazy loading** for large datasets

#### 4.2 Testing Strategy
```python
# tests/unit/domain/test_manuscript.py
def test_manuscript_assignment_rules():
    """Test pure domain logic"""
    manuscript = Manuscript(status=ManuscriptStatus.AWAITING_REFEREE)
    referee = Referee(available=True)

    manuscript.assign_referee(referee)

    assert manuscript.assigned_referees == [referee]

# tests/integration/test_referee_extraction.py
@pytest.mark.asyncio
async def test_referee_extraction_flow():
    """Test complete extraction workflow"""
    async with TestDatabase() as db:
        scraper = PlaywrightJournalScraper()
        handler = ExtractRefereesHandler(scraper, db)

        result = await handler.extract_journal_data("SICON")

        assert result.success
        assert len(result.manuscripts) > 0
```

#### 4.3 Quality Metrics
- **Code coverage** > 80%
- **Type coverage** > 95%
- **Cyclomatic complexity** < 10
- **Performance benchmarks** for all critical paths

## Migration Strategy

### Step 1: Parallel Development
- Keep existing system running
- Build new architecture alongside
- Use feature flags for gradual rollout

### Step 2: Incremental Migration
- Migrate one journal at a time
- Start with SICON/SIFIN (most mature)
- Validate each migration thoroughly

### Step 3: Cutover Plan
- Run both systems in parallel
- Compare outputs for validation
- Gradual traffic shift
- Rollback plan ready

## Success Metrics

### Technical Metrics
- ⬇️ **90% reduction** in code duplication
- ⬆️ **10x improvement** in test execution speed
- ⬇️ **75% reduction** in bug reports
- ⬆️ **95% type coverage** with mypy

### Business Metrics
- ⬇️ **50% reduction** in extraction time
- ⬆️ **99.9% uptime** for critical workflows
- ⬇️ **80% reduction** in manual interventions
- ⬆️ **100% audit trail** coverage

## Risk Mitigation

### Technical Risks
- **Data loss**: Comprehensive backups before migration
- **Breaking changes**: Feature flags and gradual rollout
- **Performance degradation**: Load testing and monitoring

### Business Risks
- **Downtime**: Parallel systems during transition
- **User disruption**: Clear communication and training
- **Feature gaps**: Maintain feature parity checklist

## Timeline

```
Week 1: Cleanup & Organization
Week 2-4: Architecture Implementation
Week 5-6: Technology Modernization
Week 7-8: Testing & Performance
Week 9-10: Migration & Validation
Week 11-12: Monitoring & Optimization
```

## Next Steps

1. **Get stakeholder approval** for refactoring plan
2. **Create detailed backlog** in project management tool
3. **Set up new development environment** with modern stack
4. **Begin Phase 1 cleanup** immediately
5. **Establish coding standards** and review process

---

*This refactoring plan will transform the editorial scripts system into a maintainable, scalable, and modern codebase ready for the AI-powered features planned in the roadmap.*
