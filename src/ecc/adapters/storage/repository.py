"""
Repository Pattern Implementation for ECC

Implements async repository pattern for clean domain/infrastructure separation.
Follows the hexagonal architecture pattern from Section 2.1 of specifications.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.ecc.core.domain.models import AnalysisType, Manuscript, ManuscriptStatus
from src.ecc.core.logging_system import ExtractorLogger
from src.ecc.infrastructure.database.models import (
    AIAnalysisModel,
    AuditEventModel,
    AuthorModel,
    FileModel,
    ManuscriptModel,
    RefereeModel,
)
from src.ecc.infrastructure.monitoring import trace_method


class BaseRepository:
    """Base repository with common operations."""

    def __init__(self, session: AsyncSession, logger: ExtractorLogger | None = None):
        self.session = session
        self.logger = logger or ExtractorLogger("repository")


class ManuscriptRepository(BaseRepository):
    """Repository for manuscript operations."""

    @trace_method("repository.get_manuscript")
    async def get_by_id(self, manuscript_id: UUID) -> Manuscript | None:
        """Get manuscript by ID with all related data."""
        query = (
            select(ManuscriptModel)
            .where(ManuscriptModel.id == manuscript_id)
            .options(
                selectinload(ManuscriptModel.authors),
                selectinload(ManuscriptModel.referees),
                selectinload(ManuscriptModel.files),
                selectinload(ManuscriptModel.ai_analyses),
            )
        )

        result = await self.session.execute(query)
        manuscript_model = result.scalar_one_or_none()

        if manuscript_model:
            return self._to_domain_model(manuscript_model)
        return None

    @trace_method("repository.find_manuscripts")
    async def find_by_journal_and_status(
        self, journal_id: str, status: ManuscriptStatus, limit: int = 100
    ) -> list[Manuscript]:
        """Find manuscripts by journal and status."""
        query = (
            select(ManuscriptModel)
            .where(
                ManuscriptModel.journal_id == journal_id, ManuscriptModel.current_status == status
            )
            .limit(limit)
        )

        result = await self.session.execute(query)
        manuscript_models = result.scalars().all()

        return [self._to_domain_model(model) for model in manuscript_models]

    @trace_method("repository.save_manuscript")
    async def save(self, manuscript: Manuscript) -> None:
        """Save manuscript to database."""
        # Check if manuscript exists by composite key (journal_id, external_id)
        existing = await self._get_by_composite(manuscript.journal_id, manuscript.external_id)

        if existing:
            # Update existing
            await self._update_manuscript_by_composite(manuscript)
        else:
            # Create new
            await self._create_manuscript(manuscript)

        await self.session.commit()

    async def save_full(self, manuscript: Manuscript) -> None:
        """Save manuscript and related entities (authors, referees, files, audit trail)."""
        # Upsert manuscript core
        await self.save(manuscript)

        # Fetch persisted manuscript to get ID
        db_manuscript = await self._get_by_composite(manuscript.journal_id, manuscript.external_id)
        if not db_manuscript:
            return

        # Replace related collections with current snapshot (simplify semantics)
        await self.session.execute(
            delete(AuthorModel).where(AuthorModel.manuscript_id == db_manuscript.id)
        )
        await self.session.execute(
            delete(RefereeModel).where(RefereeModel.manuscript_id == db_manuscript.id)
        )
        await self.session.execute(
            delete(FileModel).where(FileModel.manuscript_id == db_manuscript.id)
        )

        # Insert authors
        for a in manuscript.authors:
            self.session.add(
                AuthorModel(
                    manuscript_id=db_manuscript.id,
                    name=a.name,
                    email=a.email or None,
                    orcid=a.orcid or None,
                    institution=a.institution or None,
                    department=a.department or None,
                    country=a.country or None,
                    is_corresponding=a.is_corresponding,
                    created_at=a.created_at,
                )
            )

        # Insert referees
        for r in manuscript.referees:
            self.session.add(
                RefereeModel(
                    manuscript_id=db_manuscript.id,
                    name=r.name,
                    email=r.email or None,
                    institution=r.institution or None,
                    department=r.department or None,
                    country=r.country or None,
                    status=r.status,
                    invited_date=r.invited_date,
                    agreed_date=r.agreed_date,
                    report_due_date=r.report_due_date,
                    report_submitted_date=r.report_submitted_date,
                    expertise_score=r.expertise_score,
                    conflict_of_interest=r.conflict_of_interest,
                    historical_performance=r.historical_performance,
                    created_at=r.created_at,
                )
            )

        # Insert files
        for f in manuscript.files:
            self.session.add(
                FileModel(
                    manuscript_id=db_manuscript.id,
                    document_type=f.document_type,
                    filename=f.filename,
                    mime_type=f.mime_type,
                    size_bytes=f.size_bytes,
                    storage_path=f.storage_path,
                    checksum=f.checksum,
                    uploaded_date=f.uploaded_date,
                    version=f.version,
                )
            )

        # Persist audit trail as generic events if present
        if manuscript.metadata and manuscript.metadata.get("audit_trail"):
            raw_events = manuscript.metadata.get("audit_trail") or []
            # Deduplicate by (datetime, event text)
            seen = set()
            events = []
            for ev in raw_events:
                key = (str(ev.get("datetime", "")), str(ev.get("event", "")))
                if key in seen:
                    continue
                seen.add(key)
                events.append(ev)
            for ev in events:
                try:
                    self.session.add(
                        AuditEventModel(
                            manuscript_id=db_manuscript.id,
                            entity_type="Manuscript",
                            entity_id=db_manuscript.id,
                            action="audit_event",
                            actor="",
                            ip_address="",
                            user_agent="",
                            changes=ev,
                            request_id="",
                        )
                    )
                except Exception:
                    continue

        await self.session.commit()

    async def _get_by_composite(self, journal_id: str, external_id: str) -> ManuscriptModel | None:
        query = select(ManuscriptModel).where(
            ManuscriptModel.journal_id == journal_id, ManuscriptModel.external_id == external_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _create_manuscript(self, manuscript: Manuscript) -> None:
        """Create new manuscript record."""
        manuscript_model = ManuscriptModel(
            journal_id=manuscript.journal_id,
            external_id=manuscript.external_id,
            title=manuscript.title,
            current_status=manuscript.current_status,
            submission_date=manuscript.submission_date,
            manuscript_metadata=manuscript.metadata,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            version=1,
        )

        self.session.add(manuscript_model)
        await self.session.flush()

    async def _update_manuscript_by_composite(self, manuscript: Manuscript) -> None:
        """Update existing manuscript by composite key."""
        query = (
            update(ManuscriptModel)
            .where(
                ManuscriptModel.journal_id == manuscript.journal_id,
                ManuscriptModel.external_id == manuscript.external_id,
            )
            .values(
                title=manuscript.title,
                current_status=manuscript.current_status,
                manuscript_metadata=manuscript.metadata,
                updated_at=datetime.now(UTC),
                version=ManuscriptModel.version + 1,
            )
        )

        await self.session.execute(query)

    def _to_domain_model(self, manuscript_model: ManuscriptModel) -> Manuscript:
        """Convert database model to domain model."""
        return Manuscript(
            id=manuscript_model.id,
            journal_id=manuscript_model.journal_id,
            external_id=manuscript_model.external_id,
            title=manuscript_model.title,
            current_status=manuscript_model.current_status,
            submission_date=manuscript_model.submission_date,
            authors=[],  # Would load from related models
            referees=[],  # Would load from related models
            files=[],  # Would load from related models
            ai_analyses=[],  # Would load from related models
            audit_trail=[],  # Would load from related models
            metadata=manuscript_model.manuscript_metadata or {},
            created_at=manuscript_model.created_at,
            updated_at=manuscript_model.updated_at,
            version=manuscript_model.version,
        )


class AuthorRepository(BaseRepository):
    """Repository for author operations."""

    @trace_method("repository.get_author")
    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Get author by email address."""
        query = select(AuthorModel).where(AuthorModel.email == email)
        result = await self.session.execute(query)
        author_model = result.scalar_one_or_none()

        if author_model:
            return {
                "id": author_model.id,
                "email": author_model.email,
                "name": author_model.name,
                "institution": author_model.institution,
                "is_corresponding": author_model.is_corresponding,
            }
        return None

    @trace_method("repository.create_author")
    async def create_author(
        self,
        manuscript_id: UUID,
        name: str,
        email: str | None = None,
        institution: str | None = None,
    ) -> UUID:
        """Create new author."""
        author_model = AuthorModel(
            manuscript_id=manuscript_id,
            name=name,
            email=email,
            institution=institution,
            created_at=datetime.now(UTC),
        )

        self.session.add(author_model)
        await self.session.commit()

        return author_model.id


class AIAnalysisRepository(BaseRepository):
    """Repository for AI analysis records."""

    @trace_method("repository.save_ai_analysis")
    async def save_analysis(
        self,
        manuscript_id: UUID,
        analysis_type: AnalysisType,
        model_version: str,
        confidence_score: float,
        reasoning: str,
        recommendation: str,
        evidence: list[str],
        human_review_required: bool,
        cost_usd: float,
    ) -> UUID:
        """Save AI analysis result."""
        analysis_model = AIAnalysisModel(
            manuscript_id=manuscript_id,
            analysis_type=analysis_type,
            model_version=model_version,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommendation=recommendation,
            evidence=evidence,
            human_review_required=human_review_required,
            cost_usd=cost_usd,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),  # GDPR compliance
        )

        self.session.add(analysis_model)
        await self.session.commit()

        return analysis_model.id

    @trace_method("repository.get_ai_analyses")
    async def get_by_manuscript(
        self, manuscript_id: UUID, analysis_type: AnalysisType | None = None
    ) -> list[dict[str, Any]]:
        """Get AI analyses for manuscript."""
        query = select(AIAnalysisModel).where(AIAnalysisModel.manuscript_id == manuscript_id)

        if analysis_type:
            query = query.where(AIAnalysisModel.analysis_type == analysis_type)

        result = await self.session.execute(query)
        analyses = result.scalars().all()

        return [
            {
                "id": analysis.id,
                "analysis_type": analysis.analysis_type,
                "confidence_score": analysis.confidence_score,
                "reasoning": analysis.reasoning,
                "recommendation": analysis.recommendation,
                "human_review_required": analysis.human_review_required,
                "created_at": analysis.created_at,
            }
            for analysis in analyses
        ]


class AuditRepository(BaseRepository):
    """Repository for audit trail operations."""

    @trace_method("repository.create_audit_event")
    async def create_audit_event(
        self,
        entity_type: str,
        entity_id: UUID,
        action: str,
        actor: str,
        ip_address: str,
        user_agent: str,
        changes: dict[str, Any],
        request_id: str,
    ) -> None:
        """Create audit trail event."""
        audit_event = AuditEventModel(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
            timestamp=datetime.now(UTC),
            request_id=request_id,
        )

        self.session.add(audit_event)
        await self.session.commit()

    @trace_method("repository.get_audit_trail")
    async def get_audit_trail(
        self, entity_type: str, entity_id: UUID, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get audit trail for entity."""
        query = (
            select(AuditEventModel)
            .where(
                AuditEventModel.entity_type == entity_type, AuditEventModel.entity_id == entity_id
            )
            .order_by(AuditEventModel.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": event.id,
                "action": event.action,
                "actor": event.actor,
                "changes": event.changes,
                "timestamp": event.timestamp,
                "request_id": event.request_id,
            }
            for event in events
        ]
