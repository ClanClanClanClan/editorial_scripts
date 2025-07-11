"""
Comprehensive review quality analysis framework
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import numpy as np
import sqlite3
from pathlib import Path
import re
from dataclasses import dataclass
import spacy
from textblob import TextBlob

logger = logging.getLogger(__name__)


@dataclass
class ContentMetrics:
    """Metrics for review content analysis"""
    word_count: int
    unique_concepts: int
    technical_depth: float
    constructiveness: float
    specificity: float
    citation_count: int
    equation_count: int
    
    def get_thoroughness_score(self) -> float:
        """Calculate overall thoroughness score"""
        # Normalize word count (2000 words = 1.0)
        word_score = min(1.0, self.word_count / 2000)
        
        # Normalize concepts (20 unique concepts = 1.0)
        concept_score = min(1.0, self.unique_concepts / 20)
        
        # Weight the components
        return (word_score * 0.4 + 
                concept_score * 0.3 + 
                self.technical_depth * 0.2 + 
                self.specificity * 0.1)


@dataclass
class StructureMetrics:
    """Metrics for review structure analysis"""
    has_summary: bool
    has_major_concerns: bool
    has_minor_concerns: bool
    has_recommendations: bool
    organization_score: float
    section_count: int
    bullet_points: int
    numbered_items: int
    
    def get_structure_score(self) -> float:
        """Calculate overall structure score"""
        base_score = 0.0
        
        # Essential components
        if self.has_summary:
            base_score += 0.25
        if self.has_major_concerns:
            base_score += 0.25
        if self.has_minor_concerns:
            base_score += 0.15
        if self.has_recommendations:
            base_score += 0.20
        
        # Organization bonus
        base_score += self.organization_score * 0.15
        
        return min(1.0, base_score)


@dataclass
class ImpactMetrics:
    """Metrics for review impact analysis"""
    alignment_with_decision: float
    influence_on_revision: float
    author_feedback_score: float
    editor_agreement: float
    actionable_items: int
    
    def get_impact_score(self) -> float:
        """Calculate overall impact score"""
        return (self.alignment_with_decision * 0.3 +
                self.influence_on_revision * 0.25 +
                self.author_feedback_score * 0.2 +
                self.editor_agreement * 0.25)


@dataclass
class QualityAnalysis:
    """Complete quality analysis results"""
    overall_score: float
    content_metrics: ContentMetrics
    structure_metrics: StructureMetrics
    impact_metrics: ImpactMetrics
    improvement_suggestions: List[str]
    sentiment_analysis: Dict
    readability_score: float


class ReviewQualityAnalyzer:
    """Deep analysis of review report quality"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        
        # Load spaCy model for NLP analysis
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def analyze_review_quality(self, review_id: str) -> QualityAnalysis:
        """Perform comprehensive quality analysis on a review"""
        # Get review data
        review_data = self._get_review_data(review_id)
        if not review_data:
            raise ValueError(f"Review {review_id} not found")
        
        review_text = review_data['review_text'] or ""
        
        # Analyze different aspects
        content_metrics = self._analyze_content(review_text)
        structure_metrics = self._analyze_structure(review_text)
        impact_metrics = self._analyze_impact(review_data)
        sentiment = self._analyze_sentiment(review_text)
        readability = self._calculate_readability(review_text)
        
        # Calculate overall score
        overall_score = self._calculate_overall_quality(
            content_metrics, structure_metrics, impact_metrics
        )
        
        # Generate improvement suggestions
        suggestions = self._generate_quality_improvements(
            content_metrics, structure_metrics, sentiment
        )
        
        return QualityAnalysis(
            overall_score=overall_score,
            content_metrics=content_metrics,
            structure_metrics=structure_metrics,
            impact_metrics=impact_metrics,
            improvement_suggestions=suggestions,
            sentiment_analysis=sentiment,
            readability_score=readability
        )
    
    def _analyze_content(self, review_text: str) -> ContentMetrics:
        """Analyze review content depth and quality"""
        # Basic metrics
        words = review_text.split()
        word_count = len(words)
        
        # Extract unique concepts using NLP
        unique_concepts = self._extract_unique_concepts(review_text)
        
        # Assess technical depth
        technical_depth = self._assess_technical_depth(review_text)
        
        # Measure constructiveness
        constructiveness = self._measure_constructiveness(review_text)
        
        # Measure specificity
        specificity = self._measure_specificity(review_text)
        
        # Count citations and equations
        citation_count = len(re.findall(r'\[\d+\]|\(\w+,?\s*\d{4}\)', review_text))
        equation_count = len(re.findall(r'\$.*?\$|\\\[.*?\\\]', review_text))
        
        return ContentMetrics(
            word_count=word_count,
            unique_concepts=unique_concepts,
            technical_depth=technical_depth,
            constructiveness=constructiveness,
            specificity=specificity,
            citation_count=citation_count,
            equation_count=equation_count
        )
    
    def _analyze_structure(self, review_text: str) -> StructureMetrics:
        """Analyze review structure and organization"""
        # Check for key sections
        has_summary = bool(re.search(r'(summary|overview|general comments?):', 
                                    review_text, re.IGNORECASE))
        has_major_concerns = bool(re.search(r'(major|significant|important) (concerns?|issues?|comments?)', 
                                          review_text, re.IGNORECASE))
        has_minor_concerns = bool(re.search(r'(minor|small|detailed) (concerns?|issues?|comments?)', 
                                          review_text, re.IGNORECASE))
        has_recommendations = bool(re.search(r'(recommend|suggest|propose)', 
                                           review_text, re.IGNORECASE))
        
        # Count structural elements
        section_count = len(re.findall(r'\n\s*\d+\.|^\d+\.|\n\s*[A-Z][^.!?]*:', review_text, re.MULTILINE))
        bullet_points = len(re.findall(r'\n\s*[-*•]', review_text))
        numbered_items = len(re.findall(r'\n\s*\d+[).]', review_text))
        
        # Assess organization
        organization_score = self._assess_organization(review_text)
        
        return StructureMetrics(
            has_summary=has_summary,
            has_major_concerns=has_major_concerns,
            has_minor_concerns=has_minor_concerns,
            has_recommendations=has_recommendations,
            organization_score=organization_score,
            section_count=section_count,
            bullet_points=bullet_points,
            numbered_items=numbered_items
        )
    
    def _analyze_impact(self, review_data: Dict) -> ImpactMetrics:
        """Analyze the impact and effectiveness of the review"""
        # Check alignment with final decision
        alignment = self._check_decision_alignment(review_data)
        
        # Measure influence on revision
        influence = self._measure_revision_influence(review_data)
        
        # Get author feedback (if available)
        author_feedback = self._get_author_feedback_score(review_data)
        
        # Check editor agreement
        editor_agreement = self._check_editor_agreement(review_data)
        
        # Count actionable items
        actionable_items = self._count_actionable_items(review_data['review_text'] or "")
        
        return ImpactMetrics(
            alignment_with_decision=alignment,
            influence_on_revision=influence,
            author_feedback_score=author_feedback,
            editor_agreement=editor_agreement,
            actionable_items=actionable_items
        )
    
    def _extract_unique_concepts(self, text: str) -> int:
        """Extract unique technical concepts from review"""
        if not self.nlp:
            # Fallback to simple word analysis
            technical_words = set()
            for word in text.split():
                if len(word) > 6 and word.isalpha():
                    technical_words.add(word.lower())
            return len(technical_words)
        
        # Use NLP to extract noun phrases and entities
        doc = self.nlp(text[:1000000])  # Limit text length for processing
        
        concepts = set()
        
        # Extract noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Limit to reasonable length
                concepts.add(chunk.text.lower())
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'LAW', 'LANGUAGE']:
                concepts.add(ent.text.lower())
        
        return len(concepts)
    
    def _assess_technical_depth(self, text: str) -> float:
        """Assess the technical depth of the review"""
        indicators = {
            'methodology': len(re.findall(r'(method|approach|algorithm|technique|procedure)', text, re.IGNORECASE)),
            'analysis': len(re.findall(r'(analysis|analyze|evaluate|assess|examine)', text, re.IGNORECASE)),
            'theory': len(re.findall(r'(theorem|proof|lemma|proposition|hypothesis)', text, re.IGNORECASE)),
            'technical_terms': len(re.findall(r'(optimization|convergence|complexity|efficiency|accuracy)', text, re.IGNORECASE)),
            'quantitative': len(re.findall(r'\d+\.?\d*%?|\b(increase|decrease|improve|reduce).*\d+', text))
        }
        
        # Normalize by text length (per 1000 words)
        word_count = len(text.split())
        normalization = 1000 / max(word_count, 100)
        
        # Calculate weighted score
        depth_score = sum(indicators.values()) * normalization / 50  # Normalize to 0-1
        
        return min(1.0, depth_score)
    
    def _measure_constructiveness(self, text: str) -> float:
        """Measure how constructive the feedback is"""
        # Positive indicators
        positive_patterns = [
            r'(suggest|recommend|could|should|might|consider)',
            r'(improve|enhance|strengthen|clarify|expand)',
            r'(interesting|valuable|important|significant|novel)',
            r'(well-written|clear|good|excellent|strong)'
        ]
        
        # Negative indicators (unconstructive criticism)
        negative_patterns = [
            r'(wrong|bad|poor|terrible|awful)',
            r'(useless|pointless|waste|garbage)',
            r'(reject|unacceptable)(?! unless)',  # Allow "reject unless..."
        ]
        
        positive_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                           for pattern in positive_patterns)
        negative_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                           for pattern in negative_patterns)
        
        # Calculate ratio
        total = positive_count + negative_count
        if total == 0:
            return 0.5  # Neutral
        
        constructiveness = positive_count / total
        
        # Boost if suggestions are specific
        if re.search(r'(specifically|for example|such as|e\.g\.|i\.e\.)', text, re.IGNORECASE):
            constructiveness = min(1.0, constructiveness * 1.2)
        
        return constructiveness
    
    def _measure_specificity(self, text: str) -> float:
        """Measure how specific the feedback is"""
        specificity_indicators = [
            r'(page \d+|section \d+|line \d+|paragraph \d+)',
            r'(equation \d+|figure \d+|table \d+|theorem \d+)',
            r'(specifically|in particular|for example|for instance)',
            r'"[^"]{10,}"',  # Quoted text
            r'(first|second|third|finally|lastly)',
        ]
        
        indicator_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                            for pattern in specificity_indicators)
        
        # Normalize by text length
        word_count = len(text.split())
        specificity = indicator_count / max(word_count / 100, 1)
        
        return min(1.0, specificity)
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment and tone of the review"""
        blob = TextBlob(text)
        
        # Overall sentiment
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Analyze by sentences
        sentences = blob.sentences[:50]  # Limit for performance
        positive_sentences = sum(1 for s in sentences if s.sentiment.polarity > 0.1)
        negative_sentences = sum(1 for s in sentences if s.sentiment.polarity < -0.1)
        neutral_sentences = len(sentences) - positive_sentences - negative_sentences
        
        return {
            'overall_polarity': polarity,
            'overall_subjectivity': subjectivity,
            'tone': self._classify_tone(polarity, subjectivity),
            'sentence_breakdown': {
                'positive': positive_sentences,
                'negative': negative_sentences,
                'neutral': neutral_sentences
            }
        }
    
    def _classify_tone(self, polarity: float, subjectivity: float) -> str:
        """Classify the overall tone of the review"""
        if polarity > 0.3:
            if subjectivity > 0.5:
                return "encouraging"
            else:
                return "positive"
        elif polarity < -0.3:
            if subjectivity > 0.5:
                return "critical"
            else:
                return "negative"
        else:
            if subjectivity > 0.6:
                return "subjective_neutral"
            else:
                return "objective_neutral"
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate readability score (Flesch Reading Ease)"""
        sentences = text.split('.')
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        # Count syllables (simplified)
        syllable_count = 0
        for word in words:
            syllable_count += max(1, len(re.findall(r'[aeiouAEIOU]', word)))
        
        # Flesch Reading Ease formula
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllable_count / len(words)
        
        flesch_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        
        # Normalize to 0-1 (30-80 is typical range for academic text)
        normalized = (flesch_score - 30) / 50
        return max(0, min(1, normalized))
    
    def _calculate_overall_quality(self, content: ContentMetrics, 
                                 structure: StructureMetrics, 
                                 impact: ImpactMetrics) -> float:
        """Calculate weighted overall quality score"""
        weights = {
            'content': 0.40,
            'structure': 0.25,
            'impact': 0.35
        }
        
        content_score = content.get_thoroughness_score()
        structure_score = structure.get_structure_score()
        impact_score = impact.get_impact_score()
        
        overall = (content_score * weights['content'] +
                  structure_score * weights['structure'] +
                  impact_score * weights['impact'])
        
        return overall * 10  # Convert to 0-10 scale
    
    def _generate_quality_improvements(self, content: ContentMetrics, 
                                     structure: StructureMetrics,
                                     sentiment: Dict) -> List[str]:
        """Generate specific improvement suggestions"""
        suggestions = []
        
        # Content suggestions
        if content.word_count < 500:
            suggestions.append("Provide more detailed feedback - aim for at least 500 words")
        
        if content.unique_concepts < 10:
            suggestions.append("Address more technical aspects of the paper")
        
        if content.constructiveness < 0.6:
            suggestions.append("Balance criticism with more constructive suggestions")
        
        if content.specificity < 0.3:
            suggestions.append("Reference specific sections, equations, or figures when providing feedback")
        
        # Structure suggestions
        if not structure.has_summary:
            suggestions.append("Include a brief summary of your overall assessment")
        
        if not structure.has_major_concerns:
            suggestions.append("Clearly separate major and minor concerns")
        
        if structure.organization_score < 0.6:
            suggestions.append("Improve organization with clear sections and numbering")
        
        # Tone suggestions
        if sentiment['overall_polarity'] < -0.5:
            suggestions.append("Consider a more balanced tone - acknowledge paper strengths")
        
        if sentiment['overall_subjectivity'] > 0.8:
            suggestions.append("Provide more objective, evidence-based feedback")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _get_review_data(self, review_id: str) -> Optional[Dict]:
        """Get review data from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rh.*,
                    m.decision as final_decision,
                    m.revision_count
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE rh.id = ?
            """, (review_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def _assess_organization(self, text: str) -> float:
        """Assess how well organized the review is"""
        # Check for logical flow indicators
        flow_indicators = [
            r'(first|second|third|finally)',
            r'(however|moreover|furthermore|additionally)',
            r'(in conclusion|to summarize|overall)',
            r'\n\s*\d+\.',  # Numbered sections
            r'\n\s*[A-Z][^.!?]*:',  # Section headers
        ]
        
        indicator_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                            for pattern in flow_indicators)
        
        # Check paragraph structure
        paragraphs = text.split('\n\n')
        avg_paragraph_length = np.mean([len(p.split()) for p in paragraphs if p.strip()])
        
        # Good organization has moderate paragraph length (50-150 words)
        paragraph_score = 1.0 if 50 <= avg_paragraph_length <= 150 else 0.5
        
        # Combine scores
        organization = min(1.0, (indicator_count / 10) * 0.6 + paragraph_score * 0.4)
        
        return organization
    
    def _check_decision_alignment(self, review_data: Dict) -> float:
        """Check if review recommendation aligns with final decision"""
        review_rec = review_data.get('recommendation', '').lower()
        final_decision = review_data.get('final_decision', '').lower()
        
        if not review_rec or not final_decision:
            return 0.5  # Unknown
        
        # Map recommendations to decisions
        if 'accept' in review_rec and 'accept' in final_decision:
            return 1.0
        elif 'reject' in review_rec and 'reject' in final_decision:
            return 1.0
        elif 'minor' in review_rec and 'minor' in final_decision:
            return 1.0
        elif 'major' in review_rec and 'major' in final_decision:
            return 1.0
        else:
            return 0.3  # Misalignment
    
    def _measure_revision_influence(self, review_data: Dict) -> float:
        """Measure how much the review influenced revisions"""
        # Simplified - would need more sophisticated tracking
        revision_count = review_data.get('revision_count', 0)
        
        if revision_count > 0:
            return 0.8  # Had influence
        else:
            return 0.5  # Unknown influence
    
    def _get_author_feedback_score(self, review_data: Dict) -> float:
        """Get author feedback score if available"""
        # This would be collected through a feedback system
        # For now, return default
        return 0.7
    
    def _check_editor_agreement(self, review_data: Dict) -> float:
        """Check editor agreement with review"""
        # This would be tracked in the system
        # For now, return default based on decision alignment
        return self._check_decision_alignment(review_data)
    
    def _count_actionable_items(self, text: str) -> int:
        """Count specific actionable items in review"""
        action_patterns = [
            r'(should|must|need to|have to|suggest|recommend)',
            r'(please|kindly)?\s*(add|remove|revise|clarify|expand|explain)',
            r'(\d+\.\s*[A-Z].*?(should|must|need))',
        ]
        
        actionable_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                             for pattern in action_patterns)
        
        return actionable_count
    
    def analyze_referee_quality_trends(self, referee_id: str, limit: int = 20) -> Dict:
        """Analyze quality trends for a referee's reviews"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get recent reviews
            cursor.execute("""
                SELECT id, submitted_date, quality_score, report_length
                FROM review_history
                WHERE referee_id = ?
                AND submitted_date IS NOT NULL
                ORDER BY submitted_date DESC
                LIMIT ?
            """, (referee_id, limit))
            
            reviews = cursor.fetchall()
        
        if not reviews:
            return {'error': 'No reviews found for analysis'}
        
        # Analyze trends
        quality_scores = [r[2] for r in reviews if r[2] is not None]
        report_lengths = [r[3] for r in reviews if r[3] is not None]
        
        # Calculate trend
        if len(quality_scores) >= 2:
            x = np.arange(len(quality_scores))
            quality_trend = np.polyfit(x, quality_scores, 1)[0]
        else:
            quality_trend = 0
        
        return {
            'review_count': len(reviews),
            'average_quality': np.mean(quality_scores) if quality_scores else 0,
            'quality_trend': 'improving' if quality_trend > 0.1 else 'declining' if quality_trend < -0.1 else 'stable',
            'average_length': np.mean(report_lengths) if report_lengths else 0,
            'consistency': np.std(quality_scores) if len(quality_scores) > 1 else 0,
            'recent_reviews': [
                {
                    'id': r[0],
                    'date': r[1],
                    'quality_score': r[2],
                    'length': r[3]
                }
                for r in reviews[:5]
            ]
        }