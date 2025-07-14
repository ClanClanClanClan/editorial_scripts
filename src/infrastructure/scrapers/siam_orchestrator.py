"""
SIAM Scraper Orchestrator - Manages extraction from multiple SIAM journals
Provides retry logic, error recovery, and AI-enhanced data validation
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.infrastructure.scrapers.siam_scraper import SIAMScraper, ScrapingResult
from src.core.domain.manuscript import Manuscript
from src.infrastructure.config import settings


@dataclass
class OrchestrationResult:
    """Result of orchestrated scraping across multiple journals"""
    success: bool
    total_manuscripts: int
    results_by_journal: Dict[str, ScrapingResult]
    total_time: timedelta
    errors: List[str]
    metadata: Dict[str, Any]


class SIAMScrapingOrchestrator:
    """Orchestrates scraping across SIAM journals with advanced features"""
    
    SUPPORTED_JOURNALS = ['SICON', 'SIFIN']
    
    def __init__(self, journals: Optional[List[str]] = None):
        """Initialize orchestrator"""
        self.journals = journals or self.SUPPORTED_JOURNALS
        self.logger = logging.getLogger("scrapers.siam_orchestrator")
        self.setup_logging()
        
        # Validate journal codes
        invalid_journals = set(self.journals) - set(self.SUPPORTED_JOURNALS)
        if invalid_journals:
            raise ValueError(f"Unsupported journals: {invalid_journals}")
    
    def setup_logging(self):
        """Setup structured logging"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.handlers.clear()
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
    
    async def run_parallel_extraction(self, max_concurrent: int = 2) -> OrchestrationResult:
        """Run extraction from multiple journals in parallel"""
        start_time = datetime.now()
        
        self.logger.info(f"🚀 Starting parallel SIAM extraction for {len(self.journals)} journals")
        self.logger.info(f"📋 Journals: {', '.join(self.journals)}")
        self.logger.info(f"⚡ Max concurrent: {max_concurrent}")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create extraction tasks
        tasks = []
        for journal_code in self.journals:
            task = self._extract_with_semaphore(semaphore, journal_code)
            tasks.append(task)
        
        # Execute tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results_by_journal = {}
        total_manuscripts = 0
        errors = []
        
        for i, result in enumerate(results):
            journal_code = self.journals[i]
            
            if isinstance(result, Exception):
                error_msg = f"Failed to extract from {journal_code}: {result}"
                errors.append(error_msg)
                self.logger.error(f"❌ {error_msg}")
                
                # Create failed result
                results_by_journal[journal_code] = ScrapingResult(
                    success=False,
                    manuscripts=[],
                    total_count=0,
                    extraction_time=timedelta(0),
                    journal_code=journal_code,
                    error_message=str(result)
                )
            else:
                results_by_journal[journal_code] = result
                total_manuscripts += result.total_count
                
                if result.success:
                    self.logger.info(f"✅ {journal_code}: {result.total_count} manuscripts extracted")
                else:
                    error_msg = f"{journal_code} extraction failed: {result.error_message}"
                    errors.append(error_msg)
                    self.logger.error(f"❌ {error_msg}")
        
        total_time = datetime.now() - start_time
        overall_success = len(errors) == 0
        
        # Create orchestration result
        orchestration_result = OrchestrationResult(
            success=overall_success,
            total_manuscripts=total_manuscripts,
            results_by_journal=results_by_journal,
            total_time=total_time,
            errors=errors,
            metadata={
                'extraction_timestamp': datetime.now().isoformat(),
                'orchestrator_version': '1.0',
                'parallel_execution': True,
                'max_concurrent': max_concurrent,
                'journals_attempted': self.journals,
                'successful_journals': [j for j, r in results_by_journal.items() if r.success]
            }
        )
        
        # Log summary
        self._log_orchestration_summary(orchestration_result)
        
        return orchestration_result
    
    async def _extract_with_semaphore(self, semaphore: asyncio.Semaphore, journal_code: str) -> ScrapingResult:
        """Extract from a journal with semaphore control"""
        async with semaphore:
            self.logger.info(f"🔄 Starting extraction from {journal_code}")
            
            try:
                # Create scraper instance
                scraper = SIAMScraper(journal_code)
                
                # Run extraction with retry logic
                result = await self._extract_with_retry(scraper, max_retries=3)
                
                return result
                
            except Exception as e:
                self.logger.error(f"❌ Fatal error extracting from {journal_code}: {e}")
                raise
    
    async def _extract_with_retry(self, scraper: SIAMScraper, max_retries: int = 3) -> ScrapingResult:
        """Extract with exponential backoff retry logic"""
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"🔄 Retry attempt {attempt}/{max_retries} for {scraper.journal_code} after {delay}s delay")
                    await asyncio.sleep(delay)
                
                result = await scraper.run_extraction()
                
                if result.success:
                    self.logger.info(f"✅ Successful extraction from {scraper.journal_code} on attempt {attempt + 1}")
                    return result
                else:
                    if attempt < max_retries:
                        self.logger.warning(f"⚠️ Extraction failed for {scraper.journal_code}, will retry: {result.error_message}")
                    else:
                        self.logger.error(f"❌ Final attempt failed for {scraper.journal_code}: {result.error_message}")
                        return result
                
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"⚠️ Exception on attempt {attempt + 1} for {scraper.journal_code}, will retry: {e}")
                else:
                    self.logger.error(f"❌ Final attempt exception for {scraper.journal_code}: {e}")
                    raise
        
        # This should never be reached
        raise Exception(f"Unexpected end of retry logic for {scraper.journal_code}")
    
    async def run_sequential_extraction(self) -> OrchestrationResult:
        """Run extraction from journals sequentially (safer but slower)"""
        start_time = datetime.now()
        
        self.logger.info(f"🚀 Starting sequential SIAM extraction for {len(self.journals)} journals")
        
        results_by_journal = {}
        total_manuscripts = 0
        errors = []
        
        for journal_code in self.journals:
            try:
                self.logger.info(f"🔄 Extracting from {journal_code}")
                
                # Create scraper
                scraper = SIAMScraper(journal_code)
                
                # Run extraction with retry
                result = await self._extract_with_retry(scraper, max_retries=2)
                
                results_by_journal[journal_code] = result
                
                if result.success:
                    total_manuscripts += result.total_count
                    self.logger.info(f"✅ {journal_code}: {result.total_count} manuscripts extracted")
                else:
                    error_msg = f"{journal_code} extraction failed: {result.error_message}"
                    errors.append(error_msg)
                    self.logger.error(f"❌ {error_msg}")
                
                # Delay between journals to be respectful with stealth
                if journal_code != self.journals[-1]:  # Not the last journal
                    import random
                    delay = random.uniform(4, 8)  # Variable delay
                    await asyncio.sleep(delay)
                
            except Exception as e:
                error_msg = f"Fatal error extracting from {journal_code}: {e}"
                errors.append(error_msg)
                self.logger.error(f"❌ {error_msg}")
                
                # Create failed result
                results_by_journal[journal_code] = ScrapingResult(
                    success=False,
                    manuscripts=[],
                    total_count=0,
                    extraction_time=timedelta(0),
                    journal_code=journal_code,
                    error_message=str(e)
                )
        
        total_time = datetime.now() - start_time
        overall_success = len(errors) == 0
        
        # Create orchestration result
        orchestration_result = OrchestrationResult(
            success=overall_success,
            total_manuscripts=total_manuscripts,
            results_by_journal=results_by_journal,
            total_time=total_time,
            errors=errors,
            metadata={
                'extraction_timestamp': datetime.now().isoformat(),
                'orchestrator_version': '1.0',
                'parallel_execution': False,
                'journals_attempted': self.journals,
                'successful_journals': [j for j, r in results_by_journal.items() if r.success]
            }
        )
        
        # Log summary
        self._log_orchestration_summary(orchestration_result)
        
        return orchestration_result
    
    def _log_orchestration_summary(self, result: OrchestrationResult):
        """Log orchestration summary"""
        self.logger.info("=" * 60)
        self.logger.info("🎯 SIAM EXTRACTION ORCHESTRATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Overall Success: {'✅ YES' if result.success else '❌ NO'}")
        self.logger.info(f"Total Manuscripts: {result.total_manuscripts}")
        self.logger.info(f"Total Time: {result.total_time}")
        self.logger.info(f"Journals Attempted: {len(result.results_by_journal)}")
        
        successful_count = sum(1 for r in result.results_by_journal.values() if r.success)
        self.logger.info(f"Successful Journals: {successful_count}/{len(result.results_by_journal)}")
        
        self.logger.info("\n📊 Results by Journal:")
        for journal_code, journal_result in result.results_by_journal.items():
            status = "✅ SUCCESS" if journal_result.success else "❌ FAILED"
            self.logger.info(f"  {journal_code}: {status} - {journal_result.total_count} manuscripts")
            if not journal_result.success and journal_result.error_message:
                self.logger.info(f"    Error: {journal_result.error_message}")
        
        if result.errors:
            self.logger.info(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                self.logger.info(f"  - {error}")
        
        self.logger.info("=" * 60)
    
    async def validate_extraction_data(self, orchestration_result: OrchestrationResult) -> Dict[str, Any]:
        """Validate extracted data using AI-enhanced validation"""
        validation_results = {}
        
        self.logger.info("🔍 Starting AI-enhanced data validation")
        
        for journal_code, result in orchestration_result.results_by_journal.items():
            if not result.success or not result.manuscripts:
                validation_results[journal_code] = {
                    'validated': False,
                    'reason': 'No data to validate'
                }
                continue
            
            try:
                # Basic validation checks
                validation_score = await self._calculate_validation_score(result.manuscripts)
                
                validation_results[journal_code] = {
                    'validated': validation_score >= 0.8,
                    'score': validation_score,
                    'manuscript_count': len(result.manuscripts),
                    'data_quality_issues': await self._identify_data_quality_issues(result.manuscripts)
                }
                
                self.logger.info(f"✅ {journal_code} validation score: {validation_score:.2f}")
                
            except Exception as e:
                self.logger.error(f"❌ Validation failed for {journal_code}: {e}")
                validation_results[journal_code] = {
                    'validated': False,
                    'error': str(e)
                }
        
        return validation_results
    
    async def _calculate_validation_score(self, manuscripts: List[Manuscript]) -> float:
        """Calculate data validation score"""
        if not manuscripts:
            return 0.0
        
        total_score = 0.0
        
        for manuscript in manuscripts:
            manuscript_score = 0.0
            max_points = 5.0
            
            # Check required fields
            if manuscript.id:
                manuscript_score += 1.0
            if manuscript.title and len(manuscript.title) > 5:
                manuscript_score += 1.0
            if manuscript.journal_code:
                manuscript_score += 1.0
            if manuscript.submission_date:
                manuscript_score += 1.0
            if manuscript.referees:
                manuscript_score += 1.0
            
            total_score += manuscript_score / max_points
        
        return total_score / len(manuscripts)
    
    async def _identify_data_quality_issues(self, manuscripts: List[Manuscript]) -> List[str]:
        """Identify data quality issues"""
        issues = []
        
        # Check for missing required data
        missing_ids = sum(1 for m in manuscripts if not m.id)
        if missing_ids > 0:
            issues.append(f"{missing_ids} manuscripts missing IDs")
        
        missing_titles = sum(1 for m in manuscripts if not m.title or len(m.title) < 5)
        if missing_titles > 0:
            issues.append(f"{missing_titles} manuscripts with missing/short titles")
        
        missing_dates = sum(1 for m in manuscripts if not m.submission_date)
        if missing_dates > 0:
            issues.append(f"{missing_dates} manuscripts missing submission dates")
        
        no_referees = sum(1 for m in manuscripts if not m.referees)
        if no_referees > 0:
            issues.append(f"{no_referees} manuscripts with no referee information")
        
        return issues
    
    def get_all_manuscripts(self, orchestration_result: OrchestrationResult) -> List[Manuscript]:
        """Get all manuscripts from orchestration result"""
        all_manuscripts = []
        
        for journal_result in orchestration_result.results_by_journal.values():
            if journal_result.success:
                all_manuscripts.extend(journal_result.manuscripts)
        
        return all_manuscripts
    
    def export_results_summary(self, orchestration_result: OrchestrationResult) -> Dict[str, Any]:
        """Export results summary for reporting"""
        summary = {
            'extraction_summary': {
                'timestamp': orchestration_result.metadata.get('extraction_timestamp'),
                'success': orchestration_result.success,
                'total_manuscripts': orchestration_result.total_manuscripts,
                'total_time_seconds': orchestration_result.total_time.total_seconds(),
                'journals_attempted': len(orchestration_result.results_by_journal),
                'successful_journals': len([r for r in orchestration_result.results_by_journal.values() if r.success])
            },
            'journal_results': {},
            'error_summary': {
                'total_errors': len(orchestration_result.errors),
                'errors': orchestration_result.errors
            }
        }
        
        # Add per-journal results
        for journal_code, result in orchestration_result.results_by_journal.items():
            summary['journal_results'][journal_code] = {
                'success': result.success,
                'manuscript_count': result.total_count,
                'extraction_time_seconds': result.extraction_time.total_seconds(),
                'error_message': result.error_message
            }
        
        return summary


# Convenience functions for easy usage
async def extract_all_siam_journals(parallel: bool = True, max_concurrent: int = 2) -> OrchestrationResult:
    """Extract from all SIAM journals"""
    orchestrator = SIAMScrapingOrchestrator()
    
    if parallel:
        return await orchestrator.run_parallel_extraction(max_concurrent=max_concurrent)
    else:
        return await orchestrator.run_sequential_extraction()


async def extract_specific_siam_journals(journal_codes: List[str], parallel: bool = True) -> OrchestrationResult:
    """Extract from specific SIAM journals"""
    orchestrator = SIAMScrapingOrchestrator(journals=journal_codes)
    
    if parallel:
        return await orchestrator.run_parallel_extraction()
    else:
        return await orchestrator.run_sequential_extraction()