"""
AI-powered desk rejection analysis system.
This module provides AI-based analysis to determine if papers should be desk rejected
or proceed to the review process, and suggests potential referees for suitable papers.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

class AIDeskRejectionAnalyzer:
    """
    AI-powered system for desk rejection analysis and referee suggestions.
    Analyzes papers without referees to determine next steps.
    """
    
    def __init__(self, journal_name: str, debug: bool = False):
        self.journal_name = journal_name
        self.debug = debug
        self.logger = logging.getLogger(f"[{journal_name}] AIDeskRejectionAnalyzer")
        
    def analyze_manuscript_for_desk_rejection(self, pdf_path: str, manuscript: Dict) -> Dict:
        """
        Analyze a manuscript to determine if it should be desk rejected.
        
        Args:
            pdf_path: Path to the downloaded PDF
            manuscript: Manuscript data dictionary
            
        Returns:
            Dictionary with desk rejection analysis and recommendations
        """
        try:
            # Extract text content from PDF
            pdf_content = self._extract_pdf_content(pdf_path)
            if not pdf_content:
                return self._fallback_desk_rejection_analysis(manuscript, "Could not extract PDF content")
            
            # Perform AI-based desk rejection analysis
            analysis_results = self._analyze_for_desk_rejection(pdf_content, manuscript)
            
            return analysis_results
            
        except Exception as e:
            if self.debug:
                self.logger.error(f"Error in desk rejection analysis: {e}")
            return self._fallback_desk_rejection_analysis(manuscript, str(e))

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

    def _analyze_for_desk_rejection(self, content: str, manuscript: Dict) -> Dict:
        """Analyze paper content to determine if it should be desk rejected"""
        try:
            # Try to use OpenAI API for analysis
            try:
                import openai
                
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return self._fallback_desk_rejection_analysis(content, manuscript)
                
                openai.api_key = api_key
                
                # Customize prompt based on journal
                journal_scope = self._get_journal_scope()
                
                # Prompt for desk rejection analysis
                analysis_prompt = f"""
                You are an expert editor for {self.journal_name} journal. Analyze this submitted paper to determine if it should be:
                1. DESK REJECTED (with reasons)
                2. SENT FOR REVIEW (with suggested referees)

                Journal: {self.journal_name}
                Journal Scope: {journal_scope}
                
                Paper Title: {manuscript.get('Title', 'Unknown')}
                Content:
                {content[:4000]}  # Limit content for API

                Please provide a detailed analysis including:
                1. RECOMMENDATION: "DESK_REJECT" or "SEND_FOR_REVIEW"
                2. REASONING: Detailed explanation (2-3 sentences)
                3. SCOPE_FIT: How well does this fit the journal scope? (1-10 scale)
                4. QUALITY_ASSESSMENT: Technical quality assessment (1-10 scale)
                5. NOVELTY_ASSESSMENT: Novelty and significance (1-10 scale)
                6. REFEREE_SUGGESTIONS: If sending for review, suggest 3-5 potential referee types/expertise areas

                Consider these desk rejection criteria:
                - Papers outside journal scope
                - Poor technical quality or mathematical errors
                - Lack of novelty or significance
                - Insufficient literature review
                - Poor presentation or unclear writing
                - Incomplete or flawed methodology

                Format your response as JSON with keys: recommendation, reasoning, scope_fit, quality_assessment, novelty_assessment, referee_suggestions, confidence_level
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # Use GPT-4 for better analysis
                    messages=[
                        {"role": "system", "content": f"You are an expert academic editor for {self.journal_name} specializing in manuscript evaluation."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.2
                )
                
                import json
                analysis = json.loads(response.choices[0].message.content)
                
                # Process the AI response
                recommendation = analysis.get('recommendation', 'SEND_FOR_REVIEW')
                
                result = {
                    'status': 'completed',
                    'journal': self.journal_name,
                    'pdf_path': pdf_path if 'pdf_path' in locals() else '',
                    'manuscript_id': manuscript.get('Manuscript #', ''),
                    'title': manuscript.get('Title', ''),
                    'recommendation': recommendation,
                    'reasoning': analysis.get('reasoning', 'No reasoning provided'),
                    'scope_fit': analysis.get('scope_fit', 5),
                    'quality_assessment': analysis.get('quality_assessment', 5),
                    'novelty_assessment': analysis.get('novelty_assessment', 5),
                    'confidence_level': analysis.get('confidence_level', 0.7),
                    'ai_method': 'openai_gpt4',
                    'generated_at': time.time()
                }
                
                # Add referee suggestions if paper should be reviewed
                if recommendation == 'SEND_FOR_REVIEW':
                    result['referee_suggestions'] = analysis.get('referee_suggestions', [])
                    result['next_action'] = 'contact_referees'
                else:
                    result['next_action'] = 'desk_reject'
                    result['rejection_reason'] = analysis.get('reasoning', 'Does not meet journal standards')
                
                return result
                
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"OpenAI analysis failed: {e}")
                return self._fallback_desk_rejection_analysis(content, manuscript)
                
        except Exception as e:
            if self.debug:
                self.logger.error(f"Desk rejection analysis failed: {e}")
            return self._fallback_desk_rejection_analysis(content, manuscript)

    def _get_journal_scope(self) -> str:
        """Get journal-specific scope and criteria"""
        journal_scopes = {
            'FS': 'Financial Stochastics: probability theory, mathematical finance, stochastic processes in finance',
            'MF': 'Mathematical Finance: derivatives pricing, risk management, portfolio optimization, financial modeling',
            'MOR': 'Mathematics of Operations Research: optimization, decision theory, game theory, queueing theory',
            'JOTA': 'Journal of Optimization Theory and Applications: mathematical optimization, optimal control, variational analysis',
            'SICON': 'SIAM Journal on Control and Optimization: control theory, optimization, numerical methods, systems theory',
            'SIFIN': 'SIAM Journal on Financial Mathematics: mathematical and computational methods in finance',
            'NACO': 'Numerical Algorithms: computational mathematics, numerical optimization, scientific computing',
            'MAFE': 'Mathematical Finance and Economics: mathematical finance, financial economics, applied probability'
        }
        
        return journal_scopes.get(self.journal_name, 'Mathematical and computational research relevant to the field')

    def _fallback_desk_rejection_analysis(self, content: str, manuscript: Dict) -> Dict:
        """Fallback desk rejection analysis when OpenAI is not available"""
        try:
            # Basic heuristic analysis
            import re
            
            content_lower = content.lower() if isinstance(content, str) else ""
            title = manuscript.get('Title', '').lower()
            
            # Journal-specific keyword matching
            journal_keywords = {
                'FS': ['stochastic', 'probability', 'finance', 'brownian', 'martingale', 'option'],
                'MF': ['finance', 'pricing', 'risk', 'derivative', 'portfolio', 'volatility'],
                'MOR': ['optimization', 'operations', 'decision', 'algorithm', 'linear programming'],
                'JOTA': ['optimization', 'optimal', 'variational', 'control', 'minimization'],
                'SICON': ['control', 'optimal', 'numerical', 'algorithm', 'differential equation'],
                'SIFIN': ['financial', 'mathematics', 'computational', 'pricing', 'risk'],
                'NACO': ['numerical', 'algorithm', 'computational', 'optimization', 'scientific'],
                'MAFE': ['mathematical', 'finance', 'economics', 'probability', 'market']
            }
            
            # Get journal-specific terms
            relevant_keywords = journal_keywords.get(self.journal_name, [])
            
            # Count keyword matches
            keyword_matches = sum(1 for keyword in relevant_keywords if keyword in content_lower or keyword in title)
            
            # Basic quality indicators
            has_theorem = any(word in content_lower for word in ['theorem', 'proposition', 'lemma', 'proof'])
            has_references = 'references' in content_lower or 'bibliography' in content_lower
            has_abstract = 'abstract' in content_lower
            has_conclusion = 'conclusion' in content_lower or 'conclusions' in content_lower
            
            # Simple scoring
            scope_fit = min(10, max(1, keyword_matches * 2))
            quality_score = 5  # Default neutral
            
            if has_theorem:
                quality_score += 1
            if has_references:
                quality_score += 1
            if has_abstract:
                quality_score += 1
            if has_conclusion:
                quality_score += 1
                
            # Decision logic
            if scope_fit >= 6 and quality_score >= 6:
                recommendation = 'SEND_FOR_REVIEW'
                reasoning = f"Paper appears to fit journal scope (score: {scope_fit}/10) with adequate quality indicators (score: {quality_score}/10). Recommend sending for peer review."
                next_action = 'contact_referees'
            else:
                recommendation = 'DESK_REJECT'
                if scope_fit < 6:
                    reasoning = f"Paper does not sufficiently fit journal scope (score: {scope_fit}/10). Consider submitting to a more appropriate journal."
                else:
                    reasoning = f"Paper quality concerns (score: {quality_score}/10). May lack proper structure, references, or theoretical rigor."
                next_action = 'desk_reject'
            
            return {
                'status': 'completed',
                'journal': self.journal_name,
                'pdf_path': '',
                'manuscript_id': manuscript.get('Manuscript #', ''),
                'title': manuscript.get('Title', ''),
                'recommendation': recommendation,
                'reasoning': reasoning,
                'scope_fit': scope_fit,
                'quality_assessment': quality_score,
                'novelty_assessment': 5,  # Neutral default
                'confidence_level': 0.4,  # Lower confidence for fallback
                'ai_method': 'basic_heuristic',
                'next_action': next_action,
                'generated_at': time.time()
            }
            
        except Exception as e:
            if self.debug:
                self.logger.error(f"Fallback analysis failed: {e}")
            return {
                'status': 'error',
                'journal': self.journal_name,
                'manuscript_id': manuscript.get('Manuscript #', ''),
                'title': manuscript.get('Title', ''),
                'recommendation': 'SEND_FOR_REVIEW',  # Conservative default
                'reasoning': 'Analysis failed - recommend manual review',
                'error': str(e),
                'next_action': 'manual_review',
                'generated_at': time.time()
            }

def get_desk_rejection_analyzer(journal_name: str, debug: bool = False) -> AIDeskRejectionAnalyzer:
    """
    Factory function to get a desk rejection analyzer for any journal.
    
    Args:
        journal_name: Name of the journal (e.g., 'FS', 'MF', 'SICON', etc.)
        debug: Whether to enable debug logging
        
    Returns:
        AIDeskRejectionAnalyzer instance configured for the journal
    """
    return AIDeskRejectionAnalyzer(journal_name, debug)