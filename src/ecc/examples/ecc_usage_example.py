"""Example showing how to use ECC modules in real extraction scenarios."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ecc.core.error_handling import ErrorCollector, SafeExecutor
from src.ecc.core.logging_system import LogCategory, setup_extraction_logging
from src.ecc.core.performance_cache import CacheStrategy, create_extraction_cache
from src.ecc.core.retry_strategies import RetryConfigs, retry


class ECCExtractionExample:
    """Example extractor using all ECC components."""

    def __init__(self):
        # Initialize all ECC components
        self.logger = setup_extraction_logging("example_extractor")
        self.error_collector = ErrorCollector()
        self.safe_executor = SafeExecutor(self.logger.logger)
        self.cache = create_extraction_cache(CacheStrategy.MULTI_TIER)

        # Simulation counters
        self.operations_attempted = 0
        self.operations_successful = 0

    def extract_manuscript_data(self, manuscript_id: str) -> dict:
        """Extract manuscript data using all ECC components."""
        self.logger.enter_context(f"manuscript_{manuscript_id}")

        try:
            self.logger.progress(f"Starting extraction for {manuscript_id}")

            # Check cache first
            cached_data = self.cache.get_cached_status(manuscript_id)
            if cached_data:
                self.logger.success("Using cached manuscript data", LogCategory.DATA)
                return {"id": manuscript_id, "status": cached_data, "source": "cache"}

            # Perform extraction with error handling and retry
            manuscript_data = self._extract_with_retry(manuscript_id)

            # Cache the results
            if manuscript_data:
                self.cache.cache_manuscript_status(
                    manuscript_id, manuscript_data.get("status", "extracted")
                )
                self.logger.success("Manuscript data cached for future use")

            return manuscript_data

        finally:
            self.logger.exit_context(success=True)

    @retry(config=RetryConfigs.STANDARD)
    def _extract_with_retry(self, manuscript_id: str) -> dict:
        """Extract manuscript data with retry logic."""
        self.operations_attempted += 1

        # Simulate extraction steps
        steps_data = {}

        # Step 1: Basic info extraction
        basic_info = self.safe_executor.execute(
            operation=lambda: self._simulate_basic_extraction(manuscript_id),
            operation_name="basic_info_extraction",
            critical=True,
        )
        steps_data.update(basic_info)

        # Step 2: Referee data extraction
        referees = self.safe_executor.execute(
            operation=lambda: self._simulate_referee_extraction(manuscript_id),
            operation_name="referee_extraction",
            default_value=[],
            critical=False,
        )
        steps_data["referees"] = referees

        # Step 3: Document extraction
        documents = self.safe_executor.execute(
            operation=lambda: self._simulate_document_extraction(manuscript_id),
            operation_name="document_extraction",
            default_value=[],
            critical=False,
        )
        steps_data["documents"] = documents

        self.operations_successful += 1
        return steps_data

    def _simulate_basic_extraction(self, manuscript_id: str) -> dict:
        """Simulate basic manuscript info extraction."""
        self.logger.info("Extracting basic manuscript information", LogCategory.EXTRACTION)

        # Simulate potential failure
        if self.operations_attempted == 1 and "FAIL" in manuscript_id:
            raise ConnectionError("Simulated network timeout during basic extraction")

        time.sleep(0.05)  # Simulate extraction time

        basic_data = {
            "id": manuscript_id,
            "title": f"Research Paper {manuscript_id}",
            "status": "Under Review",
            "submission_date": "2025-01-15",
            "journal": "Mathematical Finance",
        }

        self.logger.extraction_success("Basic info extracted successfully")
        return basic_data

    def _simulate_referee_extraction(self, manuscript_id: str) -> list:
        """Simulate referee data extraction."""
        self.logger.info("Extracting referee information", LogCategory.EXTRACTION)

        # Check cache for referee data
        referees = []
        referee_names = ["Dr. Smith", "Prof. Johnson", "Dr. Williams"]

        for name in referee_names:
            cached_referee = self.cache.get_cached_referee(name)
            if cached_referee:
                self.logger.success(f"Using cached data for {name}", LogCategory.DATA)
                referees.append(cached_referee)
            else:
                # Simulate referee lookup
                referee_data = {
                    "name": name,
                    "affiliation": f"University of {name.split()[-1]}",
                    "email": f"{name.lower().replace(' ', '.')}@university.edu",
                    "status": "Review Complete",
                }

                # Cache referee data
                self.cache.cache_referee_data(name, referee_data, ttl=86400)
                referees.append(referee_data)

                self.logger.info(f"Extracted and cached referee: {name}")

        self.logger.extraction_success(f"Extracted {len(referees)} referees")
        return referees

    def _simulate_document_extraction(self, manuscript_id: str) -> list:
        """Simulate document extraction."""
        self.logger.info("Extracting manuscript documents", LogCategory.EXTRACTION)

        time.sleep(0.02)  # Simulate download time

        documents = [
            {"type": "manuscript", "filename": f"{manuscript_id}_manuscript.pdf"},
            {"type": "cover_letter", "filename": f"{manuscript_id}_cover.pdf"},
            {"type": "supplementary", "filename": f"{manuscript_id}_supplement.zip"},
        ]

        self.logger.extraction_success(f"Extracted {len(documents)} documents")
        return documents

    def generate_extraction_report(self) -> dict:
        """Generate comprehensive extraction report."""
        self.logger.progress("Generating extraction report")

        # Collect errors and warnings
        error_summary = {
            "total_errors": len(self.error_collector.errors),
            "total_warnings": len(self.error_collector.warnings),
            "error_details": self.error_collector.errors[-5:],  # Last 5 errors
            "warning_details": self.error_collector.warnings[-5:],  # Last 5 warnings
        }

        # Performance metrics
        performance_metrics = {
            "operations_attempted": self.operations_attempted,
            "operations_successful": self.operations_successful,
            "success_rate": (self.operations_successful / max(1, self.operations_attempted)) * 100,
            "cache_stats": self.cache.cache.stats() if hasattr(self.cache.cache, "stats") else {},
        }

        report = {
            "extraction_summary": performance_metrics,
            "error_summary": error_summary,
            "component_status": {
                "logging": "operational",
                "error_handling": "operational",
                "retry_mechanism": "operational",
                "caching": "operational",
            },
        }

        self.logger.success("Extraction report generated")
        return report


def demonstrate_ecc_usage():
    """Demonstrate comprehensive ECC module usage."""
    extractor = ECCExtractionExample()
    extractor.logger.info("🚀 ECC MODULES USAGE DEMONSTRATION")
    extractor.logger.info("=" * 60)

    # Test manuscripts (including one that will initially fail)
    manuscripts = ["MS-2025-001", "MS-2025-002", "MS-FAIL-003"]

    extraction_results = []

    for manuscript_id in manuscripts:
        extractor.logger.info(f"\n📄 Processing {manuscript_id}")
        try:
            result = extractor.extract_manuscript_data(manuscript_id)
            extraction_results.append(result)
            extractor.logger.success(
                f"{manuscript_id}: {result.get('source', 'extracted')} - {len(result.get('referees', []))} referees"
            )
        except Exception as e:
            extractor.logger.error(f"{manuscript_id}: Failed - {e}")

    # Test cache performance
    extractor.logger.info("\n🔄 Testing cache performance...")
    start_time = time.time()
    cached_result = extractor.extract_manuscript_data("MS-2025-001")  # Should hit cache
    cache_time = time.time() - start_time
    extractor.logger.success(
        f"Cache retrieval: {cache_time:.4f}s (Source: {cached_result.get('source')})"
    )

    # Generate comprehensive report
    extractor.logger.info("\n📊 EXTRACTION REPORT")
    extractor.logger.info("-" * 40)
    report = extractor.generate_extraction_report()

    extractor.logger.info(
        f"Operations: {report['extraction_summary']['operations_attempted']} attempted, "
        f"{report['extraction_summary']['operations_successful']} successful"
    )
    extractor.logger.info(f"Success Rate: {report['extraction_summary']['success_rate']:.1f}%")
    extractor.logger.info(f"Errors: {report['error_summary']['total_errors']}")
    extractor.logger.info(f"Warnings: {report['error_summary']['total_warnings']}")
    extractor.logger.info(
        f"Components: {', '.join(report['component_status'].keys())} all operational"
    )

    extractor.logger.success("ECC MODULES SUCCESSFULLY INTEGRATED!")
    extractor.logger.info("Benefits demonstrated:")
    extractor.logger.info("   • Centralized logging with context management")
    extractor.logger.info("   • Automatic error handling and collection")
    extractor.logger.info("   • Retry mechanisms for resilient operations")
    extractor.logger.info("   • Multi-tier caching for performance")
    extractor.logger.info("   • Comprehensive monitoring and reporting")


if __name__ == "__main__":
    demonstrate_ecc_usage()
