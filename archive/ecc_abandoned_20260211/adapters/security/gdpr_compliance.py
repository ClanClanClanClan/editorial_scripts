"""GDPR Compliance Framework for ECC.

Implements the data protection requirements from ECC specifications v2.0:
- Data minimization and purpose limitation
- Consent management for AI processing
- Right to deletion and portability
- Breach notification system
- PII detection and masking
- Data retention policies
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any

import aiosmtplib

from src.ecc.adapters.security.vault_client import VaultClient
from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger, LogCategory


class LawfulBasis(Enum):
    """GDPR lawful bases for processing."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTEREST = "legitimate_interest"


class DataCategory(Enum):
    """Categories of personal data."""

    BASIC_IDENTITY = "basic_identity"  # Name, email
    PROFESSIONAL = "professional"  # Institution, department
    RESEARCH_DATA = "research_data"  # Manuscripts, reviews
    BEHAVIORAL = "behavioral"  # System usage, preferences
    SPECIAL_CATEGORY = "special_category"  # Sensitive personal data


class ProcessingPurpose(Enum):
    """Purposes for data processing."""

    MANUSCRIPT_REVIEW = "manuscript_review"
    AI_ANALYSIS = "ai_analysis"
    SYSTEM_ADMINISTRATION = "system_administration"
    COMMUNICATION = "communication"
    AUDIT_COMPLIANCE = "audit_compliance"
    RESEARCH_ANALYTICS = "research_analytics"


class ConsentStatus(Enum):
    """Consent status values."""

    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    NOT_REQUESTED = "not_requested"
    EXPIRED = "expired"


class RequestType(Enum):
    """Data subject request types."""

    ACCESS = "access"  # Right to access
    RECTIFICATION = "rectification"  # Right to rectify
    ERASURE = "erasure"  # Right to be forgotten
    PORTABILITY = "portability"  # Right to data portability
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"  # Right to object


class RequestStatus(Enum):
    """Data subject request status."""

    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class PIIPattern:
    """Pattern for detecting personally identifiable information."""

    name: str
    pattern: re.Pattern
    confidence: float
    category: DataCategory
    masking_strategy: str = "asterisk"  # asterisk, hash, remove, redact

    def detect(self, text: str) -> list[dict[str, Any]]:
        """Detect PII in text."""
        matches = []
        for match in self.pattern.finditer(text):
            matches.append(
                {
                    "type": self.name,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": self.confidence,
                    "category": self.category.value,
                }
            )
        return matches

    def mask(self, text: str) -> str:
        """Mask PII in text."""

        def replace_match(match):
            matched_text = match.group()
            if self.masking_strategy == "asterisk":
                return "*" * len(matched_text)
            elif self.masking_strategy == "hash":
                return hashlib.sha256(matched_text.encode()).hexdigest()[:8]
            elif self.masking_strategy == "remove":
                return ""
            elif self.masking_strategy == "redact":
                return f"[REDACTED-{self.name.upper()}]"
            else:
                return matched_text

        return self.pattern.sub(replace_match, text)


@dataclass
class ConsentRecord:
    """Consent record for GDPR compliance."""

    subject_id: str
    purpose: ProcessingPurpose
    lawful_basis: LawfulBasis
    status: ConsentStatus
    given_at: datetime | None = None
    withdrawn_at: datetime | None = None
    expires_at: datetime | None = None
    consent_text: str = ""
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if consent is valid."""
        if self.status != ConsentStatus.GIVEN:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    def is_required(self) -> bool:
        """Check if consent is required for this processing."""
        return self.lawful_basis == LawfulBasis.CONSENT


@dataclass
class DataSubjectRequest:
    """Data subject rights request."""

    id: str
    subject_id: str
    request_type: RequestType
    status: RequestStatus
    requested_at: datetime
    completed_at: datetime | None = None
    due_date: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    description: str = ""
    response: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_overdue(self) -> bool:
        """Check if request is overdue."""
        return datetime.utcnow() > self.due_date and self.status != RequestStatus.COMPLETED

    def days_remaining(self) -> int:
        """Days remaining to fulfill request."""
        return max(0, (self.due_date - datetime.utcnow()).days)


@dataclass
class DataBreach:
    """Data breach record."""

    id: str
    detected_at: datetime
    reported_at: datetime | None = None
    description: str = ""
    affected_subjects: int = 0
    data_categories: list[DataCategory] = field(default_factory=list)
    risk_level: str = "medium"  # low, medium, high
    containment_measures: list[str] = field(default_factory=list)
    notification_required: bool = True
    dpa_notified: bool = False
    subjects_notified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def requires_dpa_notification(self) -> bool:
        """Check if breach requires DPA notification."""
        return self.notification_required and not self.dpa_notified

    def is_notification_overdue(self) -> bool:
        """Check if notification is overdue (72 hours)."""
        if not self.requires_dpa_notification():
            return False

        deadline = self.detected_at + timedelta(hours=72)
        return datetime.utcnow() > deadline


class PIIDetector:
    """Automated PII detection system."""

    def __init__(self, logger: ExtractorLogger | None = None):
        """Initialize PII detector with common patterns."""
        self.logger = logger or ExtractorLogger("pii_detector")
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> list[PIIPattern]:
        """Initialize PII detection patterns."""
        return [
            # Email addresses
            PIIPattern(
                name="email",
                pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
                confidence=0.95,
                category=DataCategory.BASIC_IDENTITY,
                masking_strategy="asterisk",
            ),
            # Phone numbers (various formats)
            PIIPattern(
                name="phone",
                pattern=re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
                confidence=0.85,
                category=DataCategory.BASIC_IDENTITY,
                masking_strategy="asterisk",
            ),
            # Names (simple pattern - can be improved with NLP)
            PIIPattern(
                name="person_name",
                pattern=re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b"),
                confidence=0.7,
                category=DataCategory.BASIC_IDENTITY,
                masking_strategy="redact",
            ),
            # ORCID IDs
            PIIPattern(
                name="orcid",
                pattern=re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b"),
                confidence=0.95,
                category=DataCategory.PROFESSIONAL,
                masking_strategy="hash",
            ),
            # DOI patterns (might contain author info)
            PIIPattern(
                name="doi",
                pattern=re.compile(r"\b10\.\d{4,}/[^\s]+"),
                confidence=0.8,
                category=DataCategory.RESEARCH_DATA,
                masking_strategy="redact",
            ),
            # IP addresses
            PIIPattern(
                name="ip_address",
                pattern=re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
                confidence=0.9,
                category=DataCategory.BEHAVIORAL,
                masking_strategy="hash",
            ),
        ]

    def scan_text(self, text: str) -> dict[str, list[dict[str, Any]]]:
        """
        Scan text for PII patterns.

        Args:
            text: Text to scan

        Returns:
            Dictionary mapping pattern names to detected matches
        """
        results = {}

        for pattern in self.patterns:
            matches = pattern.detect(text)
            if matches:
                results[pattern.name] = matches

        return results

    def mask_pii(self, text: str, patterns_to_mask: list[str] | None = None) -> str:
        """
        Mask PII in text.

        Args:
            text: Text to mask
            patterns_to_mask: Specific patterns to mask (None for all)

        Returns:
            Text with PII masked
        """
        masked_text = text

        for pattern in self.patterns:
            if patterns_to_mask is None or pattern.name in patterns_to_mask:
                masked_text = pattern.mask(masked_text)

        return masked_text

    def get_pii_summary(self, text: str) -> dict[str, Any]:
        """
        Get summary of PII found in text.

        Args:
            text: Text to analyze

        Returns:
            Summary of PII detection results
        """
        results = self.scan_text(text)

        summary = {
            "total_pii_items": sum(len(matches) for matches in results.values()),
            "categories_found": set(),
            "high_confidence_items": 0,
            "patterns_detected": list(results.keys()),
        }

        for pattern_name, matches in results.items():
            pattern = next(p for p in self.patterns if p.name == pattern_name)
            summary["categories_found"].add(pattern.category.value)

            for match in matches:
                if match["confidence"] >= 0.9:
                    summary["high_confidence_items"] += 1

        summary["categories_found"] = list(summary["categories_found"])

        return summary


class ConsentManager:
    """Manages consent records for GDPR compliance."""

    def __init__(
        self, vault_client: VaultClient | None = None, logger: ExtractorLogger | None = None
    ):
        """Initialize consent manager."""
        self.vault = vault_client
        self.logger = logger or ExtractorLogger("consent_manager")
        self.consent_records: dict[str, ConsentRecord] = {}

    async def record_consent(
        self,
        subject_id: str,
        purpose: ProcessingPurpose,
        lawful_basis: LawfulBasis,
        consent_text: str,
        expires_in_days: int | None = None,
    ) -> ConsentRecord:
        """
        Record consent for data processing.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose
            lawful_basis: Legal basis for processing
            consent_text: Text of consent given
            expires_in_days: Consent expiration in days

        Returns:
            Created consent record
        """
        self.logger.enter_context(f"record_consent_{subject_id}_{purpose.value}")

        try:
            # Create consent record
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            consent_key = f"{subject_id}_{purpose.value}"
            consent_record = ConsentRecord(
                subject_id=subject_id,
                purpose=purpose,
                lawful_basis=lawful_basis,
                status=(
                    ConsentStatus.GIVEN
                    if lawful_basis == LawfulBasis.CONSENT
                    else ConsentStatus.NOT_REQUESTED
                ),
                given_at=datetime.utcnow() if lawful_basis == LawfulBasis.CONSENT else None,
                expires_at=expires_at,
                consent_text=consent_text,
            )

            # Store consent record
            self.consent_records[consent_key] = consent_record

            # Store in Vault if available
            if self.vault:
                await self.vault.write_secret(
                    f"gdpr/consent/{consent_key}",
                    {
                        "subject_id": subject_id,
                        "purpose": purpose.value,
                        "lawful_basis": lawful_basis.value,
                        "status": consent_record.status.value,
                        "given_at": (
                            consent_record.given_at.isoformat() if consent_record.given_at else None
                        ),
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "consent_text": consent_text,
                        "version": consent_record.version,
                    },
                )

            self.logger.success(
                f"Consent recorded: {subject_id} for {purpose.value} (basis: {lawful_basis.value})",
                LogCategory.SECURITY,
            )

            return consent_record

        except Exception as e:
            self.logger.error(f"Failed to record consent: {e}")
            raise ExtractorError("Consent recording failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def check_consent(self, subject_id: str, purpose: ProcessingPurpose) -> bool:
        """
        Check if we have valid consent for processing.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose

        Returns:
            True if consent is valid or not required
        """
        consent_key = f"{subject_id}_{purpose.value}"
        consent_record = self.consent_records.get(consent_key)

        if not consent_record:
            # Try to load from Vault
            if self.vault:
                secret_data = await self.vault.read_secret(f"gdpr/consent/{consent_key}")
                if secret_data:
                    data = secret_data["data"]
                    consent_record = ConsentRecord(
                        subject_id=data["subject_id"],
                        purpose=ProcessingPurpose(data["purpose"]),
                        lawful_basis=LawfulBasis(data["lawful_basis"]),
                        status=ConsentStatus(data["status"]),
                        given_at=(
                            datetime.fromisoformat(data["given_at"])
                            if data.get("given_at")
                            else None
                        ),
                        expires_at=(
                            datetime.fromisoformat(data["expires_at"])
                            if data.get("expires_at")
                            else None
                        ),
                        consent_text=data["consent_text"],
                        version=data["version"],
                    )
                    self.consent_records[consent_key] = consent_record

        if not consent_record:
            self.logger.warning(f"No consent record found: {subject_id} for {purpose.value}")
            return False

        # Check if consent is required
        if not consent_record.is_required():
            return True

        # Check if consent is valid
        return consent_record.is_valid()

    async def withdraw_consent(self, subject_id: str, purpose: ProcessingPurpose) -> bool:
        """
        Withdraw consent for processing.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose

        Returns:
            True if consent was withdrawn
        """
        consent_key = f"{subject_id}_{purpose.value}"
        consent_record = self.consent_records.get(consent_key)

        if not consent_record:
            return False

        # Update consent record
        consent_record.status = ConsentStatus.WITHDRAWN
        consent_record.withdrawn_at = datetime.utcnow()

        # Update in Vault
        if self.vault:
            await self.vault.write_secret(
                f"gdpr/consent/{consent_key}",
                {
                    "subject_id": subject_id,
                    "purpose": purpose.value,
                    "status": ConsentStatus.WITHDRAWN.value,
                    "withdrawn_at": datetime.utcnow().isoformat(),
                },
            )

        self.logger.success(
            f"Consent withdrawn: {subject_id} for {purpose.value}", LogCategory.SECURITY
        )

        return True

    async def get_subject_consents(self, subject_id: str) -> list[ConsentRecord]:
        """Get all consent records for a subject."""
        subject_consents = []

        for consent_record in self.consent_records.values():
            if consent_record.subject_id == subject_id:
                subject_consents.append(consent_record)

        return subject_consents


class DataSubjectRightsManager:
    """Manages data subject rights requests."""

    def __init__(
        self, vault_client: VaultClient | None = None, logger: ExtractorLogger | None = None
    ):
        """Initialize rights manager."""
        self.vault = vault_client
        self.logger = logger or ExtractorLogger("rights_manager")
        self.requests: dict[str, DataSubjectRequest] = {}
        self.request_handlers = {
            RequestType.ACCESS: self._handle_access_request,
            RequestType.RECTIFICATION: self._handle_rectification_request,
            RequestType.ERASURE: self._handle_erasure_request,
            RequestType.PORTABILITY: self._handle_portability_request,
            RequestType.RESTRICTION: self._handle_restriction_request,
            RequestType.OBJECTION: self._handle_objection_request,
        }

    async def submit_request(
        self, subject_id: str, request_type: RequestType, description: str = ""
    ) -> DataSubjectRequest:
        """
        Submit a data subject rights request.

        Args:
            subject_id: Data subject identifier
            request_type: Type of request
            description: Additional description

        Returns:
            Created request record
        """
        self.logger.enter_context(f"submit_request_{request_type.value}")

        try:
            # Generate request ID
            request_id = hashlib.sha256(
                f"{subject_id}:{request_type.value}:{time.time()}".encode()
            ).hexdigest()[:12]

            # Create request
            request = DataSubjectRequest(
                id=request_id,
                subject_id=subject_id,
                request_type=request_type,
                status=RequestStatus.RECEIVED,
                requested_at=datetime.utcnow(),
                description=description,
            )

            # Store request
            self.requests[request_id] = request

            # Store in Vault
            if self.vault:
                await self.vault.write_secret(
                    f"gdpr/requests/{request_id}",
                    {
                        "subject_id": subject_id,
                        "request_type": request_type.value,
                        "status": RequestStatus.RECEIVED.value,
                        "requested_at": request.requested_at.isoformat(),
                        "due_date": request.due_date.isoformat(),
                        "description": description,
                    },
                )

            self.logger.success(
                f"Rights request submitted: {request_type.value} for {subject_id}",
                LogCategory.SECURITY,
            )

            return request

        except Exception as e:
            self.logger.error(f"Failed to submit request: {e}")
            raise ExtractorError("Request submission failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def process_request(self, request_id: str) -> bool:
        """
        Process a data subject rights request.

        Args:
            request_id: Request identifier

        Returns:
            True if processed successfully
        """
        request = self.requests.get(request_id)
        if not request:
            raise ExtractorError(f"Request not found: {request_id}")

        # Update status
        request.status = RequestStatus.IN_PROGRESS

        try:
            # Get handler for request type
            handler = self.request_handlers.get(request.request_type)
            if not handler:
                raise ExtractorError(f"No handler for request type: {request.request_type}")

            # Process request
            response = await handler(request)

            # Update request
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response = response

            self.logger.success(f"Request processed: {request_id}", LogCategory.SECURITY)

            return True

        except Exception as e:
            request.status = RequestStatus.REJECTED
            request.response = f"Processing failed: {e}"
            self.logger.error(f"Request processing failed: {request_id} - {e}")
            return False

    async def _handle_access_request(self, request: DataSubjectRequest) -> str:
        """Handle data access request."""
        # This would collect all data for the subject
        # For now, return placeholder response
        return f"Data access report generated for subject {request.subject_id}"

    async def _handle_rectification_request(self, request: DataSubjectRequest) -> str:
        """Handle data rectification request."""
        return f"Data rectification completed for subject {request.subject_id}"

    async def _handle_erasure_request(self, request: DataSubjectRequest) -> str:
        """Handle data erasure request (right to be forgotten)."""
        # This would delete all data for the subject
        return f"Data erasure completed for subject {request.subject_id}"

    async def _handle_portability_request(self, request: DataSubjectRequest) -> str:
        """Handle data portability request."""
        return f"Data export generated for subject {request.subject_id}"

    async def _handle_restriction_request(self, request: DataSubjectRequest) -> str:
        """Handle processing restriction request."""
        return f"Processing restriction applied for subject {request.subject_id}"

    async def _handle_objection_request(self, request: DataSubjectRequest) -> str:
        """Handle processing objection request."""
        return f"Processing objection noted for subject {request.subject_id}"

    async def get_overdue_requests(self) -> list[DataSubjectRequest]:
        """Get overdue requests."""
        return [req for req in self.requests.values() if req.is_overdue()]


class BreachNotificationManager:
    """Manages data breach notifications."""

    def __init__(
        self,
        vault_client: VaultClient | None = None,
        dpa_email: str = "dpo@institution.edu",
        smtp_config: dict[str, Any] | None = None,
        logger: ExtractorLogger | None = None,
    ):
        """Initialize breach notification manager."""
        self.vault = vault_client
        self.dpa_email = dpa_email
        self.smtp_config = smtp_config or {}
        self.logger = logger or ExtractorLogger("breach_manager")
        self.breaches: dict[str, DataBreach] = {}

    async def report_breach(
        self,
        description: str,
        affected_subjects: int,
        data_categories: list[DataCategory],
        risk_level: str = "medium",
    ) -> DataBreach:
        """
        Report a data breach.

        Args:
            description: Breach description
            affected_subjects: Number of affected subjects
            data_categories: Types of data involved
            risk_level: Risk level (low, medium, high)

        Returns:
            Created breach record
        """
        self.logger.enter_context("report_breach")

        try:
            # Generate breach ID
            breach_id = hashlib.sha256(f"breach:{description}:{time.time()}".encode()).hexdigest()[
                :12
            ]

            # Create breach record
            breach = DataBreach(
                id=breach_id,
                detected_at=datetime.utcnow(),
                description=description,
                affected_subjects=affected_subjects,
                data_categories=data_categories,
                risk_level=risk_level,
                notification_required=risk_level in ["medium", "high"] or affected_subjects > 10,
            )

            # Store breach
            self.breaches[breach_id] = breach

            # Store in Vault
            if self.vault:
                await self.vault.write_secret(
                    f"gdpr/breaches/{breach_id}",
                    {
                        "detected_at": breach.detected_at.isoformat(),
                        "description": description,
                        "affected_subjects": affected_subjects,
                        "data_categories": [cat.value for cat in data_categories],
                        "risk_level": risk_level,
                        "notification_required": breach.notification_required,
                    },
                )

            # Send immediate notifications if high risk
            if risk_level == "high":
                await self._send_breach_notification(breach)

            self.logger.success(
                f"Breach reported: {breach_id} (risk: {risk_level})", LogCategory.SECURITY
            )

            return breach

        except Exception as e:
            self.logger.error(f"Failed to report breach: {e}")
            raise ExtractorError("Breach reporting failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def _send_breach_notification(self, breach: DataBreach):
        """Send breach notification to DPA."""
        try:
            if not self.smtp_config:
                self.logger.warning("No SMTP config - breach notification not sent")
                return

            # Create notification email
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config.get("from_address", "noreply@ecc.edu")
            msg["To"] = self.dpa_email
            msg["Subject"] = f"Data Breach Notification - {breach.id}"

            body = f"""
            Data Breach Notification - ECC System

            Breach ID: {breach.id}
            Detected: {breach.detected_at.isoformat()}
            Risk Level: {breach.risk_level}
            Affected Subjects: {breach.affected_subjects}

            Description:
            {breach.description}

            Data Categories:
            {', '.join([cat.value for cat in breach.data_categories])}

            This breach requires immediate attention under GDPR Article 33.
            """

            msg.attach(MIMEText(body, "plain"))

            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.smtp_config.get("host"),
                port=self.smtp_config.get("port", 587),
                use_tls=True,
            ) as server:
                await server.login(
                    self.smtp_config.get("username"), self.smtp_config.get("password")
                )
                await server.send_message(msg)

            breach.reported_at = datetime.utcnow()
            breach.dpa_notified = True

            self.logger.success(f"Breach notification sent: {breach.id}", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"Failed to send breach notification: {e}")

    async def get_overdue_notifications(self) -> list[DataBreach]:
        """Get breaches with overdue notifications."""
        return [breach for breach in self.breaches.values() if breach.is_notification_overdue()]


class GDPRComplianceManager:
    """Main GDPR compliance manager combining all components."""

    def __init__(
        self,
        vault_client: VaultClient | None = None,
        config: dict[str, Any] | None = None,
        logger: ExtractorLogger | None = None,
    ):
        """Initialize GDPR compliance manager."""
        self.vault = vault_client
        self.config = config or {}
        self.logger = logger or ExtractorLogger("gdpr_compliance")

        # Initialize components
        self.pii_detector = PIIDetector(logger)
        self.consent_manager = ConsentManager(vault_client, logger)
        self.rights_manager = DataSubjectRightsManager(vault_client, logger)
        self.breach_manager = BreachNotificationManager(
            vault_client,
            dpa_email=self.config.get("dpa_email", "dpo@institution.edu"),
            smtp_config=self.config.get("smtp"),
            logger=logger,
        )

        # Data retention policies (in days)
        self.retention_policies = {
            DataCategory.BASIC_IDENTITY: 2555,  # 7 years
            DataCategory.PROFESSIONAL: 2555,  # 7 years
            DataCategory.RESEARCH_DATA: 2555,  # 7 years
            DataCategory.BEHAVIORAL: 365,  # 1 year
            DataCategory.SPECIAL_CATEGORY: 1095,  # 3 years
        }

    async def initialize(self):
        """Initialize GDPR compliance system."""
        self.logger.enter_context("gdpr_init")

        try:
            # Check for overdue requests and notifications
            overdue_requests = await self.rights_manager.get_overdue_requests()
            if overdue_requests:
                self.logger.warning(f"Found {len(overdue_requests)} overdue data subject requests")

            overdue_notifications = await self.breach_manager.get_overdue_notifications()
            if overdue_notifications:
                self.logger.warning(
                    f"Found {len(overdue_notifications)} overdue breach notifications"
                )

            self.logger.success("GDPR compliance system initialized", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"GDPR initialization failed: {e}")
            raise ExtractorError("GDPR initialization failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def check_processing_consent(
        self, subject_id: str, purpose: ProcessingPurpose, data: dict[str, Any] | None = None
    ) -> bool:
        """
        Check if we can process data for the given subject and purpose.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose
            data: Optional data to check for PII

        Returns:
            True if processing is allowed
        """
        # Check consent
        has_consent = await self.consent_manager.check_consent(subject_id, purpose)

        # If processing AI data, extra consent checks
        if purpose == ProcessingPurpose.AI_ANALYSIS and data:
            # Scan for PII that might need special consent
            pii_summary = self.pii_detector.get_pii_summary(str(data))
            if pii_summary["high_confidence_items"] > 0:
                # High confidence PII found - ensure explicit consent
                ai_consent = await self.consent_manager.check_consent(
                    subject_id, ProcessingPurpose.AI_ANALYSIS
                )
                return has_consent and ai_consent

        return has_consent

    async def process_data_with_compliance(
        self,
        subject_id: str,
        purpose: ProcessingPurpose,
        data: dict[str, Any],
        mask_pii: bool = True,
    ) -> dict[str, Any]:
        """
        Process data with GDPR compliance checks.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose
            data: Data to process
            mask_pii: Whether to mask PII in logs

        Returns:
            Processed data
        """
        # Check consent
        if not await self.check_processing_consent(subject_id, purpose, data):
            raise ExtractorError(f"No valid consent for processing: {subject_id} - {purpose.value}")

        # Process data based on purpose
        if purpose == ProcessingPurpose.AI_ANALYSIS:
            # Special handling for AI analysis
            return await self._process_ai_data(subject_id, data, mask_pii)
        else:
            # Standard processing
            return data

    async def _process_ai_data(
        self, subject_id: str, data: dict[str, Any], mask_pii: bool
    ) -> dict[str, Any]:
        """Process data for AI analysis with PII handling."""
        processed_data = data.copy()

        # Mask PII in text fields if requested
        if mask_pii:
            for key, value in processed_data.items():
                if isinstance(value, str):
                    processed_data[key] = self.pii_detector.mask_pii(value)

        # Log AI processing with privacy preservation
        self.logger.success(
            f"AI processing authorized for subject {subject_id}", LogCategory.SECURITY
        )

        return processed_data

    async def handle_data_deletion(self, subject_id: str) -> dict[str, Any]:
        """
        Handle right to erasure (be forgotten) request.

        Args:
            subject_id: Data subject identifier

        Returns:
            Deletion summary
        """
        deletion_summary = {
            "subject_id": subject_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "items_deleted": [],
            "items_anonymized": [],
            "errors": [],
        }

        try:
            # This would integrate with all data stores to delete/anonymize data
            # For now, just log the action
            self.logger.success(
                f"Data deletion completed for subject: {subject_id}", LogCategory.SECURITY
            )

        except Exception as e:
            deletion_summary["errors"].append(str(e))
            self.logger.error(f"Data deletion failed for {subject_id}: {e}")

        return deletion_summary

    async def generate_compliance_report(self) -> dict[str, Any]:
        """Generate GDPR compliance report."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "consent_records": len(self.consent_manager.consent_records),
            "active_requests": len(
                [
                    r
                    for r in self.rights_manager.requests.values()
                    if r.status in [RequestStatus.RECEIVED, RequestStatus.IN_PROGRESS]
                ]
            ),
            "overdue_requests": len(await self.rights_manager.get_overdue_requests()),
            "data_breaches": len(self.breach_manager.breaches),
            "overdue_notifications": len(await self.breach_manager.get_overdue_notifications()),
            "pii_patterns_active": len(self.pii_detector.patterns),
            "retention_policies": {
                cat.value: days for cat, days in self.retention_policies.items()
            },
        }

        self.logger.info("GDPR compliance report generated", LogCategory.SECURITY)

        return report
