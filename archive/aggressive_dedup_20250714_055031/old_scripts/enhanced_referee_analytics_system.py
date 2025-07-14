#!/usr/bin/env python3
"""
Enhanced Referee Analytics System with Report Preservation and Advanced Analytics
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import hashlib
import aiofiles
import re
from dataclasses import dataclass, asdict
from enum import Enum

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    LATE = "late"
    DECLINED = "declined"
    ACCEPTED = "accepted"
    REMINDED = "reminded"


@dataclass
class RefereeReport:
    """Structured referee report data"""
    manuscript_id: str
    journal: str
    referee_email: str
    report_text: str
    recommendation: Optional[str] = None
    review_date: Optional[str] = None
    submission_date: Optional[str] = None
    review_status: str = "submitted"
    
    # Analytics fields
    word_count: int = 0
    sentiment_score: Optional[float] = None
    key_topics: List[str] = None
    review_quality_score: Optional[float] = None
    
    # Technical metrics
    technical_depth: Optional[str] = None  # "shallow", "moderate", "deep"
    constructiveness: Optional[str] = None  # "destructive", "neutral", "constructive"
    review_type: Optional[str] = None  # "accept", "minor_revision", "major_revision", "reject"
    
    # Extraction metadata
    extraction_timestamp: str = ""
    extraction_method: str = "scraper"
    extraction_confidence: float = 1.0

    def __post_init__(self):
        if self.key_topics is None:
            self.key_topics = []
        if self.extraction_timestamp == "":
            self.extraction_timestamp = datetime.now().isoformat()
        if self.report_text:
            self.word_count = len(self.report_text.split())


class EnhancedRefereeAnalytics:
    """Enhanced referee analytics with report preservation and advanced analytics"""
    
    def __init__(self, base_dir: Path):
        self.cache_dir = base_dir / "enhanced_referee_analytics"
        self.reports_dir = self.cache_dir / "reports"
        self.analytics_dir = self.cache_dir / "analytics"
        self.referees_dir = self.cache_dir / "referees"
        self.manuscripts_dir = self.cache_dir / "manuscripts"
        
        # Create directories
        for directory in [self.cache_dir, self.reports_dir, self.analytics_dir, 
                         self.referees_dir, self.manuscripts_dir]:
            directory.mkdir(exist_ok=True)
        
        logger.info(f"📊 Enhanced referee analytics initialized: {self.cache_dir}")
    
    def get_report_file(self, manuscript_id: str, referee_email: str) -> Path:
        """Get path for individual report file"""
        email_hash = hashlib.md5(referee_email.encode()).hexdigest()[:8]
        return self.reports_dir / f"report_{manuscript_id}_{email_hash}.json"
    
    def get_referee_file(self, referee_email: str) -> Path:
        """Get referee comprehensive analytics file"""
        email_hash = hashlib.md5(referee_email.encode()).hexdigest()
        return self.referees_dir / f"referee_{email_hash}.json"
    
    async def extract_report_from_page_content(self, page_content: str, manuscript_id: str) -> List[RefereeReport]:
        """Extract referee reports from page HTML content"""
        reports = []
        
        # Common patterns for referee reports
        report_patterns = [
            r'Report from Referee.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}).*?(Report:.*?)(?=Report from|$)',
            r'Referee.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}).*?Comments:(.*?)(?=Referee|$)',
            r'Review by.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})(.*?)(?=Review by|$)',
        ]
        
        # Look for structured report sections
        for pattern in report_patterns:
            matches = re.finditer(pattern, page_content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    referee_email = match.group(1).lower()
                    report_content = match.group(2).strip()
                    
                    if len(report_content) > 50:  # Minimum meaningful report length
                        # Extract recommendation if present
                        recommendation = self._extract_recommendation(report_content)
                        
                        # Create report object
                        report = RefereeReport(
                            manuscript_id=manuscript_id,
                            journal="",  # Will be filled by caller
                            referee_email=referee_email,
                            report_text=report_content,
                            recommendation=recommendation,
                            extraction_method="html_pattern_matching"
                        )
                        
                        # Analyze report content
                        await self._analyze_report_content(report)
                        
                        reports.append(report)
                        logger.info(f"📄 Extracted report from {referee_email} for {manuscript_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to parse report match: {e}")
                    continue
        
        return reports
    
    def _extract_recommendation(self, report_text: str) -> Optional[str]:
        """Extract recommendation from report text"""
        text_lower = report_text.lower()
        
        # Common recommendation patterns
        if any(word in text_lower for word in ['accept', 'publication']):
            if any(word in text_lower for word in ['minor revision', 'minor changes']):
                return "minor_revision"
            elif any(word in text_lower for word in ['major revision', 'major changes']):
                return "major_revision"
            else:
                return "accept"
        elif any(word in text_lower for word in ['reject', 'decline', 'not suitable']):
            return "reject"
        
        return None
    
    async def _analyze_report_content(self, report: RefereeReport):
        """Analyze report content for quality metrics"""
        text = report.report_text.lower()
        
        # Technical depth analysis
        technical_indicators = {
            'deep': ['methodology', 'algorithm', 'proof', 'theorem', 'mathematical', 'statistical', 'experimental design'],
            'moderate': ['method', 'approach', 'analysis', 'results', 'conclusion', 'literature'],
            'shallow': ['overall', 'general', 'seems', 'appears', 'good', 'bad']
        }
        
        depth_scores = {}
        for depth, indicators in technical_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            depth_scores[depth] = score
        
        report.technical_depth = max(depth_scores, key=depth_scores.get)
        
        # Constructiveness analysis
        constructive_words = ['suggest', 'recommend', 'improve', 'consider', 'perhaps', 'could', 'might']
        destructive_words = ['terrible', 'awful', 'completely wrong', 'useless', 'nonsense']
        
        constructive_count = sum(1 for word in constructive_words if word in text)
        destructive_count = sum(1 for word in destructive_words if word in text)
        
        if constructive_count > destructive_count * 2:
            report.constructiveness = "constructive"
        elif destructive_count > constructive_count:
            report.constructiveness = "destructive"
        else:
            report.constructiveness = "neutral"
        
        # Quality score (0-100)
        quality_factors = [
            min(report.word_count / 100, 10),  # Length factor (max 10 points)
            constructive_count * 2,  # Constructiveness (max ~10 points)
            depth_scores.get('deep', 0) * 3,  # Technical depth (max ~15 points)
            5 if report.recommendation else 0,  # Has clear recommendation
        ]
        
        report.review_quality_score = min(sum(quality_factors), 100)
        
        # Extract key topics
        topic_patterns = {
            'methodology': r'(method|approach|technique|algorithm)',
            'results': r'(result|finding|outcome|conclusion)',
            'literature': r'(reference|citation|related work|prior)',
            'writing': r'(writing|clarity|presentation|language)',
            'novelty': r'(novel|original|contribution|significance)'
        }
        
        report.key_topics = []
        for topic, pattern in topic_patterns.items():
            if re.search(pattern, text):
                report.key_topics.append(topic)
    
    async def save_referee_report(self, report: RefereeReport, journal: str):
        """Save individual referee report permanently"""
        report.journal = journal
        
        # Save individual report
        report_file = self.get_report_file(report.manuscript_id, report.referee_email)
        
        try:
            async with aiofiles.open(report_file, 'w') as f:
                await f.write(json.dumps(asdict(report), indent=2, default=str))
            
            logger.info(f"💾 Saved report: {report.manuscript_id} by {report.referee_email}")
        except Exception as e:
            logger.error(f"Failed to save report {report_file}: {e}")
        
        # Update referee comprehensive analytics
        await self._update_referee_analytics(report)
    
    async def _update_referee_analytics(self, report: RefereeReport):
        """Update comprehensive referee analytics with new report"""
        referee_file = self.get_referee_file(report.referee_email)
        
        # Load existing analytics
        existing_data = {}
        if referee_file.exists():
            try:
                async with aiofiles.open(referee_file, 'r') as f:
                    content = await f.read()
                    existing_data = json.loads(content)
            except:
                pass
        
        # Initialize structure
        if 'reports' not in existing_data:
            existing_data['reports'] = []
        if 'analytics_summary' not in existing_data:
            existing_data['analytics_summary'] = {}
        
        # Add new report
        report_entry = {
            'manuscript_id': report.manuscript_id,
            'journal': report.journal,
            'report_file': str(self.get_report_file(report.manuscript_id, report.referee_email)),
            'submission_date': report.submission_date or datetime.now().isoformat(),
            'word_count': report.word_count,
            'recommendation': report.recommendation,
            'quality_score': report.review_quality_score,
            'technical_depth': report.technical_depth,
            'constructiveness': report.constructiveness,
            'key_topics': report.key_topics
        }
        
        # Check for duplicates
        existing_manuscripts = {r['manuscript_id'] for r in existing_data['reports']}
        if report.manuscript_id not in existing_manuscripts:
            existing_data['reports'].append(report_entry)
        
        # Calculate comprehensive analytics
        await self._calculate_referee_analytics(existing_data)
        
        # Save updated analytics
        try:
            async with aiofiles.open(referee_file, 'w') as f:
                await f.write(json.dumps(existing_data, indent=2, default=str))
            
            logger.info(f"📊 Updated analytics for {report.referee_email}")
        except Exception as e:
            logger.error(f"Failed to update referee analytics: {e}")
    
    async def _calculate_referee_analytics(self, referee_data: Dict[str, Any]):
        """Calculate comprehensive referee performance analytics"""
        reports = referee_data.get('reports', [])
        
        if not reports:
            return
        
        # Basic statistics
        total_reports = len(reports)
        total_words = sum(r.get('word_count', 0) for r in reports)
        avg_words = total_words / total_reports if total_reports > 0 else 0
        
        # Quality metrics
        quality_scores = [r.get('quality_score', 0) for r in reports if r.get('quality_score')]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Recommendation patterns
        recommendations = [r.get('recommendation') for r in reports if r.get('recommendation')]
        recommendation_counts = {}
        for rec in recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Technical depth analysis
        depth_counts = {}
        for report in reports:
            depth = report.get('technical_depth', 'unknown')
            depth_counts[depth] = depth_counts.get(depth, 0) + 1
        
        # Constructiveness analysis
        constructiveness_counts = {}
        for report in reports:
            const = report.get('constructiveness', 'unknown')
            constructiveness_counts[const] = constructiveness_counts.get(const, 0) + 1
        
        # Topic expertise
        all_topics = []
        for report in reports:
            all_topics.extend(report.get('key_topics', []))
        
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Journal activity
        journal_counts = {}
        for report in reports:
            journal = report.get('journal', 'unknown')
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
        
        # Timeline analysis
        dates = [r.get('submission_date') for r in reports if r.get('submission_date')]
        dates = [d for d in dates if d]  # Remove None values
        
        career_span = {}
        if dates:
            dates.sort()
            career_span = {
                'first_review': dates[0],
                'latest_review': dates[-1],
                'active_period_days': (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])).days if len(dates) > 1 else 0
            }
        
        # Performance indicators
        performance_indicators = {
            'productivity': 'high' if total_reports > 5 else 'moderate' if total_reports > 2 else 'low',
            'review_thoroughness': 'high' if avg_words > 500 else 'moderate' if avg_words > 200 else 'low',
            'quality_consistency': 'high' if avg_quality > 70 else 'moderate' if avg_quality > 50 else 'low',
            'technical_expertise': max(depth_counts, key=depth_counts.get) if depth_counts else 'unknown',
            'review_tone': max(constructiveness_counts, key=constructiveness_counts.get) if constructiveness_counts else 'unknown'
        }
        
        # Update analytics summary
        referee_data['analytics_summary'] = {
            'last_updated': datetime.now().isoformat(),
            'total_reports': total_reports,
            'total_words_written': total_words,
            'average_words_per_review': round(avg_words, 1),
            'average_quality_score': round(avg_quality, 1),
            'recommendation_patterns': recommendation_counts,
            'technical_depth_distribution': depth_counts,
            'constructiveness_distribution': constructiveness_counts,
            'topic_expertise': dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)),
            'journal_activity': journal_counts,
            'career_timeline': career_span,
            'performance_indicators': performance_indicators,
            'referee_profile': {
                'specialization': max(topic_counts, key=topic_counts.get) if topic_counts else 'general',
                'preferred_journals': list(journal_counts.keys()),
                'review_style': performance_indicators['review_tone'],
                'expertise_level': performance_indicators['technical_expertise']
            }
        }
    
    async def get_referee_complete_profile(self, referee_email: str) -> Optional[Dict[str, Any]]:
        """Get complete referee profile including all reports and analytics"""
        referee_file = self.get_referee_file(referee_email)
        
        if not referee_file.exists():
            return None
        
        try:
            async with aiofiles.open(referee_file, 'r') as f:
                content = await f.read()
                profile = json.loads(content)
            
            # Add full report texts
            profile['full_reports'] = []
            for report_entry in profile.get('reports', []):
                report_file_path = report_entry.get('report_file')
                if report_file_path and Path(report_file_path).exists():
                    try:
                        async with aiofiles.open(report_file_path, 'r') as rf:
                            report_content = await rf.read()
                            full_report = json.loads(report_content)
                            profile['full_reports'].append(full_report)
                    except:
                        continue
            
            return profile
        except Exception as e:
            logger.error(f"Failed to load referee profile for {referee_email}: {e}")
            return None
    
    async def generate_referee_analytics_report(self, output_dir: Path) -> Dict[str, Any]:
        """Generate comprehensive referee analytics report"""
        output_dir.mkdir(exist_ok=True)
        
        # Collect all referee profiles
        all_referees = []
        referee_files = list(self.referees_dir.glob("referee_*.json"))
        
        for referee_file in referee_files:
            try:
                async with aiofiles.open(referee_file, 'r') as f:
                    content = await f.read()
                    referee_data = json.loads(content)
                    all_referees.append(referee_data)
            except:
                continue
        
        # Global analytics
        total_referees = len(all_referees)
        total_reports = sum(len(ref.get('reports', [])) for ref in all_referees)
        total_words = sum(ref.get('analytics_summary', {}).get('total_words_written', 0) for ref in all_referees)
        
        # Quality distribution
        quality_scores = []
        for referee in all_referees:
            avg_quality = referee.get('analytics_summary', {}).get('average_quality_score', 0)
            if avg_quality > 0:
                quality_scores.append(avg_quality)
        
        # Topic expertise across all referees
        global_topics = {}
        for referee in all_referees:
            topics = referee.get('analytics_summary', {}).get('topic_expertise', {})
            for topic, count in topics.items():
                global_topics[topic] = global_topics.get(topic, 0) + count
        
        # Journal activity
        global_journals = {}
        for referee in all_referees:
            journals = referee.get('analytics_summary', {}).get('journal_activity', {})
            for journal, count in journals.items():
                global_journals[journal] = global_journals.get(journal, 0) + count
        
        # Performance distribution
        performance_distribution = {}
        for referee in all_referees:
            indicators = referee.get('analytics_summary', {}).get('performance_indicators', {})
            for metric, value in indicators.items():
                if metric not in performance_distribution:
                    performance_distribution[metric] = {}
                performance_distribution[metric][value] = performance_distribution[metric].get(value, 0) + 1
        
        analytics_report = {
            'report_timestamp': datetime.now().isoformat(),
            'global_statistics': {
                'total_referees': total_referees,
                'total_reports': total_reports,
                'total_words_written': total_words,
                'average_reports_per_referee': round(total_reports / total_referees, 1) if total_referees > 0 else 0,
                'average_words_per_referee': round(total_words / total_referees, 1) if total_referees > 0 else 0
            },
            'quality_analytics': {
                'average_quality_score': round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0,
                'quality_distribution': {
                    'excellent': sum(1 for q in quality_scores if q > 80),
                    'good': sum(1 for q in quality_scores if 60 < q <= 80),
                    'moderate': sum(1 for q in quality_scores if 40 < q <= 60),
                    'poor': sum(1 for q in quality_scores if q <= 40)
                }
            },
            'expertise_landscape': dict(sorted(global_topics.items(), key=lambda x: x[1], reverse=True)),
            'journal_activity': dict(sorted(global_journals.items(), key=lambda x: x[1], reverse=True)),
            'performance_distributions': performance_distribution,
            'top_performers': []
        }
        
        # Identify top performers
        for referee in all_referees:
            summary = referee.get('analytics_summary', {})
            if (summary.get('total_reports', 0) >= 3 and 
                summary.get('average_quality_score', 0) > 70):
                
                analytics_report['top_performers'].append({
                    'referee_email': referee.get('referee_email', 'unknown'),
                    'total_reports': summary.get('total_reports', 0),
                    'quality_score': summary.get('average_quality_score', 0),
                    'specialization': summary.get('referee_profile', {}).get('specialization', 'general'),
                    'expertise_level': summary.get('referee_profile', {}).get('expertise_level', 'unknown')
                })
        
        # Sort top performers by quality score
        analytics_report['top_performers'].sort(key=lambda x: x['quality_score'], reverse=True)
        analytics_report['top_performers'] = analytics_report['top_performers'][:20]  # Top 20
        
        # Save report
        report_file = output_dir / f"referee_analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(report_file, 'w') as f:
            await f.write(json.dumps(analytics_report, indent=2, default=str))
        
        # Generate markdown summary
        await self._generate_markdown_summary(analytics_report, output_dir)
        
        logger.info(f"📊 Analytics report generated: {report_file}")
        return analytics_report
    
    async def _generate_markdown_summary(self, report: Dict[str, Any], output_dir: Path):
        """Generate markdown summary of analytics"""
        stats = report['global_statistics']
        quality = report['quality_analytics']
        
        markdown = f"""# Referee Analytics Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Global Statistics

- **Total Referees**: {stats['total_referees']}
- **Total Reports**: {stats['total_reports']}
- **Total Words Written**: {stats['total_words_written']:,}
- **Average Reports per Referee**: {stats['average_reports_per_referee']}
- **Average Words per Referee**: {stats['average_words_per_referee']:,}

## Quality Analytics

- **Average Quality Score**: {quality['average_quality_score']}/100
- **Quality Distribution**:
  - Excellent (80+): {quality['quality_distribution']['excellent']} referees
  - Good (60-80): {quality['quality_distribution']['good']} referees
  - Moderate (40-60): {quality['quality_distribution']['moderate']} referees
  - Poor (<40): {quality['quality_distribution']['poor']} referees

## Expertise Landscape

"""
        
        # Top 10 topics
        for i, (topic, count) in enumerate(list(report['expertise_landscape'].items())[:10]):
            markdown += f"{i+1}. **{topic.title()}**: {count} mentions\n"
        
        markdown += f"""

## Journal Activity

"""
        
        # Journal activity
        for journal, count in list(report['journal_activity'].items())[:10]:
            markdown += f"- **{journal}**: {count} reviews\n"
        
        markdown += f"""

## Top Performers

"""
        
        # Top performers
        for i, performer in enumerate(report['top_performers'][:10]):
            markdown += f"{i+1}. **{performer['referee_email']}**\n"
            markdown += f"   - Quality Score: {performer['quality_score']}/100\n"
            markdown += f"   - Total Reports: {performer['total_reports']}\n"
            markdown += f"   - Specialization: {performer['specialization']}\n"
            markdown += f"   - Expertise: {performer['expertise_level']}\n\n"
        
        # Save markdown
        markdown_file = output_dir / f"referee_analytics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        async with aiofiles.open(markdown_file, 'w') as f:
            await f.write(markdown)


class DemoEnhancedRefereeSystem:
    """Demo system for enhanced referee analytics with reports"""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.demo_dir = self.base_dir / "demo_enhanced_referee_analytics"
        self.demo_dir.mkdir(exist_ok=True)
        
        self.analytics = EnhancedRefereeAnalytics(self.demo_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def create_sample_reports(self) -> List[RefereeReport]:
        """Create sample referee reports for demonstration"""
        sample_reports = [
            RefereeReport(
                manuscript_id="M174160",
                journal="SIFIN",
                referee_email="prof.smith@university.edu",
                report_text="""This paper presents a novel approach to stochastic control theory with interesting applications. 

The methodology is sound and the mathematical framework is well-developed. The authors have provided rigorous proofs for the main theorems and the experimental validation supports their theoretical claims.

However, I have several suggestions for improvement:
1. The literature review could be more comprehensive, particularly regarding recent work by Johnson et al. (2024)
2. The computational complexity analysis needs more detail
3. Some notation could be clarified in Section 3.2

Overall, this is solid work that makes meaningful contributions to the field. I recommend acceptance with minor revisions to address the points above.""",
                recommendation="minor_revision",
                review_date="2025-07-10",
                submission_date="2025-07-10T14:30:00"
            ),
            
            RefereeReport(
                manuscript_id="M174160", 
                journal="SIFIN",
                referee_email="dr.jones@institute.org",
                report_text="""The paper tackles an important problem in financial mathematics. The theoretical framework appears correct, but the presentation needs significant improvement.

Major concerns:
- The paper lacks clarity in several key sections
- The experimental setup is not well described  
- Figure 2 is difficult to interpret
- The comparison with baseline methods is incomplete

Minor issues:
- Several typos throughout
- Reference formatting is inconsistent
- Some mathematical notation is non-standard

I recommend major revision to address these issues before the paper can be considered for publication.""",
                recommendation="major_revision",
                review_date="2025-07-12",
                submission_date="2025-07-12T09:15:00"
            ),
            
            RefereeReport(
                manuscript_id="M174727",
                journal="SIFIN", 
                referee_email="prof.smith@university.edu",
                report_text="""This manuscript presents interesting results on mean-variance optimization. The mathematical approach is sophisticated and the results appear novel.

Strengths:
- Strong theoretical foundation
- Novel algorithmic approach
- Comprehensive empirical evaluation
- Well-written and clear presentation

The work represents a solid contribution to the portfolio optimization literature. The authors have addressed an important gap and provided both theoretical insights and practical algorithms.

I recommend acceptance without revision.""",
                recommendation="accept",
                review_date="2025-07-11",
                submission_date="2025-07-11T16:45:00"
            ),
            
            RefereeReport(
                manuscript_id="M175988",
                journal="SIFIN",
                referee_email="researcher.wilson@lab.ac.uk", 
                report_text="""The paper addresses particle systems in mathematical finance. While the topic is relevant, the execution is problematic.

Critical issues:
- The main theorem proof contains errors in steps 3-4
- The numerical method convergence is not established
- Related work section misses key references
- Experimental results are not reproducible

This work requires substantial revision before it can be considered suitable for publication. The authors need to fix the theoretical issues and provide more rigorous empirical validation.""",
                recommendation="major_revision",
                review_date="2025-07-09",
                submission_date="2025-07-09T11:20:00"
            )
        ]
        
        return sample_reports
    
    async def run_demo(self) -> Dict[str, Any]:
        """Run comprehensive demo of enhanced referee analytics"""
        logger.info("🚀 Starting Enhanced Referee Analytics Demo")
        
        # Create sample reports
        sample_reports = await self.create_sample_reports()
        
        # Save all reports and build analytics
        for report in sample_reports:
            await self.analytics.save_referee_report(report, report.journal)
        
        logger.info(f"💾 Saved {len(sample_reports)} sample reports")
        
        # Generate comprehensive analytics report
        analytics_report = await self.analytics.generate_referee_analytics_report(self.demo_dir)
        
        # Get detailed profiles for demonstration
        referee_profiles = {}
        unique_emails = set(report.referee_email for report in sample_reports)
        
        for email in unique_emails:
            profile = await self.analytics.get_referee_complete_profile(email)
            if profile:
                referee_profiles[email] = profile
        
        demo_results = {
            'demo_session_id': self.session_id,
            'demo_timestamp': datetime.now().isoformat(),
            'sample_reports_generated': len(sample_reports),
            'unique_referees': len(unique_emails),
            'analytics_report': analytics_report,
            'referee_profiles': referee_profiles,
            'features_demonstrated': [
                'report_text_preservation',
                'quality_scoring',
                'recommendation_extraction',
                'technical_depth_analysis',
                'constructiveness_assessment',
                'topic_expertise_tracking',
                'career_analytics',
                'performance_indicators',
                'cross_manuscript_analytics'
            ]
        }
        
        # Save demo results
        results_file = self.demo_dir / f"enhanced_referee_demo_{self.session_id}.json"
        async with aiofiles.open(results_file, 'w') as f:
            await f.write(json.dumps(demo_results, indent=2, default=str))
        
        logger.info(f"📊 Demo results saved: {results_file}")
        return demo_results


async def main():
    """Run enhanced referee analytics demo"""
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize demo system
        demo = DemoEnhancedRefereeSystem()
        
        # Run demo
        results = await demo.run_demo()
        
        if results:
            analytics = results['analytics_report']
            stats = analytics['global_statistics']
            
            logger.info(f"\\n{'='*60}")
            logger.info("ENHANCED REFEREE ANALYTICS DEMO COMPLETE")
            logger.info('='*60)
            logger.info(f"📊 Reports analyzed: {stats['total_reports']}")
            logger.info(f"👥 Referees tracked: {stats['total_referees']}")  
            logger.info(f"📝 Words preserved: {stats['total_words_written']:,}")
            logger.info(f"🎯 Quality score: {analytics['quality_analytics']['average_quality_score']}/100")
            logger.info(f"🔬 Top expertise: {list(analytics['expertise_landscape'].keys())[0] if analytics['expertise_landscape'] else 'N/A'}")
            logger.info(f"🏆 Top performers: {len(analytics['top_performers'])}")
            logger.info(f"📁 Data location: {demo.demo_dir}")
            
            return True
        else:
            logger.error("❌ Demo failed")
            return False
    
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)