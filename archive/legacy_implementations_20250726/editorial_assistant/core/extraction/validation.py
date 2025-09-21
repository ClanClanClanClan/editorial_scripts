"""
Extraction Result Validation

Provides comprehensive validation for extraction results to ensure
data quality and consistency across all journal platforms.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import ExtractionResult, ExtractionStatus


class ValidationSeverity(Enum):
    """Validation issue severity levels."""

    ERROR = "error"  # Critical issues that invalidate the extraction
    WARNING = "warning"  # Issues that reduce quality but don't invalidate
    INFO = "info"  # Informational notices about extraction


@dataclass
class ValidationIssue:
    """Individual validation issue."""

    severity: ValidationSeverity
    category: str
    message: str
    field: str | None = None
    value: Any | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """
    Result of extraction validation.

    Provides detailed analysis of extraction quality and identifies
    specific issues that need attention.
    """

    is_valid: bool = True
    overall_score: float = 0.0
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def add_issue(
        self,
        severity: ValidationSeverity,
        category: str,
        message: str,
        field: str = None,
        value: Any = None,
        suggestion: str = None,
    ) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            field=field,
            value=value,
            suggestion=suggestion,
        )
        self.issues.append(issue)

        # Mark as invalid if we have errors
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation for improvement."""
        self.recommendations.append(recommendation)

    def get_issues_by_severity(self, severity: ValidationSeverity) -> list[ValidationIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_category(self, category: str) -> list[ValidationIssue]:
        """Get issues filtered by category."""
        return [issue for issue in self.issues if issue.category == category]

    def has_errors(self) -> bool:
        """Check if validation has any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if validation has any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)


class QualityValidator:
    """
    Comprehensive quality validator for extraction results.

    Validates extraction results against quality standards and
    identifies specific areas for improvement.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize quality validator.

        Args:
            strict_mode: Whether to use strict validation rules
        """
        self.strict_mode = strict_mode

        # Quality thresholds
        self.thresholds = {
            "minimum_overall_score": 0.6,
            "minimum_manuscript_completeness": 0.7,
            "minimum_referee_completeness": 0.5,
            "minimum_data_integrity": 0.8,
            "preferred_pdf_success_rate": 0.6,
            "maximum_error_rate": 0.2,
        }

        if strict_mode:
            # Stricter thresholds for production use
            self.thresholds.update(
                {
                    "minimum_overall_score": 0.8,
                    "minimum_manuscript_completeness": 0.9,
                    "minimum_referee_completeness": 0.7,
                    "minimum_data_integrity": 0.95,
                    "preferred_pdf_success_rate": 0.8,
                    "maximum_error_rate": 0.1,
                }
            )

    def validate_extraction_result(
        self, result: ExtractionResult, minimum_quality_threshold: float = None
    ) -> ValidationResult:
        """
        Validate complete extraction result.

        Args:
            result: Extraction result to validate
            minimum_quality_threshold: Override minimum quality threshold

        Returns:
            ValidationResult with detailed analysis
        """
        validation = ValidationResult()

        # Use provided threshold or default
        min_threshold = minimum_quality_threshold or self.thresholds["minimum_overall_score"]

        # Validate basic structure
        self._validate_structure(result, validation)

        # Validate data content
        self._validate_manuscripts(result, validation)
        self._validate_referees(result, validation)
        self._validate_pdfs(result, validation)

        # Validate quality metrics
        self._validate_quality_score(result, validation, min_threshold)
        self._validate_metrics(result, validation)

        # Validate status consistency
        self._validate_status(result, validation)

        # Generate summary and recommendations
        self._generate_summary(result, validation)
        self._generate_recommendations(result, validation)

        return validation

    def _validate_structure(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate basic result structure."""
        # Check required fields
        if not result.manuscripts and not result.referees:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "structure",
                "No manuscripts or referees extracted",
                suggestion="Check authentication and navigation logic",
            )

        if not result.metadata:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "structure",
                "Missing extraction metadata",
                suggestion="Add metadata tracking to extraction process",
            )

        if not result.quality_score:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "structure",
                "Missing quality score calculation",
                suggestion="Ensure quality score is calculated",
            )

        if not result.metrics:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "structure",
                "Missing detailed metrics",
                suggestion="Add comprehensive metrics tracking",
            )

    def _validate_manuscripts(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate manuscript data."""
        if not result.manuscripts:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "manuscripts",
                "No manuscripts extracted",
                suggestion="Verify manuscript detection logic",
            )
            return

        # Check manuscript quality
        manuscripts_with_ids = 0
        manuscripts_with_titles = 0
        manuscripts_with_referees = 0

        for i, manuscript in enumerate(result.manuscripts):
            # Check required fields
            if not hasattr(manuscript, "manuscript_id") or not manuscript.manuscript_id:
                validation.add_issue(
                    ValidationSeverity.ERROR,
                    "manuscripts",
                    f"Manuscript {i+1} missing ID",
                    field="manuscript_id",
                    suggestion="Improve manuscript ID extraction logic",
                )
            else:
                manuscripts_with_ids += 1

            # Check preferred fields
            if not hasattr(manuscript, "title") or not manuscript.title:
                validation.add_issue(
                    ValidationSeverity.WARNING,
                    "manuscripts",
                    f"Manuscript {i+1} missing title",
                    field="title",
                    suggestion="Improve title extraction logic",
                )
            else:
                manuscripts_with_titles += 1

            # Check referee data
            if hasattr(manuscript, "referees") and manuscript.referees:
                manuscripts_with_referees += 1

        # Overall manuscript quality
        total_manuscripts = len(result.manuscripts)
        id_completeness = manuscripts_with_ids / total_manuscripts
        title_completeness = manuscripts_with_titles / total_manuscripts
        referee_coverage = manuscripts_with_referees / total_manuscripts

        if id_completeness < self.thresholds["minimum_manuscript_completeness"]:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "manuscripts",
                f"Only {id_completeness:.1%} of manuscripts have IDs",
                value=id_completeness,
                suggestion="Fix manuscript ID extraction patterns",
            )

        if title_completeness < 0.8:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "manuscripts",
                f"Only {title_completeness:.1%} of manuscripts have titles",
                value=title_completeness,
                suggestion="Improve title extraction patterns",
            )

        if referee_coverage < 0.7:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "manuscripts",
                f"Only {referee_coverage:.1%} of manuscripts have referee data",
                value=referee_coverage,
                suggestion="Verify referee data extraction logic",
            )

    def _validate_referees(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate referee data."""
        total_referees = 0
        referees_with_names = 0
        referees_with_emails = 0
        referees_with_institutions = 0
        referees_with_status = 0

        # Collect referee data from manuscripts
        for manuscript in result.manuscripts:
            if hasattr(manuscript, "referees") and manuscript.referees:
                for referee in manuscript.referees:
                    total_referees += 1

                    if hasattr(referee, "name") and referee.name:
                        referees_with_names += 1

                    if hasattr(referee, "email") and referee.email:
                        referees_with_emails += 1

                    if hasattr(referee, "institution") and referee.institution:
                        referees_with_institutions += 1

                    if hasattr(referee, "status") and referee.status:
                        referees_with_status += 1

        # Add standalone referees
        for referee in result.referees:
            total_referees += 1

            if hasattr(referee, "name") and referee.name:
                referees_with_names += 1

            if hasattr(referee, "email") and referee.email:
                referees_with_emails += 1

            if hasattr(referee, "institution") and referee.institution:
                referees_with_institutions += 1

            if hasattr(referee, "status") and referee.status:
                referees_with_status += 1

        if total_referees == 0:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "referees",
                "No referee data extracted",
                suggestion="Check referee extraction logic and selectors",
            )
            return

        # Calculate completion rates
        name_completeness = referees_with_names / total_referees
        email_completeness = referees_with_emails / total_referees
        institution_completeness = referees_with_institutions / total_referees
        status_completeness = referees_with_status / total_referees

        # Validate completeness
        if name_completeness < 0.9:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "referees",
                f"Only {name_completeness:.1%} of referees have names",
                value=name_completeness,
                suggestion="Fix referee name extraction patterns",
            )

        if email_completeness < self.thresholds["minimum_referee_completeness"]:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "referees",
                f"Only {email_completeness:.1%} of referees have email addresses",
                value=email_completeness,
                suggestion="Improve email extraction or implement email lookup",
            )

        if institution_completeness < 0.3:
            validation.add_issue(
                ValidationSeverity.INFO,
                "referees",
                f"Only {institution_completeness:.1%} of referees have institutions",
                value=institution_completeness,
                suggestion="Consider improving institution extraction",
            )

    def _validate_pdfs(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate PDF downloads."""
        if not result.pdfs:
            validation.add_issue(
                ValidationSeverity.INFO,
                "pdfs",
                "No PDFs downloaded",
                suggestion="Implement PDF download functionality if needed",
            )
            return

        # Check PDF file validity
        valid_pdfs = 0
        for pdf_path in result.pdfs:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                valid_pdfs += 1

        pdf_success_rate = valid_pdfs / len(result.pdfs)

        if pdf_success_rate < self.thresholds["preferred_pdf_success_rate"]:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "pdfs",
                f"PDF download success rate: {pdf_success_rate:.1%}",
                value=pdf_success_rate,
                suggestion="Improve PDF download reliability",
            )

    def _validate_quality_score(
        self, result: ExtractionResult, validation: ValidationResult, minimum_threshold: float
    ) -> None:
        """Validate quality score."""
        score = result.quality_score

        if score.overall_score < minimum_threshold:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "quality",
                f"Overall quality score {score.overall_score:.3f} below threshold {minimum_threshold:.3f}",
                value=score.overall_score,
                suggestion="Improve extraction logic to increase quality",
            )

        # Check component scores
        if score.manuscript_completeness < self.thresholds["minimum_manuscript_completeness"]:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "quality",
                f"Manuscript completeness {score.manuscript_completeness:.3f} below target",
                value=score.manuscript_completeness,
            )

        if score.referee_completeness < self.thresholds["minimum_referee_completeness"]:
            validation.add_issue(
                ValidationSeverity.WARNING,
                "quality",
                f"Referee completeness {score.referee_completeness:.3f} below target",
                value=score.referee_completeness,
            )

        if score.data_integrity < self.thresholds["minimum_data_integrity"]:
            validation.add_issue(
                ValidationSeverity.ERROR,
                "quality",
                f"Data integrity {score.data_integrity:.3f} below target",
                value=score.data_integrity,
                suggestion="Reduce errors in extraction process",
            )

    def _validate_metrics(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate extraction metrics."""
        metrics = result.metrics

        # Check error rates
        total_operations = metrics.total_manuscripts_processed + metrics.total_pdfs_downloaded

        if total_operations > 0:
            total_errors = (
                metrics.authentication_errors
                + metrics.navigation_errors
                + metrics.parsing_errors
                + metrics.download_errors
            )

            error_rate = total_errors / total_operations

            if error_rate > self.thresholds["maximum_error_rate"]:
                validation.add_issue(
                    ValidationSeverity.ERROR,
                    "metrics",
                    f"Error rate {error_rate:.1%} exceeds maximum {self.thresholds['maximum_error_rate']:.1%}",
                    value=error_rate,
                    suggestion="Investigate and fix sources of errors",
                )

        # Check performance metrics
        if metrics.total_extraction_time > 600:  # 10 minutes
            validation.add_issue(
                ValidationSeverity.WARNING,
                "metrics",
                f"Extraction time {metrics.total_extraction_time:.1f}s exceeds recommended 600s",
                value=metrics.total_extraction_time,
                suggestion="Optimize extraction performance",
            )

    def _validate_status(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Validate extraction status consistency."""
        # Check status matches data quality
        if result.status == ExtractionStatus.SUCCESS:
            if result.quality_score.overall_score < 0.7:
                validation.add_issue(
                    ValidationSeverity.WARNING,
                    "status",
                    "Status marked as SUCCESS but quality score is low",
                    suggestion="Review status determination logic",
                )

        elif result.status == ExtractionStatus.FAILED:
            if result.has_usable_data():
                validation.add_issue(
                    ValidationSeverity.WARNING,
                    "status",
                    "Status marked as FAILED but usable data was extracted",
                    suggestion="Consider PARTIAL_SUCCESS status",
                )

    def _generate_summary(self, result: ExtractionResult, validation: ValidationResult) -> None:
        """Generate validation summary."""
        errors = validation.get_issues_by_severity(ValidationSeverity.ERROR)
        warnings = validation.get_issues_by_severity(ValidationSeverity.WARNING)
        infos = validation.get_issues_by_severity(ValidationSeverity.INFO)

        validation.summary = {
            "total_issues": len(validation.issues),
            "errors": len(errors),
            "warnings": len(warnings),
            "infos": len(infos),
            "is_valid": validation.is_valid,
            "overall_score": result.quality_score.overall_score,
            "quality_assessment": self._assess_quality(result.quality_score.overall_score),
        }

    def _generate_recommendations(
        self, result: ExtractionResult, validation: ValidationResult
    ) -> None:
        """Generate improvement recommendations."""
        # Priority recommendations based on issues
        error_categories = {
            issue.category
            for issue in validation.issues
            if issue.severity == ValidationSeverity.ERROR
        }

        if "structure" in error_categories:
            validation.add_recommendation(
                "Fix basic extraction structure issues first - ensure basic data is being extracted"
            )

        if "manuscripts" in error_categories:
            validation.add_recommendation("Improve manuscript detection and ID extraction patterns")

        if "referees" in error_categories:
            validation.add_recommendation("Review referee extraction selectors and parsing logic")

        if "quality" in error_categories:
            validation.add_recommendation(
                "Overall extraction quality needs improvement - review all extraction steps"
            )

        # General recommendations based on quality score
        if result.quality_score.overall_score < 0.5:
            validation.add_recommendation(
                "Consider implementing fail-safe extraction methods or fallback strategies"
            )
        elif result.quality_score.overall_score < 0.8:
            validation.add_recommendation(
                "Focus on improving data completeness and reducing errors"
            )

        # Specific feature recommendations
        if not result.quality_score.has_referee_emails:
            validation.add_recommendation(
                "Implement email extraction or email lookup functionality"
            )

        if not result.quality_score.has_manuscript_pdfs:
            validation.add_recommendation("Consider implementing PDF download functionality")

    def _assess_quality(self, score: float) -> str:
        """Assess quality level from score."""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Acceptable"
        elif score >= 0.5:
            return "Poor"
        else:
            return "Very Poor"
