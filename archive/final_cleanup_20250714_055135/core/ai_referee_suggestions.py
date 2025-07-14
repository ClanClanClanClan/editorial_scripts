"""
AI-powered referee suggestion system for all journals.
This module provides a generic AI integration that can be used by any journal
to analyze PDFs and generate referee recommendations.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

class AIRefereeAnalyzer:
    """
    Generic AI-powered referee suggestion system for all journals.
    Can be used by any journal to analyze manuscripts and suggest referees.
    """
    
    def __init__(self, journal_name: str, debug: bool = False):
        self.journal_name = journal_name
        self.debug = debug
        self.logger = logging.getLogger(f"[{journal_name}] AIRefereeAnalyzer")
        
    def analyze_and_suggest(self, pdf_path: str, manuscript: Dict) -> Dict:
        """
        Main entry point for AI analysis and referee suggestions.
        
        Args:
            pdf_path: Path to the downloaded PDF
            manuscript: Manuscript data dictionary
            
        Returns:
            Dictionary with analysis results and referee suggestions
        """
        try:
            # Extract text content from PDF
            pdf_content = self._extract_pdf_content(pdf_path)
            if not pdf_content:
                return self._fallback_suggestions(manuscript, "Could not extract PDF content")
            
            # Analyze content with AI
            analysis_results = self._analyze_paper_content(pdf_content, manuscript)
            
            # Get referee suggestions based on analysis
            referee_suggestions = self._get_referee_recommendations(analysis_results)
            
            # Generate final AI suggestions structure
            suggestions = {
                'status': 'completed',
                'journal': self.journal_name,
                'pdf_path': pdf_path,
                'manuscript_id': manuscript.get('Manuscript #', ''),
                'title': manuscript.get('Title', ''),
                'content_analysis': analysis_results,
                'suggestions': referee_suggestions,
                'generated_at': time.time()
            }
            
            if self.debug:
                self.logger.info(f"AI suggestions generated for {manuscript.get('Manuscript #', '')}: {len(referee_suggestions)} recommendations")
            
            return suggestions
            
        except Exception as e:
            if self.debug:
                self.logger.error(f"Error generating AI suggestions: {e}")
            return self._fallback_suggestions(manuscript, str(e))

    def _extract_pdf_content(self, pdf_path: str) -> str:
        """Extract text content from PDF for AI analysis"""
        try:
            # Try to use the enhanced PDF parser from the project
            try:
                from pdf_parser import UltraEnhancedPDFParser
                parser = UltraEnhancedPDFParser()
                metadata = parser.extract_metadata(pdf_path)
                
                # Combine title, abstract, and content
                content_parts = []
                if hasattr(metadata, 'title') and metadata.title:
                    content_parts.append(f"Title: {metadata.title}")
                if hasattr(metadata, 'abstract') and metadata.abstract:
                    content_parts.append(f"Abstract: {metadata.abstract}")
                elif hasattr(metadata, 'raw_text') and metadata.raw_text:
                    # Use raw text if abstract not available
                    content_parts.append(f"Content: {metadata.raw_text[:5000]}")
                if hasattr(metadata, 'full_text') and metadata.full_text:
                    content_parts.append(f"Content: {metadata.full_text[:5000]}")  # Limit content length
                
                return "\n\n".join(content_parts)
                
            except ImportError:
                # Fallback to basic PDF extraction
                try:
                    import PyPDF2
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages[:10]:  # Limit to first 10 pages
                            text += page.extract_text() + "\n"
                        return text[:5000]  # Limit to 5000 characters
                except ImportError:
                    # Final fallback - try to read as text
                    with open(pdf_path, 'r', encoding='utf-8', errors='ignore') as file:
                        return file.read()[:5000]
                    
        except Exception as e:
            if self.debug:
                self.logger.error(f"Error extracting PDF content: {e}")
            return ""

    def _analyze_paper_content(self, content: str, manuscript: Dict) -> Dict:
        """Analyze paper content using AI to extract key information"""
        try:
            # Try to use OpenAI API for analysis
            try:
                import openai
                
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return self._fallback_content_analysis(content, manuscript)
                
                openai.api_key = api_key
                
                # Customize prompt based on journal
                journal_specific_info = self._get_journal_specific_analysis_prompt()
                
                # Prompt for paper analysis
                analysis_prompt = f"""
                Analyze the following academic paper from {self.journal_name} journal and extract key information for referee assignment:

                Paper Title: {manuscript.get('Title', 'Unknown')}
                Journal: {self.journal_name}
                
                {journal_specific_info}
                
                Content:
                {content[:3000]}  # Limit content for API

                Please provide:
                1. Research area and subfield
                2. Key topics and keywords
                3. Methodologies used
                4. Required referee expertise
                5. Difficulty level (1-10)
                6. Suggested reviewer qualifications

                Format your response as JSON with keys: research_area, keywords, methodologies, required_expertise, difficulty, reviewer_qualifications
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are an expert academic editor for {self.journal_name} analyzing papers for referee assignment."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                import json
                analysis = json.loads(response.choices[0].message.content)
                
                return {
                    'research_area': analysis.get('research_area', 'Unknown'),
                    'keywords': analysis.get('keywords', []),
                    'methodologies': analysis.get('methodologies', []),
                    'required_expertise': analysis.get('required_expertise', []),
                    'difficulty': analysis.get('difficulty', 5),
                    'reviewer_qualifications': analysis.get('reviewer_qualifications', []),
                    'ai_confidence': 0.8,
                    'analysis_method': 'openai_gpt',
                    'journal': self.journal_name
                }
                
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"OpenAI analysis failed: {e}")
                return self._fallback_content_analysis(content, manuscript)
                
        except Exception as e:
            if self.debug:
                self.logger.error(f"Content analysis failed: {e}")
            return self._fallback_content_analysis(content, manuscript)

    def _get_journal_specific_analysis_prompt(self) -> str:
        """Get journal-specific analysis prompts"""
        journal_prompts = {
            'FS': 'Focus on stochastic processes, mathematical finance, and quantitative methods.',
            'MF': 'Emphasize mathematical finance, derivatives pricing, and risk management.',
            'MOR': 'Concentrate on operations research, optimization, and management science.',
            'JOTA': 'Focus on optimization theory, variational analysis, and control theory.',
            'SICON': 'Emphasize control theory, numerical analysis, and applied mathematics.',
            'SIFIN': 'Focus on financial mathematics, computational methods, and quantitative finance.',
            'NACO': 'Concentrate on numerical analysis, computational optimization, and scientific computing.',
            'MAFE': 'Emphasize mathematical finance, economics, and applied probability.',
        }
        
        return journal_prompts.get(self.journal_name, 'Focus on the mathematical and theoretical aspects of the paper.')

    def _fallback_content_analysis(self, content: str, manuscript: Dict) -> Dict:
        """Fallback content analysis using basic NLP when OpenAI is not available"""
        try:
            # Basic keyword extraction
            import re
            
            # Extract potential keywords from content
            words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
            
            # Journal-specific keyword sets
            journal_keywords = {
                'FS': ['stochastic', 'finance', 'portfolio', 'volatility', 'derivative', 'option'],
                'MF': ['mathematical', 'finance', 'pricing', 'risk', 'market', 'portfolio'],
                'MOR': ['optimization', 'operations', 'management', 'decision', 'supply', 'logistics'],
                'JOTA': ['optimization', 'variational', 'control', 'calculus', 'analysis'],
                'SICON': ['control', 'numerical', 'computation', 'algorithm', 'simulation'],
                'SIFIN': ['financial', 'mathematics', 'computational', 'quantitative'],
                'NACO': ['numerical', 'computational', 'optimization', 'scientific'],
                'MAFE': ['mathematical', 'finance', 'economics', 'probability']
            }
            
            # Common mathematical/computational terms
            general_terms = ['optimization', 'algorithm', 'theorem', 'proof', 'analysis', 'numerical', 'computation']
            
            # Get journal-specific terms
            journal_terms = journal_keywords.get(self.journal_name, [])
            all_terms = general_terms + journal_terms
            
            keywords = []
            for term in all_terms:
                if term in content.lower():
                    keywords.append(term)
            
            # Determine research area based on journal and keywords
            research_area = self._determine_research_area(keywords)
            
            return {
                'research_area': research_area,
                'keywords': keywords[:10],  # Top 10 keywords
                'methodologies': ['mathematical_analysis'],
                'required_expertise': [research_area.lower().replace(' ', '_')],
                'difficulty': 6,
                'reviewer_qualifications': [f'PhD in {research_area} or related field'],
                'ai_confidence': 0.4,
                'analysis_method': 'basic_nlp',
                'journal': self.journal_name
            }
            
        except Exception as e:
            if self.debug:
                self.logger.error(f"Fallback analysis failed: {e}")
            return {
                'research_area': 'Unknown',
                'keywords': [],
                'methodologies': [],
                'required_expertise': [],
                'difficulty': 5,
                'reviewer_qualifications': [],
                'ai_confidence': 0.1,
                'analysis_method': 'minimal',
                'journal': self.journal_name
            }

    def _determine_research_area(self, keywords: List[str]) -> str:
        """Determine research area based on keywords and journal"""
        journal_areas = {
            'FS': 'Financial Stochastics',
            'MF': 'Mathematical Finance',
            'MOR': 'Operations Research',
            'JOTA': 'Optimization Theory',
            'SICON': 'Control Theory',
            'SIFIN': 'Financial Mathematics',
            'NACO': 'Numerical Analysis',
            'MAFE': 'Mathematical Finance'
        }
        
        # Start with journal default
        base_area = journal_areas.get(self.journal_name, 'Mathematics')
        
        # Refine based on keywords
        if any(term in keywords for term in ['stochastic', 'probability', 'random']):
            return f'Stochastic {base_area}'
        elif any(term in keywords for term in ['numerical', 'computational', 'algorithm']):
            return f'Computational {base_area}'
        elif any(term in keywords for term in ['optimization', 'control', 'optimal']):
            return f'Optimization and {base_area}'
        
        return base_area

    def _get_referee_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate referee recommendations based on content analysis"""
        try:
            # Try to use existing referee database
            try:
                from database.referee_db import RefereeDatabase
                referee_db = RefereeDatabase()
                
                # Match referees based on expertise
                required_expertise = analysis.get('required_expertise', [])
                keywords = analysis.get('keywords', [])
                
                matching_referees = []
                for expertise in required_expertise:
                    refs = referee_db.get_referees_by_expertise(expertise)
                    matching_referees.extend(refs)
                
                # Also search by keywords
                for keyword in keywords[:5]:  # Top 5 keywords
                    refs = referee_db.search_by_keyword(keyword)
                    matching_referees.extend(refs)
                
                # Remove duplicates and filter by journal experience
                seen_emails = set()
                filtered_referees = []
                for referee in matching_referees:
                    email = referee.get('email', '')
                    if email not in seen_emails:
                        seen_emails.add(email)
                        # Check if referee has experience with this journal
                        if self._has_journal_experience(referee):
                            filtered_referees.append(referee)
                
                # Convert to recommendation format
                recommendations = []
                for i, referee in enumerate(filtered_referees[:10]):  # Top 10 recommendations
                    recommendations.append({
                        'rank': i + 1,
                        'referee_name': referee.get('name', 'Unknown'),
                        'referee_email': referee.get('email', ''),
                        'expertise_match': referee.get('expertise_areas', []),
                        'confidence': max(0.5, 0.9 - i * 0.05),  # Decreasing confidence
                        'recommendation_reason': f"Expertise in {', '.join(referee.get('expertise_areas', []))}",
                        'workload_status': referee.get('current_workload', 'Unknown'),
                        'recent_activity': referee.get('last_review_date', 'Unknown'),
                        'journal_experience': self._get_journal_experience(referee)
                    })
                
                return recommendations
                
            except ImportError:
                # Fallback to generic recommendations
                return self._fallback_referee_recommendations(analysis)
                
        except Exception as e:
            if self.debug:
                self.logger.error(f"Error generating referee recommendations: {e}")
            return self._fallback_referee_recommendations(analysis)

    def _has_journal_experience(self, referee: Dict) -> bool:
        """Check if referee has experience with this journal"""
        journal_history = referee.get('journal_history', [])
        return self.journal_name in journal_history or len(journal_history) > 0

    def _get_journal_experience(self, referee: Dict) -> str:
        """Get referee's journal experience summary"""
        journal_history = referee.get('journal_history', [])
        if self.journal_name in journal_history:
            return f"Previous experience with {self.journal_name}"
        elif journal_history:
            return f"Experience with {', '.join(journal_history[:3])}"
        else:
            return "No recorded journal experience"

    def _fallback_referee_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate fallback referee recommendations when database is not available"""
        research_area = analysis.get('research_area', 'Unknown')
        keywords = analysis.get('keywords', [])
        
        # Generate generic recommendations based on research area and journal
        recommendations = [
            {
                'rank': 1,
                'referee_name': f'Expert in {research_area}',
                'referee_email': 'expert@university.edu',
                'expertise_match': [research_area.lower()],
                'confidence': 0.7,
                'recommendation_reason': f'Specializes in {research_area} for {self.journal_name}',
                'workload_status': 'Unknown',
                'recent_activity': 'Unknown',
                'journal_experience': f'Recommended for {self.journal_name}'
            },
            {
                'rank': 2,
                'referee_name': f'Senior Researcher in {self.journal_name}',
                'referee_email': 'senior@institution.edu',
                'expertise_match': keywords[:3],
                'confidence': 0.6,
                'recommendation_reason': f'Experience with {", ".join(keywords[:3])} in {self.journal_name}',
                'workload_status': 'Unknown',
                'recent_activity': 'Unknown',
                'journal_experience': f'Suitable for {self.journal_name}'
            },
            {
                'rank': 3,
                'referee_name': f'Associate Professor',
                'referee_email': 'associate@college.edu',
                'expertise_match': [research_area.lower()],
                'confidence': 0.5,
                'recommendation_reason': f'Academic expertise in {research_area}',
                'workload_status': 'Unknown',
                'recent_activity': 'Unknown',
                'journal_experience': 'General academic experience'
            }
        ]
        
        return recommendations

    def _fallback_suggestions(self, manuscript: Dict, error_message: str) -> Dict:
        """Generate fallback AI suggestions when the main system fails"""
        return {
            'status': 'error',
            'journal': self.journal_name,
            'pdf_path': '',
            'manuscript_id': manuscript.get('Manuscript #', ''),
            'title': manuscript.get('Title', ''),
            'error': error_message,
            'suggestions': [
                {
                    'rank': 1,
                    'referee_name': 'Manual Review Required',
                    'referee_email': '',
                    'expertise_match': [],
                    'confidence': 0.0,
                    'recommendation_reason': f'AI analysis failed for {self.journal_name} - manual referee selection needed',
                    'workload_status': 'Unknown',
                    'recent_activity': 'Unknown',
                    'journal_experience': 'Manual selection required'
                }
            ],
            'generated_at': time.time()
        }

def get_ai_analyzer(journal_name: str, debug: bool = False) -> AIRefereeAnalyzer:
    """
    Factory function to get an AI analyzer for any journal.
    
    Args:
        journal_name: Name of the journal (e.g., 'FS', 'MF', 'SICON', etc.)
        debug: Whether to enable debug logging
        
    Returns:
        AIRefereeAnalyzer instance configured for the journal
    """
    return AIRefereeAnalyzer(journal_name, debug)