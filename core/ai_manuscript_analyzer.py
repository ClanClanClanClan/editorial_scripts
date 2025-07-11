"""
AI-powered manuscript analysis system for desk rejection and referee recommendations.
This module integrates with OpenAI API to provide intelligent paper analysis.
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import re
import PyPDF2
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ManuscriptMetadata:
    """Structured manuscript metadata"""
    title: str
    abstract: str = ""
    keywords: List[str] = None
    research_area: str = ""
    methodology: str = ""
    complexity_score: float = 0.0
    novelty_score: float = 0.0
    quality_indicators: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.quality_indicators is None:
            self.quality_indicators = {}


@dataclass
class RefereeRecommendation:
    """Referee recommendation with scoring"""
    name: str
    expertise_match: float
    availability_score: float
    quality_score: float
    workload_score: float
    overall_score: float
    rationale: str
    contact_info: Dict[str, str] = None
    
    def __post_init__(self):
        if self.contact_info is None:
            self.contact_info = {}


@dataclass
class DeskRejectionAnalysis:
    """Desk rejection analysis results"""
    recommendation: str  # "accept", "reject", "uncertain"
    confidence: float
    rejection_reasons: List[str]
    quality_issues: List[str]
    scope_issues: List[str]
    technical_issues: List[str]
    recommendation_summary: str


class AIManuscriptAnalyzer:
    """AI-powered manuscript analyzer for editorial decisions"""
    
    def __init__(self, openai_api_key: str = None, cache_enabled: bool = True):
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.cache_enabled = cache_enabled
        self.cache_dir = Path("ai_analysis_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Analysis settings
        self.desk_rejection_threshold = 0.3  # Below this confidence = likely reject
        self.acceptance_threshold = 0.7     # Above this confidence = likely accept
        
        # Initialize OpenAI client if available
        self.openai_available = False
        if self.api_key:
            try:
                import openai
                self.openai = openai
                self.openai.api_key = self.api_key
                self.openai_available = True
                logger.info("✅ OpenAI API initialized successfully")
            except ImportError:
                logger.warning("⚠️ OpenAI package not installed")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI initialization failed: {e}")
    
    def extract_pdf_content(self, pdf_path: str) -> Dict[str, str]:
        """Extract text content from PDF"""
        content = {
            'title': '',
            'abstract': '',
            'full_text': '',
            'references': '',
            'error': None
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {e}")
                
                content['full_text'] = full_text
                
                # Try to extract title (usually in first few lines)
                lines = full_text.split('\n')[:20]
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:  # Reasonable title length
                        content['title'] = line
                        break
                
                # Try to extract abstract
                abstract_match = re.search(r'abstract[\s\n]+(.*?)(?=\n\s*(?:keywords|introduction|1\.|background))', 
                                         full_text.lower(), re.DOTALL | re.IGNORECASE)
                if abstract_match:
                    content['abstract'] = abstract_match.group(1).strip()
                
                logger.info(f"✅ PDF content extracted: {len(full_text)} characters")
                
        except Exception as e:
            content['error'] = str(e)
            logger.error(f"❌ PDF extraction failed: {e}")
        
        return content
    
    def analyze_manuscript_for_desk_rejection(self, manuscript_data: Dict, pdf_content: Dict = None) -> DeskRejectionAnalysis:
        """Analyze manuscript for desk rejection decision"""
        
        # Generate cache key
        cache_key = self._generate_cache_key('desk_rejection', manuscript_data, pdf_content)
        
        # Check cache first
        if self.cache_enabled:
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                logger.info("📋 Using cached desk rejection analysis")
                return DeskRejectionAnalysis(**cached_result)
        
        try:
            if self.openai_available and pdf_content:
                analysis = self._openai_desk_rejection_analysis(manuscript_data, pdf_content)
            else:
                analysis = self._fallback_desk_rejection_analysis(manuscript_data, pdf_content)
            
            # Save to cache
            if self.cache_enabled:
                self._save_to_cache(cache_key, asdict(analysis))
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Desk rejection analysis failed: {e}")
            return self._fallback_desk_rejection_analysis(manuscript_data, pdf_content)
    
    def _openai_desk_rejection_analysis(self, manuscript_data: Dict, pdf_content: Dict) -> DeskRejectionAnalysis:
        """OpenAI-powered desk rejection analysis"""
        
        title = manuscript_data.get('Title', pdf_content.get('title', 'Unknown'))
        abstract = pdf_content.get('abstract', '')
        full_text_sample = pdf_content.get('full_text', '')[:3000]  # First 3000 chars
        
        prompt = f"""
        As an expert academic editor, analyze this manuscript for potential desk rejection.
        
        Title: {title}
        
        Abstract: {abstract}
        
        Text Sample: {full_text_sample}
        
        Evaluate the manuscript on these criteria:
        1. Scope fit for a mathematics/applied mathematics journal
        2. Technical quality and rigor
        3. Novelty and significance
        4. Writing clarity and presentation
        5. Completeness and methodology
        
        Provide your analysis in JSON format with:
        - recommendation: "accept", "reject", or "uncertain"
        - confidence: float between 0 and 1
        - rejection_reasons: list of specific reasons if recommending rejection
        - quality_issues: list of quality concerns
        - scope_issues: list of scope/fit concerns  
        - technical_issues: list of technical problems
        - recommendation_summary: brief summary of recommendation
        
        Be thorough but concise. Focus on actionable feedback.
        """
        
        try:
            response = self.openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert academic editor for mathematics journals with 20+ years of experience."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return DeskRejectionAnalysis(
                recommendation=result.get('recommendation', 'uncertain'),
                confidence=float(result.get('confidence', 0.5)),
                rejection_reasons=result.get('rejection_reasons', []),
                quality_issues=result.get('quality_issues', []),
                scope_issues=result.get('scope_issues', []),
                technical_issues=result.get('technical_issues', []),
                recommendation_summary=result.get('recommendation_summary', 'Analysis completed')
            )
            
        except Exception as e:
            logger.error(f"OpenAI desk rejection analysis failed: {e}")
            raise
    
    def _fallback_desk_rejection_analysis(self, manuscript_data: Dict, pdf_content: Dict) -> DeskRejectionAnalysis:
        """Fallback analysis when OpenAI is not available"""
        
        title = manuscript_data.get('Title', pdf_content.get('title', 'Unknown') if pdf_content else 'Unknown')
        abstract = pdf_content.get('abstract', '') if pdf_content else ''
        
        # Simple heuristic-based analysis
        issues = []
        quality_issues = []
        scope_issues = []
        technical_issues = []
        
        # Basic quality checks
        if len(title) < 10:
            quality_issues.append("Title appears too short")
        
        if len(abstract) < 100:
            quality_issues.append("Abstract appears too short or missing")
        
        # Simple keyword-based scope checking
        math_keywords = ['algorithm', 'optimization', 'theorem', 'proof', 'analysis', 'method', 'model']
        title_lower = title.lower()
        abstract_lower = abstract.lower()
        
        math_score = sum(1 for keyword in math_keywords if keyword in title_lower or keyword in abstract_lower)
        
        if math_score == 0:
            scope_issues.append("Limited mathematical content detected")
        
        # Determine recommendation
        issue_count = len(quality_issues) + len(scope_issues) + len(technical_issues)
        
        if issue_count == 0:
            recommendation = "accept"
            confidence = 0.7
        elif issue_count <= 2:
            recommendation = "uncertain"
            confidence = 0.5
        else:
            recommendation = "reject"
            confidence = 0.8
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=confidence,
            rejection_reasons=quality_issues + scope_issues + technical_issues,
            quality_issues=quality_issues,
            scope_issues=scope_issues,
            technical_issues=technical_issues,
            recommendation_summary=f"Heuristic analysis found {issue_count} potential issues"
        )
    
    def recommend_referees(self, manuscript_data: Dict, pdf_content: Dict = None, num_recommendations: int = 5) -> List[RefereeRecommendation]:
        """Generate referee recommendations for a manuscript"""
        
        # Generate cache key
        cache_key = self._generate_cache_key('referee_recommendations', manuscript_data, pdf_content)
        
        # Check cache first
        if self.cache_enabled:
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                logger.info("📋 Using cached referee recommendations")
                return [RefereeRecommendation(**rec) for rec in cached_result]
        
        try:
            if self.openai_available and pdf_content:
                recommendations = self._openai_referee_recommendations(manuscript_data, pdf_content, num_recommendations)
            else:
                recommendations = self._fallback_referee_recommendations(manuscript_data, pdf_content, num_recommendations)
            
            # Save to cache
            if self.cache_enabled:
                self._save_to_cache(cache_key, [asdict(rec) for rec in recommendations])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Referee recommendation failed: {e}")
            return self._fallback_referee_recommendations(manuscript_data, pdf_content, num_recommendations)
    
    def _openai_referee_recommendations(self, manuscript_data: Dict, pdf_content: Dict, num_recommendations: int) -> List[RefereeRecommendation]:
        """OpenAI-powered referee recommendations"""
        
        title = manuscript_data.get('Title', pdf_content.get('title', 'Unknown'))
        abstract = pdf_content.get('abstract', '')
        
        prompt = f"""
        As an expert academic editor, recommend {num_recommendations} suitable referees for this manuscript.
        
        Title: {title}
        Abstract: {abstract}
        
        For each recommended referee, provide:
        - name: A realistic academic name (can be generic like "Expert in [Area]")
        - expertise_match: How well their expertise matches (0.0-1.0)
        - availability_score: Estimated availability (0.0-1.0, based on typical academic workload)
        - quality_score: Expected review quality (0.0-1.0)
        - workload_score: Current workload consideration (0.0-1.0, higher = less overloaded)
        - overall_score: Combined score (0.0-1.0)
        - rationale: Brief explanation for the recommendation
        
        Return as JSON array of referee objects.
        Focus on diversity of expertise while maintaining relevance.
        """
        
        try:
            response = self.openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert academic editor with extensive knowledge of researchers in mathematics and applied mathematics."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.4
            )
            
            result = json.loads(response.choices[0].message.content)
            
            recommendations = []
            for rec_data in result:
                recommendations.append(RefereeRecommendation(
                    name=rec_data.get('name', 'Expert Reviewer'),
                    expertise_match=float(rec_data.get('expertise_match', 0.7)),
                    availability_score=float(rec_data.get('availability_score', 0.6)),
                    quality_score=float(rec_data.get('quality_score', 0.8)),
                    workload_score=float(rec_data.get('workload_score', 0.5)),
                    overall_score=float(rec_data.get('overall_score', 0.6)),
                    rationale=rec_data.get('rationale', 'Suitable expertise for this research area')
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"OpenAI referee recommendations failed: {e}")
            raise
    
    def _fallback_referee_recommendations(self, manuscript_data: Dict, pdf_content: Dict, num_recommendations: int) -> List[RefereeRecommendation]:
        """Fallback referee recommendations when OpenAI is not available"""
        
        title = manuscript_data.get('Title', '')
        
        # Simple keyword-based recommendations
        math_areas = {
            'optimization': 'Optimization Theory',
            'algorithm': 'Computational Mathematics', 
            'numerical': 'Numerical Analysis',
            'stochastic': 'Stochastic Processes',
            'differential': 'Differential Equations',
            'topology': 'Topology',
            'algebra': 'Algebra',
            'analysis': 'Mathematical Analysis'
        }
        
        detected_areas = []
        title_lower = title.lower()
        
        for keyword, area in math_areas.items():
            if keyword in title_lower:
                detected_areas.append(area)
        
        if not detected_areas:
            detected_areas = ['General Mathematics']
        
        recommendations = []
        for i in range(num_recommendations):
            area = detected_areas[i % len(detected_areas)]
            
            recommendations.append(RefereeRecommendation(
                name=f"Expert in {area} {i+1}",
                expertise_match=0.7 - i * 0.05,  # Decreasing match score
                availability_score=0.6,
                quality_score=0.8,
                workload_score=0.5,
                overall_score=0.6 - i * 0.05,
                rationale=f"Specializes in {area}, relevant to manuscript topic",
                contact_info={'email': f'expert{i+1}@university.edu'}
            ))
        
        return recommendations
    
    def analyze_manuscript_comprehensively(self, manuscript_data: Dict, pdf_path: str = None) -> Dict[str, Any]:
        """Perform comprehensive manuscript analysis"""
        
        analysis_result = {
            'manuscript_id': manuscript_data.get('Manuscript #', 'Unknown'),
            'title': manuscript_data.get('Title', 'Unknown'),
            'analysis_timestamp': datetime.now().isoformat(),
            'pdf_analysis': None,
            'desk_rejection_analysis': None,
            'referee_recommendations': [],
            'ai_enabled': self.openai_available,
            'analysis_confidence': 0.0
        }
        
        try:
            # Extract PDF content if available
            pdf_content = None
            if pdf_path and Path(pdf_path).exists():
                logger.info(f"📄 Extracting content from PDF: {pdf_path}")
                pdf_content = self.extract_pdf_content(pdf_path)
                analysis_result['pdf_analysis'] = pdf_content
            
            # Perform desk rejection analysis
            logger.info("🔍 Performing desk rejection analysis...")
            desk_analysis = self.analyze_manuscript_for_desk_rejection(manuscript_data, pdf_content)
            analysis_result['desk_rejection_analysis'] = asdict(desk_analysis)
            
            # Generate referee recommendations if not likely to be rejected
            if desk_analysis.recommendation in ['accept', 'uncertain']:
                logger.info("👥 Generating referee recommendations...")
                referee_recs = self.recommend_referees(manuscript_data, pdf_content)
                analysis_result['referee_recommendations'] = [asdict(rec) for rec in referee_recs]
            
            # Calculate overall confidence
            confidence_factors = [desk_analysis.confidence]
            if analysis_result['referee_recommendations']:
                avg_referee_confidence = sum(rec['overall_score'] for rec in analysis_result['referee_recommendations']) / len(analysis_result['referee_recommendations'])
                confidence_factors.append(avg_referee_confidence)
            
            analysis_result['analysis_confidence'] = sum(confidence_factors) / len(confidence_factors)
            
            logger.info(f"✅ Comprehensive analysis completed (confidence: {analysis_result['analysis_confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis failed: {e}")
            analysis_result['error'] = str(e)
        
        return analysis_result
    
    def _generate_cache_key(self, analysis_type: str, manuscript_data: Dict, pdf_content: Dict = None) -> str:
        """Generate cache key for analysis results"""
        key_data = {
            'type': analysis_type,
            'title': manuscript_data.get('Title', ''),
            'manuscript_id': manuscript_data.get('Manuscript #', ''),
        }
        
        if pdf_content:
            key_data['pdf_hash'] = hashlib.md5(pdf_content.get('full_text', '').encode()).hexdigest()[:8]
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load analysis results from cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still fresh (24 hours)
                cached_time = datetime.fromisoformat(cached_data['timestamp'])
                if (datetime.now() - cached_time).total_seconds() < 86400:
                    return cached_data['result']
        except Exception as e:
            logger.debug(f"Cache load error: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: Any):
        """Save analysis results to cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'result': result
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Cache save error: {e}")


def demo_ai_analysis():
    """Demonstrate the AI manuscript analyzer"""
    print("🤖 AI Manuscript Analyzer Demo")
    print("=" * 40)
    
    # Initialize analyzer
    analyzer = AIManuscriptAnalyzer()
    
    # Sample manuscript data
    sample_manuscript = {
        'Manuscript #': 'DEMO-2024-001',
        'Title': 'A Novel Optimization Algorithm for Large-Scale Mathematical Programming',
        'Current Stage': 'Awaiting Referee Assignment',
        'Contact Author': 'Dr. Sample Researcher',
        'Submitted': '2024-01-01'
    }
    
    print(f"📄 Analyzing manuscript: {sample_manuscript['Title']}")
    
    try:
        # Perform comprehensive analysis
        analysis = analyzer.analyze_manuscript_comprehensively(sample_manuscript)
        
        print(f"\n🔍 Desk Rejection Analysis:")
        desk_analysis = analysis.get('desk_rejection_analysis', {})
        print(f"  Recommendation: {desk_analysis.get('recommendation', 'Unknown')}")
        print(f"  Confidence: {desk_analysis.get('confidence', 0):.2f}")
        print(f"  Summary: {desk_analysis.get('recommendation_summary', 'No summary')}")
        
        print(f"\n👥 Referee Recommendations:")
        referees = analysis.get('referee_recommendations', [])
        for i, referee in enumerate(referees[:3], 1):
            print(f"  {i}. {referee.get('name', 'Unknown')} (Score: {referee.get('overall_score', 0):.2f})")
            print(f"     Rationale: {referee.get('rationale', 'No rationale')}")
        
        print(f"\n📊 Overall Analysis Confidence: {analysis.get('analysis_confidence', 0):.2f}")
        print(f"🤖 AI Enabled: {analysis.get('ai_enabled', False)}")
        
        print("\n✅ AI analysis demo completed!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_ai_analysis()