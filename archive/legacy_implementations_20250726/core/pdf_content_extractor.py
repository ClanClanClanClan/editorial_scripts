#!/usr/bin/env python3
"""
Advanced PDF content extraction for manuscripts.
Extracts abstracts, keywords, metadata, and performs content analysis.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

try:
    import numpy as np
    import pdfplumber
    import PyPDF2
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    print(f"⚠️ Missing dependencies for PDF extraction: {e}")
    print("Install with: pip install PyPDF2 pdfplumber scikit-learn numpy")


class ManuscriptPDFExtractor:
    """Extract detailed content and metadata from manuscript PDFs."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Common mathematical finance keywords for subject classification
        self.mf_keywords = {
            "stochastic_processes": [
                "stochastic",
                "brownian",
                "markov",
                "diffusion",
                "jump",
                "levy",
            ],
            "optimization": [
                "optimization",
                "optimal",
                "control",
                "portfolio",
                "utility",
                "hedging",
            ],
            "derivatives": ["option", "derivative", "pricing", "volatility", "black-scholes"],
            "risk_management": ["risk", "var", "cvar", "coherent", "measure", "capital"],
            "behavioral_finance": [
                "behavioral",
                "sentiment",
                "bias",
                "psychology",
                "irrationality",
            ],
            "market_microstructure": [
                "microstructure",
                "liquidity",
                "spread",
                "orderbook",
                "trading",
            ],
            "econometrics": ["econometric", "regression", "time series", "garch", "var model"],
            "machine_learning": ["machine learning", "neural", "algorithm", "prediction", "ai"],
        }

    def extract_manuscript_content(self, pdf_path: str, manuscript_id: str) -> dict[str, Any]:
        """Extract comprehensive content from manuscript PDF."""
        try:
            print(f"🔍 Extracting content from {manuscript_id} PDF...")

            # Extract text using multiple methods
            text_content = self._extract_text_robust(pdf_path)

            if not text_content:
                print(f"❌ Failed to extract text from {pdf_path}")
                return {}

            # Analyze the extracted text
            content_analysis = {
                "manuscript_id": manuscript_id,
                "pdf_path": pdf_path,
                "extraction_timestamp": datetime.now().isoformat(),
                "text_length": len(text_content),
                "word_count": len(text_content.split()),
                "abstract": self._extract_abstract(text_content),
                "keywords": self._extract_keywords(text_content),
                "subject_classifications": self._classify_subjects(text_content),
                "funding_acknowledgments": self._extract_funding(text_content),
                "data_availability": self._extract_data_availability(text_content),
                "authors_from_pdf": self._extract_authors_from_pdf(text_content),
                "title_from_pdf": self._extract_title(text_content),
                "references_count": self._count_references(text_content),
                "figures_tables": self._count_figures_tables(text_content),
                "mathematical_content": self._analyze_mathematical_content(text_content),
                "language_indicators": self._detect_language_indicators(text_content),
                "quality_indicators": self._assess_quality_indicators(text_content),
            }

            print(f"✅ Extracted {len(content_analysis['abstract'])} char abstract")
            print(
                f"   📊 {content_analysis['word_count']} words, {content_analysis['references_count']} references"
            )
            print(
                f"   🏷️ {len(content_analysis['keywords'])} keywords, {len(content_analysis['subject_classifications'])} subject areas"
            )

            return content_analysis

        except Exception as e:
            print(f"❌ Error extracting content from {pdf_path}: {str(e)}")
            return {}

    def _extract_text_robust(self, pdf_path: str) -> str:
        """Extract text using multiple methods for robustness."""
        text_content = ""

        # Method 1: pdfplumber (best for complex layouts)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:10]:  # First 10 pages should contain abstract/intro
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
        except Exception as e:
            print(f"   ⚠️ pdfplumber failed: {e}")

        # Method 2: PyPDF2 fallback
        if len(text_content) < 1000:  # If pdfplumber didn't get much text
            try:
                with open(pdf_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(min(10, len(pdf_reader.pages))):
                        page = pdf_reader.pages[page_num]
                        text_content += page.extract_text() + "\n"
            except Exception as e:
                print(f"   ⚠️ PyPDF2 fallback failed: {e}")

        return text_content.strip()

    def _extract_abstract(self, text: str) -> str:
        """Extract the abstract from the manuscript text."""
        # Common abstract patterns in academic papers
        abstract_patterns = [
            r"(?i)abstract\s*:?\s*\n?(.*?)(?=\n\s*(?:keywords?|introduction|1\.|§\s*1))",
            r"(?i)abstract\s*:?\s*\n?(.*?)(?=\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*:)",
            r"(?i)abstract\s*:?\s*\n?(.*?)(?=\n\s*\d+\.)",
            r"(?i)abstract\s*:?\s*\n?(.*?)(?=\n\s*[IVX]+\.)",
        ]

        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r"\n+", " ", abstract)  # Replace newlines with spaces
                abstract = re.sub(r"\s+", " ", abstract)  # Normalize whitespace
                if 50 <= len(abstract) <= 2000:  # Reasonable abstract length
                    return abstract

        # If no clear abstract section, try to find the first substantial paragraph
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        for paragraph in paragraphs[:5]:  # Check first 5 paragraphs
            if 100 <= len(paragraph) <= 2000 and not any(
                word in paragraph.lower() for word in ["figure", "table", "section", "theorem"]
            ):
                return paragraph

        return ""

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract author-provided keywords."""
        # Look for explicit keywords section
        keyword_patterns = [
            r"(?i)keywords?\s*:?\s*\n?(.*?)(?=\n\s*(?:introduction|1\.|§\s*1|abstract))",
            r"(?i)key\s+words?\s*:?\s*\n?(.*?)(?=\n\s*[A-Z])",
            r"(?i)subject\s+classification\s*:?\s*\n?(.*?)(?=\n\s*[A-Z])",
        ]

        for pattern in keyword_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                keywords_text = match.group(1).strip()
                # Parse keywords (usually comma or semicolon separated)
                keywords = []
                for delimiter in [";", ",", "\n"]:
                    if delimiter in keywords_text:
                        keywords = [k.strip() for k in keywords_text.split(delimiter)]
                        break

                # Clean and validate keywords
                clean_keywords = []
                for kw in keywords:
                    kw = re.sub(r"[^\w\s-]", "", kw).strip()
                    if 2 <= len(kw) <= 50 and kw.lower() not in ["and", "or", "the", "a", "an"]:
                        clean_keywords.append(kw)

                if clean_keywords:
                    return clean_keywords[:10]  # Limit to 10 keywords

        # If no explicit keywords, extract key terms using TF-IDF
        return self._extract_key_terms_tfidf(text)

    def _extract_key_terms_tfidf(self, text: str) -> list[str]:
        """Extract key terms using TF-IDF analysis."""
        try:
            # Clean text and split into sentences
            sentences = [
                sent.strip() for sent in re.split(r"[.!?]+", text) if len(sent.strip()) > 20
            ]

            if len(sentences) < 5:
                return []

            # Use TF-IDF to find important terms
            vectorizer = TfidfVectorizer(
                max_features=100, stop_words="english", ngram_range=(1, 3), min_df=1, max_df=0.95
            )

            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()

            # Get mean TF-IDF scores
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)

            # Sort by score and get top terms
            top_indices = mean_scores.argsort()[-20:][::-1]
            key_terms = [feature_names[i] for i in top_indices if mean_scores[i] > 0.1]

            # Filter for mathematical finance relevance
            relevant_terms = []
            for term in key_terms:
                if any(
                    mf_term in term.lower()
                    for category in self.mf_keywords.values()
                    for mf_term in category
                ):
                    relevant_terms.append(term)

            return relevant_terms[:8] if relevant_terms else key_terms[:8]

        except Exception as e:
            print(f"   ⚠️ TF-IDF keyword extraction failed: {e}")
            return []

    def _classify_subjects(self, text: str) -> list[str]:
        """Classify the manuscript into mathematical finance subject areas."""
        text_lower = text.lower()
        classifications = []

        for category, keywords in self.mf_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
            if keyword_count >= 2:  # Need at least 2 keywords from a category
                classifications.append(category.replace("_", " ").title())

        return classifications

    def _extract_funding(self, text: str) -> str:
        """Extract funding acknowledgments."""
        funding_patterns = [
            r"(?i)(?:funding|grant|support|acknowledgment|acknowledgement)s?\s*:?\s*\n?(.*?)(?=\n\s*(?:references|bibliography|\d+\.))",
            r"(?i)this\s+(?:work|research)\s+(?:was|is)\s+supported\s+by\s+(.*?)(?=\.|;|\n)",
            r"(?i)(?:grant|funding)\s+(?:number|no\.?|#)\s*:?\s*([A-Z0-9-]+)",
        ]

        for pattern in funding_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                funding = match.group(1).strip()
                if 10 <= len(funding) <= 500:
                    return funding

        return ""

    def _extract_data_availability(self, text: str) -> str:
        """Extract data availability statements."""
        data_patterns = [
            r"(?i)data\s+availability\s*:?\s*\n?(.*?)(?=\n\s*(?:references|author|conflict))",
            r"(?i)(?:data|code)\s+(?:is|are)\s+available\s+(.*?)(?=\.|;|\n)",
            r"(?i)(?:datasets?|data)\s+used\s+in\s+this\s+study\s+(.*?)(?=\.|;|\n)",
        ]

        for pattern in data_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                statement = match.group(1).strip()
                if 10 <= len(statement) <= 300:
                    return statement

        return ""

    def _extract_authors_from_pdf(self, text: str) -> list[dict[str, str]]:
        """Extract author information from PDF text."""
        # Look for author section near the top
        first_1000_chars = text[:1000]

        # Pattern for authors with affiliations
        author_patterns = [
            r"(?i)(?:authors?|by)\s*:?\s*\n?(.*?)(?=\n\s*(?:abstract|introduction))",
            r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)(?:\s*[,;]\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+))*",
        ]

        authors = []
        for pattern in author_patterns:
            matches = re.finditer(pattern, first_1000_chars)
            for match in matches:
                author_text = match.group(1) if match.groups() else match.group(0)
                # Parse individual authors
                author_names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+", author_text)
                for name in author_names[:10]:  # Limit to 10 authors
                    authors.append({"name": name.strip(), "source": "pdf_extraction"})

        return authors

    def _extract_title(self, text: str) -> str:
        """Extract the manuscript title from PDF."""
        # Title is usually in the first few lines, often in larger font
        first_500_chars = text[:500]
        lines = [line.strip() for line in first_500_chars.split("\n") if line.strip()]

        for line in lines[:5]:  # Check first 5 lines
            # Skip common header elements
            if any(
                skip in line.lower()
                for skip in ["page", "doi", "manuscript", "received", "accepted"]
            ):
                continue

            # Title characteristics: reasonable length, mixed case, no periods at end
            if 10 <= len(line) <= 200 and not line.endswith(".") and any(c.islower() for c in line):
                return line

        return ""

    def _count_references(self, text: str) -> int:
        """Count the number of references."""
        # Look for references section
        ref_patterns = [
            r"(?i)references\s*\n(.*?)(?=\n\s*(?:appendix|index)|\Z)",
            r"(?i)bibliography\s*\n(.*?)(?=\n\s*(?:appendix|index)|\Z)",
        ]

        for pattern in ref_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                ref_text = match.group(1)
                # Count numbered references [1], [2], etc.
                numbered_refs = len(re.findall(r"\[\d+\]", ref_text))
                if numbered_refs > 0:
                    return numbered_refs

                # Count references starting with author names
                author_refs = len(re.findall(r"\n[A-Z][a-z]+,\s+[A-Z]\.", ref_text))
                if author_refs > 0:
                    return author_refs

        # Fallback: count citation patterns in text
        citations = len(re.findall(r"\[[\d,\s-]+\]", text))
        return max(1, citations // 2)  # Rough estimate

    def _count_figures_tables(self, text: str) -> dict[str, int]:
        """Count figures and tables mentioned in the text."""
        figures = len(re.findall(r"(?i)figure\s+\d+", text))
        tables = len(re.findall(r"(?i)table\s+\d+", text))

        return {"figure_count": figures, "table_count": tables}

    def _analyze_mathematical_content(self, text: str) -> dict[str, Any]:
        """Analyze mathematical content density and types."""
        # Count mathematical expressions
        latex_patterns = len(re.findall(r"\$.*?\$|\\\(.*?\\\)|\\\[.*?\\\]", text))
        equation_numbers = len(re.findall(r"(?i)equation\s+\(\d+\)", text))
        theorem_refs = len(re.findall(r"(?i)(?:theorem|lemma|proposition|corollary)\s+\d+", text))

        # Mathematical finance specific terms
        mf_term_count = 0
        for category, terms in self.mf_keywords.items():
            mf_term_count += sum(text.lower().count(term) for term in terms)

        return {
            "latex_expressions": latex_patterns,
            "numbered_equations": equation_numbers,
            "theorem_references": theorem_refs,
            "mf_term_density": mf_term_count / max(1, len(text.split())) * 1000,  # per 1000 words
            "mathematical_sophistication": "high"
            if latex_patterns > 20
            else "medium"
            if latex_patterns > 5
            else "low",
        }

    def _detect_language_indicators(self, text: str) -> dict[str, Any]:
        """Detect language and regional indicators."""
        # Simple language detection based on common words
        english_indicators = ["the", "and", "or", "but", "with", "for", "this", "that"]
        english_score = sum(text.lower().count(word) for word in english_indicators)

        # Regional spelling indicators
        us_spelling = ["optimize", "analyze", "realize", "color", "center"]
        uk_spelling = ["optimise", "analyse", "realise", "colour", "centre"]

        us_count = sum(text.lower().count(word) for word in us_spelling)
        uk_count = sum(text.lower().count(word) for word in uk_spelling)

        return {
            "primary_language": "en",
            "confidence_score": min(1.0, english_score / 100),
            "regional_variant": "us"
            if us_count > uk_count
            else "uk"
            if uk_count > 0
            else "unknown",
        }

    def _assess_quality_indicators(self, text: str) -> dict[str, Any]:
        """Assess manuscript quality indicators."""
        word_count = len(text.split())

        # Readability metrics (simplified)
        sentences = len(re.split(r"[.!?]+", text))
        avg_sentence_length = word_count / max(1, sentences)

        # Technical depth indicators
        technical_terms = len(
            re.findall(r"(?i)(?:theorem|lemma|proposition|corollary|proof|definition)", text)
        )

        # Citation density
        citations = len(re.findall(r"\[[\d,\s-]+\]", text))
        citation_density = citations / max(1, word_count) * 1000  # per 1000 words

        return {
            "word_count": word_count,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "technical_depth_score": min(10, technical_terms / 5),  # 0-10 scale
            "citation_density": round(citation_density, 2),
            "estimated_reading_level": "graduate" if avg_sentence_length > 25 else "undergraduate",
            "completeness_indicators": {
                "has_abstract": len(self._extract_abstract(text)) > 50,
                "has_references": citations > 10,
                "has_mathematical_content": "\\" in text or "$" in text,
                "sufficient_length": word_count > 3000,
            },
        }


def extract_all_manuscript_pdfs(pdf_directory: str = "downloads/manuscripts") -> dict[str, Any]:
    """Extract content from all manuscript PDFs."""
    extractor = ManuscriptPDFExtractor()

    print("🔍 EXTRACTING CONTENT FROM ALL MANUSCRIPT PDFs")
    print("=" * 60)

    results = {}
    pdf_files = []

    # Find all PDF files
    for root, dirs, files in os.walk(pdf_directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    print(f"Found {len(pdf_files)} PDF files to process")

    for pdf_path in pdf_files:
        # Extract manuscript ID from filename
        filename = os.path.basename(pdf_path)
        manuscript_id = filename.replace(".pdf", "")

        print(f"\n📄 Processing {manuscript_id}...")

        content = extractor.extract_manuscript_content(pdf_path, manuscript_id)
        if content:
            results[manuscript_id] = content

    # Save results to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"pdf_content_extraction_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n🎉 EXTRACTION COMPLETE!")
    print(f"   📊 Processed {len(results)} manuscripts")
    print(f"   💾 Results saved to: {output_file}")

    # Summary statistics
    total_abstracts = sum(1 for r in results.values() if len(r.get("abstract", "")) > 50)
    total_keywords = sum(len(r.get("keywords", [])) for r in results.values())

    print(f"   📝 {total_abstracts}/{len(results)} abstracts extracted")
    print(f"   🏷️ {total_keywords} total keywords found")

    return results


if __name__ == "__main__":
    # Extract content from all PDFs
    results = extract_all_manuscript_pdfs()
