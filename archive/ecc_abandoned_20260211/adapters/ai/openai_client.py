"""
OpenAI Client with AI Governance

Implements Section 5 AI governance framework from ECC specifications:
- Comprehensive audit trails
- Confidence scoring and human review requirements
- Bias detection and monitoring
- Usage tracking and budget controls
"""

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from openai import AsyncOpenAI

from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger
from src.ecc.infrastructure.monitoring import get_observability, trace_method


class ModelType(Enum):
    """OpenAI model types for ECC operations."""

    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


class AnalysisType(Enum):
    """Types of AI analysis supported by ECC."""

    DESK_REJECTION = "desk_rejection"
    REFEREE_RECOMMENDATION = "referee_recommendation"
    REPORT_SYNTHESIS = "report_synthesis"
    CONFLICT_DETECTION = "conflict_detection"


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI integration."""

    api_key: str
    organization: str | None = None
    default_model: ModelType = ModelType.GPT_4_TURBO
    max_tokens: int = 4000
    temperature: float = 0.1  # Low temperature for consistency
    timeout: int = 60
    max_retries: int = 3

    # Budget controls
    daily_budget_usd: float = 100.0
    monthly_budget_usd: float = 2000.0
    cost_per_1k_tokens: dict[str, float] = None

    # Governance settings
    human_review_confidence_threshold: float = 0.8
    enable_bias_detection: bool = True
    enable_audit_logging: bool = True

    def __post_init__(self):
        """Initialize default cost mapping."""
        if self.cost_per_1k_tokens is None:
            self.cost_per_1k_tokens = {
                "gpt-4-turbo-preview": 0.03,
                "gpt-4": 0.06,
                "gpt-3.5-turbo": 0.002,
            }


@dataclass
class AIRequest:
    """AI analysis request with governance metadata."""

    id: str
    analysis_type: AnalysisType
    manuscript_id: str
    journal_id: str
    content: str
    model: ModelType
    temperature: float
    max_tokens: int
    timestamp: datetime
    user_id: str
    session_id: str


@dataclass
class AIResponse:
    """AI analysis response with governance data."""

    request_id: str
    response_id: str
    model_version: str
    content: str
    confidence_score: float
    reasoning: str
    evidence: list[str]
    usage_tokens: int
    cost_usd: float
    processing_time: float
    timestamp: datetime
    human_review_required: bool
    bias_flags: list[str]


class OpenAIClient:
    """
    OpenAI client with comprehensive AI governance.

    Implements Section 5 AI governance framework:
    - Pre-analysis validation
    - Post-analysis audit trails
    - Budget monitoring and controls
    - Bias detection and alerts
    - Human review workflow
    """

    def __init__(self, config: OpenAIConfig, logger: ExtractorLogger | None = None):
        """Initialize OpenAI client with governance."""
        self.config = config
        self.logger = logger or ExtractorLogger("openai_client")
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            organization=config.organization,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

        # Usage tracking for budget controls
        self.daily_usage = 0.0
        self.monthly_usage = 0.0
        self.last_reset_date = datetime.utcnow().date()

        # Request history for audit trails
        self.request_history: list[AIRequest] = []
        self.response_history: list[AIResponse] = []

        # Observability
        self.observability = get_observability()

    @trace_method("ai.generate_analysis")
    async def generate_analysis(self, request: AIRequest) -> AIResponse:
        """
        Generate AI analysis with full governance pipeline.

        Implements the complete AI governance flow from Section 5.1:
        1. Pre-analysis validation
        2. Content generation
        3. Post-analysis audit
        4. Human review determination
        """
        start_time = time.time()

        try:
            # Step 1: Pre-analysis governance checks
            validation_result = await self._pre_analysis_check(request)
            if not validation_result.approved:
                raise ExtractorError(f"AI governance check failed: {validation_result.reason}")

            # Step 2: Budget validation
            estimated_cost = self._estimate_cost(request)
            if not self._check_budget(estimated_cost):
                raise ExtractorError("Budget limit exceeded for AI analysis")

            # Step 3: Generate AI response
            self.logger.log_info(
                f"Generating {request.analysis_type.value} analysis for {request.manuscript_id}"
            )

            completion = await self._call_openai(request)

            # Step 4: Parse and validate response
            response = self._parse_ai_response(request, completion, start_time)

            # Step 5: Post-analysis governance
            await self._post_analysis_audit(request, response)

            # Step 6: Update usage tracking
            self._update_usage(response.cost_usd)

            # Step 7: Record observability metrics
            if self.observability:
                self.observability.record_ai_analysis(
                    journal_id=request.journal_id,
                    analysis_type=request.analysis_type.value,
                    human_agreement=False,  # Will be updated after human review
                    confidence_score=response.confidence_score,
                )

            self.logger.log_success(
                f"AI analysis completed with confidence {response.confidence_score:.2f}"
            )
            return response

        except Exception as e:
            self.logger.log_error(f"AI analysis failed: {e}")
            raise

    async def _pre_analysis_check(self, request: AIRequest) -> "GovernanceResult":
        """Validate AI request before processing (Section 5.1)."""
        checks = []

        # Data quality check
        if len(request.content.strip()) < 100:
            checks.append("Content too short for reliable analysis")

        # Content safety check
        if self._contains_sensitive_content(request.content):
            checks.append("Content contains sensitive information")

        # Rate limiting check
        if self._is_rate_limited(request.user_id):
            checks.append("User rate limit exceeded")

        if checks:
            return GovernanceResult(False, "; ".join(checks))
        else:
            return GovernanceResult(True, "All checks passed")

    def _contains_sensitive_content(self, content: str) -> bool:
        """Check for sensitive content patterns."""
        # Simple PII detection - in production would use more sophisticated methods
        sensitive_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
        ]

        import re

        for pattern in sensitive_patterns:
            if re.search(pattern, content):
                return True
        return False

    def _is_rate_limited(self, user_id: str) -> bool:
        """Check user-specific rate limits."""
        # Simple rate limiting - in production would use Redis
        recent_requests = [
            r
            for r in self.request_history
            if r.user_id == user_id and r.timestamp > datetime.now(UTC) - timedelta(hours=1)
        ]
        return len(recent_requests) > 10  # Max 10 requests per hour per user

    def _estimate_cost(self, request: AIRequest) -> float:
        """Estimate cost for budget validation."""
        model_key = request.model.value
        cost_per_1k = self.config.cost_per_1k_tokens.get(model_key, 0.03)

        # Rough estimation: input + output tokens
        estimated_tokens = len(request.content) // 3 + request.max_tokens
        return (estimated_tokens / 1000) * cost_per_1k

    def _check_budget(self, cost: float) -> bool:
        """Check if request fits within budget limits."""
        # Reset usage if new day/month
        self._reset_usage_if_needed()

        return (
            self.daily_usage + cost <= self.config.daily_budget_usd
            and self.monthly_usage + cost <= self.config.monthly_budget_usd
        )

    def _reset_usage_if_needed(self):
        """Reset usage counters for new time periods."""
        current_date = datetime.now(UTC).date()

        if current_date != self.last_reset_date:
            # New day
            self.daily_usage = 0.0

            # New month
            if current_date.month != self.last_reset_date.month:
                self.monthly_usage = 0.0

            self.last_reset_date = current_date

    async def _call_openai(self, request: AIRequest) -> Any:
        """Make actual OpenAI API call."""
        prompt = self._build_prompt(request)

        completion = await self.client.chat.completions.create(
            model=request.model.value,
            messages=[
                {"role": "system", "content": self._get_system_prompt(request.analysis_type)},
                {"role": "user", "content": prompt},
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_format={"type": "json_object"},  # Structured output
        )

        return completion

    def _build_prompt(self, request: AIRequest) -> str:
        """Build analysis prompt based on request type."""
        if request.analysis_type == AnalysisType.DESK_REJECTION:
            return f"""
            Analyze the following manuscript for potential desk rejection.
            Provide a confidence score (0.0-1.0), reasoning, and evidence.

            Manuscript content:
            {request.content}

            Respond in JSON format with fields:
            - confidence: float (0.0-1.0)
            - recommendation: string (accept/reject)
            - reasoning: string
            - evidence: array of strings
            """

        elif request.analysis_type == AnalysisType.REFEREE_RECOMMENDATION:
            return f"""
            Recommend suitable referees for this manuscript.
            Consider expertise matching and conflict of interest.

            Manuscript content:
            {request.content}

            Respond in JSON format with fields:
            - confidence: float
            - recommendations: array of referee suggestions
            - reasoning: string
            - evidence: array of strings
            """

        # Add other analysis types...
        else:
            return f"Analyze this manuscript content: {request.content}"

    def _get_system_prompt(self, analysis_type: AnalysisType) -> str:
        """Get system prompt for analysis type."""
        base_prompt = """You are an expert academic editor assistant.
        Provide accurate, unbiased analysis with clear reasoning.
        Always include confidence scores and supporting evidence."""

        if analysis_type == AnalysisType.DESK_REJECTION:
            return (
                base_prompt
                + """
            Focus on fundamental issues like scope, methodology, and presentation quality.
            Be conservative with rejection recommendations."""
            )

        return base_prompt

    def _parse_ai_response(
        self, request: AIRequest, completion: Any, start_time: float
    ) -> AIResponse:
        """Parse OpenAI response into structured format."""
        content = completion.choices[0].message.content
        usage = completion.usage

        # Parse JSON response
        import json

        try:
            parsed = json.loads(content)
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")
            evidence = parsed.get("evidence", [])
        except (json.JSONDecodeError, ValueError):
            confidence = 0.0
            reasoning = "Failed to parse AI response"
            evidence = []

        # Calculate cost
        total_tokens = usage.total_tokens
        model_cost = self.config.cost_per_1k_tokens.get(request.model.value, 0.03)
        cost = (total_tokens / 1000) * model_cost

        # Determine if human review is required
        human_review_required = confidence < self.config.human_review_confidence_threshold

        # Bias detection (simplified)
        bias_flags = self._detect_bias(content, request.analysis_type)

        return AIResponse(
            request_id=request.id,
            response_id=str(uuid4()),
            model_version=request.model.value,
            content=content,
            confidence_score=confidence,
            reasoning=reasoning,
            evidence=evidence,
            usage_tokens=total_tokens,
            cost_usd=cost,
            processing_time=time.time() - start_time,
            timestamp=datetime.now(UTC),
            human_review_required=human_review_required,
            bias_flags=bias_flags,
        )

    def _detect_bias(self, content: str, analysis_type: AnalysisType) -> list[str]:
        """Simple bias detection - in production would be more sophisticated."""
        if not self.config.enable_bias_detection:
            return []

        flags = []
        content_lower = content.lower()

        # Check for potentially biased language
        bias_terms = [
            "obviously",
            "clearly",
            "simple",
            "trivial",
            "brilliant",
            "genius",
            "stupid",
            "amateur",
        ]

        for term in bias_terms:
            if term in content_lower:
                flags.append(f"potentially_biased_language: {term}")

        return flags

    async def _post_analysis_audit(self, request: AIRequest, response: AIResponse):
        """Create audit record for compliance (Section 5.1)."""
        # Store request and response for audit trail
        self.request_history.append(request)
        self.response_history.append(response)

        # Log audit event
        audit_data = {
            "request_id": request.id,
            "analysis_type": request.analysis_type.value,
            "manuscript_id": request.manuscript_id,
            "confidence_score": response.confidence_score,
            "human_review_required": response.human_review_required,
            "cost_usd": response.cost_usd,
            "bias_flags": response.bias_flags,
        }

        self.logger.log_info(f"AI audit: {audit_data}")

    def _update_usage(self, cost: float):
        """Update usage tracking for budget monitoring."""
        self.daily_usage += cost
        self.monthly_usage += cost

    def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return {
            "daily_usage": self.daily_usage,
            "daily_budget": self.config.daily_budget_usd,
            "daily_remaining": self.config.daily_budget_usd - self.daily_usage,
            "monthly_usage": self.monthly_usage,
            "monthly_budget": self.config.monthly_budget_usd,
            "monthly_remaining": self.config.monthly_budget_usd - self.monthly_usage,
            "requests_today": len(
                [r for r in self.request_history if r.timestamp.date() == datetime.now(UTC).date()]
            ),
        }


@dataclass
class GovernanceResult:
    """Result of AI governance validation."""

    approved: bool
    reason: str
