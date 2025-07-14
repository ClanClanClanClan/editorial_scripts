"""
Accuracy validation tests for AI services
Tests AI predictions against historical editorial decisions and outcomes
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.ai.services.ai_orchestrator_service import AIOrchestrator
from src.ai.models.manuscript_analysis import AnalysisRecommendation


@dataclass
class HistoricalCase:
    """Historical manuscript case for validation"""
    manuscript_id: str
    title: str
    abstract: str
    journal_code: str
    actual_decision: str  # "accept", "reject", "major_revision", "minor_revision"
    actual_referees: List[str]
    submission_date: datetime
    final_outcome: str
    metadata: Dict[str, Any] = None


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for AI predictions"""
    total_cases: int
    correct_predictions: int
    accuracy_rate: float
    precision_by_class: Dict[str, float]
    recall_by_class: Dict[str, float]
    f1_score_by_class: Dict[str, float]
    confusion_matrix: Dict[Tuple[str, str], int]
    
    def print_report(self):
        """Print detailed accuracy report"""
        print("\n" + "="*60)
        print("🎯 AI ACCURACY VALIDATION REPORT")
        print("="*60)
        print(f"Total cases evaluated: {self.total_cases}")
        print(f"Correct predictions: {self.correct_predictions}")
        print(f"Overall accuracy: {self.accuracy_rate:.1%}")
        print()
        
        print("📊 Performance by Class:")
        for class_name in self.precision_by_class:
            precision = self.precision_by_class[class_name]
            recall = self.recall_by_class[class_name]
            f1 = self.f1_score_by_class[class_name]
            print(f"  {class_name}:")
            print(f"    Precision: {precision:.1%}")
            print(f"    Recall: {recall:.1%}")
            print(f"    F1-Score: {f1:.1%}")
        print()
        
        print("🔍 Confusion Matrix:")
        classes = list(self.precision_by_class.keys())
        print("    " + "".join(f"{c:>12}" for c in classes))
        for actual in classes:
            row = f"{actual:>8}"
            for predicted in classes:
                count = self.confusion_matrix.get((actual, predicted), 0)
                row += f"{count:>12}"
            print(row)


class AIAccuracyValidator:
    """Validates AI predictions against historical data"""
    
    def __init__(self, ai_orchestrator: AIOrchestrator):
        self.orchestrator = ai_orchestrator
        self.decision_mapping = {
            # Map AI recommendations to editorial decisions
            AnalysisRecommendation.ACCEPT_FOR_REVIEW: "accept",
            AnalysisRecommendation.DESK_REJECT: "reject",
            AnalysisRecommendation.REQUIRES_REVISION: "major_revision",
            AnalysisRecommendation.UNCERTAIN: "uncertain"
        }
    
    def load_historical_cases(self, data_path: str) -> List[HistoricalCase]:
        """Load historical cases from JSON file"""
        try:
            with open(data_path, 'r') as f:
                data = json.load(f)
            
            cases = []
            for case_data in data:
                case = HistoricalCase(
                    manuscript_id=case_data['manuscript_id'],
                    title=case_data['title'],
                    abstract=case_data['abstract'],
                    journal_code=case_data['journal_code'],
                    actual_decision=case_data['actual_decision'],
                    actual_referees=case_data.get('actual_referees', []),
                    submission_date=datetime.fromisoformat(case_data['submission_date']),
                    final_outcome=case_data['final_outcome'],
                    metadata=case_data.get('metadata', {})
                )
                cases.append(case)
            
            return cases
        
        except FileNotFoundError:
            print(f"⚠️ Historical data file not found: {data_path}")
            return self.generate_mock_historical_cases()
    
    def generate_mock_historical_cases(self) -> List[HistoricalCase]:
        """Generate mock historical cases for testing"""
        mock_cases = [
            HistoricalCase(
                manuscript_id="HIST-001",
                title="Novel Optimization Algorithm for Convex Problems",
                abstract="We present a new first-order method for solving convex optimization problems with improved convergence rates.",
                journal_code="SICON",
                actual_decision="accept",
                actual_referees=["Dr. Smith", "Prof. Johnson"],
                submission_date=datetime(2024, 1, 15),
                final_outcome="published"
            ),
            HistoricalCase(
                manuscript_id="HIST-002",
                title="A Simple Approach",
                abstract="This paper presents a simple approach without much detail.",
                journal_code="SICON",
                actual_decision="reject",
                actual_referees=[],
                submission_date=datetime(2024, 2, 10),
                final_outcome="rejected"
            ),
            HistoricalCase(
                manuscript_id="HIST-003",
                title="Machine Learning for Financial Optimization",
                abstract="We apply deep learning techniques to portfolio optimization problems, achieving significant improvements over traditional methods.",
                journal_code="SIFIN",
                actual_decision="major_revision",
                actual_referees=["Dr. Brown", "Prof. Davis", "Dr. Wilson"],
                submission_date=datetime(2024, 3, 5),
                final_outcome="published_after_revision"
            ),
            HistoricalCase(
                manuscript_id="HIST-004",
                title="Numerical Methods for Partial Differential Equations",
                abstract="We develop new finite element methods for solving nonlinear PDEs with applications to fluid dynamics and heat transfer.",
                journal_code="SICON",
                actual_decision="minor_revision",
                actual_referees=["Prof. Taylor", "Dr. Anderson"],
                submission_date=datetime(2024, 4, 20),
                final_outcome="published_after_revision"
            ),
            HistoricalCase(
                manuscript_id="HIST-005",
                title="Bad Quality Paper",
                abstract="This is a very short abstract.",
                journal_code="SICON",
                actual_decision="reject",
                actual_referees=[],
                submission_date=datetime(2024, 5, 12),
                final_outcome="rejected"
            )
        ]
        return mock_cases
    
    async def validate_desk_rejection_accuracy(self, cases: List[HistoricalCase]) -> AccuracyMetrics:
        """Validate desk rejection analysis accuracy"""
        print("🔍 Validating desk rejection analysis accuracy...")
        
        predictions = []
        actuals = []
        
        for i, case in enumerate(cases):
            print(f"  Processing case {i+1}/{len(cases)}: {case.manuscript_id}")
            
            try:
                # Get AI prediction
                analysis = await self.orchestrator.analyze_desk_rejection(
                    title=case.title,
                    abstract=case.abstract,
                    journal_code=case.journal_code
                )
                
                predicted = self.decision_mapping[analysis.recommendation]
                actual = case.actual_decision
                
                predictions.append(predicted)
                actuals.append(actual)
                
            except Exception as e:
                print(f"    Error processing case {case.manuscript_id}: {e}")
                continue
        
        return self.calculate_accuracy_metrics(predictions, actuals, "Desk Rejection")
    
    async def validate_referee_recommendation_accuracy(self, cases: List[HistoricalCase]) -> Dict[str, Any]:
        """Validate referee recommendation accuracy"""
        print("🔍 Validating referee recommendation accuracy...")
        
        total_cases = 0
        exact_matches = 0
        partial_matches = 0
        expertise_relevance_scores = []
        
        for i, case in enumerate(cases):
            if not case.actual_referees:
                continue
                
            print(f"  Processing case {i+1}/{len(cases)}: {case.manuscript_id}")
            
            try:
                # Get AI recommendations
                recommendations = await self.orchestrator.recommend_referees(
                    title=case.title,
                    abstract=case.abstract,
                    journal_code=case.journal_code,
                    count=len(case.actual_referees)
                )
                
                recommended_names = [r.referee_name for r in recommendations]
                actual_names = case.actual_referees
                
                # Check for exact matches
                if set(recommended_names) == set(actual_names):
                    exact_matches += 1
                
                # Check for partial matches
                overlap = len(set(recommended_names) & set(actual_names))
                if overlap > 0:
                    partial_matches += 1
                
                # Calculate expertise relevance (mock score based on recommendation scores)
                avg_expertise = sum(r.expertise_match for r in recommendations) / len(recommendations)
                expertise_relevance_scores.append(avg_expertise)
                
                total_cases += 1
                
            except Exception as e:
                print(f"    Error processing case {case.manuscript_id}: {e}")
                continue
        
        return {
            'total_cases': total_cases,
            'exact_match_rate': exact_matches / total_cases if total_cases > 0 else 0,
            'partial_match_rate': partial_matches / total_cases if total_cases > 0 else 0,
            'avg_expertise_relevance': sum(expertise_relevance_scores) / len(expertise_relevance_scores) if expertise_relevance_scores else 0,
            'expertise_scores': expertise_relevance_scores
        }
    
    def calculate_accuracy_metrics(self, predictions: List[str], actuals: List[str], task_name: str) -> AccuracyMetrics:
        """Calculate comprehensive accuracy metrics"""
        if not predictions or not actuals or len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must be non-empty and same length")
        
        total_cases = len(predictions)
        correct_predictions = sum(p == a for p, a in zip(predictions, actuals))
        accuracy_rate = correct_predictions / total_cases
        
        # Get unique classes
        all_classes = list(set(predictions + actuals))
        
        # Calculate precision, recall, F1 for each class
        precision_by_class = {}
        recall_by_class = {}
        f1_score_by_class = {}
        confusion_matrix = {}
        
        for class_name in all_classes:
            # True positives, false positives, false negatives
            tp = sum(1 for p, a in zip(predictions, actuals) if p == class_name and a == class_name)
            fp = sum(1 for p, a in zip(predictions, actuals) if p == class_name and a != class_name)
            fn = sum(1 for p, a in zip(predictions, actuals) if p != class_name and a == class_name)
            
            # Precision and recall
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            precision_by_class[class_name] = precision
            recall_by_class[class_name] = recall
            f1_score_by_class[class_name] = f1
        
        # Confusion matrix
        for actual in all_classes:
            for predicted in all_classes:
                count = sum(1 for p, a in zip(predictions, actuals) if p == predicted and a == actual)
                confusion_matrix[(actual, predicted)] = count
        
        return AccuracyMetrics(
            total_cases=total_cases,
            correct_predictions=correct_predictions,
            accuracy_rate=accuracy_rate,
            precision_by_class=precision_by_class,
            recall_by_class=recall_by_class,
            f1_score_by_class=f1_score_by_class,
            confusion_matrix=confusion_matrix
        )
    
    async def run_comprehensive_validation(self, data_path: str = None) -> Dict[str, Any]:
        """Run comprehensive accuracy validation"""
        print("🚀 Starting comprehensive AI accuracy validation...")
        
        # Load historical cases
        if data_path:
            cases = self.load_historical_cases(data_path)
        else:
            cases = self.generate_mock_historical_cases()
        
        print(f"📚 Loaded {len(cases)} historical cases")
        
        results = {}
        
        # Validate desk rejection accuracy
        try:
            desk_rejection_metrics = await self.validate_desk_rejection_accuracy(cases)
            results['desk_rejection'] = desk_rejection_metrics
            desk_rejection_metrics.print_report()
        except Exception as e:
            print(f"❌ Desk rejection validation failed: {e}")
            results['desk_rejection'] = None
        
        # Validate referee recommendation accuracy
        try:
            referee_metrics = await self.validate_referee_recommendation_accuracy(cases)
            results['referee_recommendation'] = referee_metrics
            
            print("\n📊 Referee Recommendation Accuracy:")
            print(f"  Total cases: {referee_metrics['total_cases']}")
            print(f"  Exact match rate: {referee_metrics['exact_match_rate']:.1%}")
            print(f"  Partial match rate: {referee_metrics['partial_match_rate']:.1%}")
            print(f"  Avg expertise relevance: {referee_metrics['avg_expertise_relevance']:.2f}")
            
        except Exception as e:
            print(f"❌ Referee recommendation validation failed: {e}")
            results['referee_recommendation'] = None
        
        return results


# Mock AI client for testing
class MockAIClientForAccuracy:
    """Mock AI client with realistic responses for accuracy testing"""
    
    async def analyze_desk_rejection(self, title: str, abstract: str, journal_code: str, **kwargs):
        from src.ai.models.manuscript_analysis import DeskRejectionAnalysis, AnalysisRecommendation
        
        # Simple heuristic: short abstracts or "bad" titles get rejected
        if len(abstract) < 50 or "bad" in title.lower() or "simple" in title.lower():
            recommendation = AnalysisRecommendation.DESK_REJECT
            confidence = 0.8
        elif "novel" in title.lower() or "new" in title.lower() or len(abstract) > 100:
            recommendation = AnalysisRecommendation.ACCEPT_FOR_REVIEW
            confidence = 0.75
        else:
            recommendation = AnalysisRecommendation.REQUIRES_REVISION
            confidence = 0.6
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=confidence,
            rejection_reasons=[],
            quality_issues=[],
            detailed_feedback="Mock analysis for accuracy testing"
        )
    
    async def recommend_referees(self, title: str, abstract: str, journal_code: str, count: int = 3, **kwargs):
        from src.ai.models.manuscript_analysis import RefereeRecommendation
        
        # Mock referee database based on keywords
        mock_referees = {
            "optimization": ["Dr. Smith", "Prof. Johnson", "Dr. Brown"],
            "machine learning": ["Prof. Davis", "Dr. Wilson", "Prof. Taylor"],
            "numerical": ["Dr. Anderson", "Prof. Miller", "Dr. Garcia"],
            "financial": ["Dr. Rodriguez", "Prof. Martinez", "Dr. Lopez"]
        }
        
        # Select referees based on title keywords
        selected_referees = []
        for keyword, referees in mock_referees.items():
            if keyword in title.lower() or keyword in abstract.lower():
                selected_referees.extend(referees[:count])
                break
        
        if not selected_referees:
            selected_referees = ["Dr. Default", "Prof. Generic", "Dr. Standard"]
        
        recommendations = []
        for i, name in enumerate(selected_referees[:count]):
            recommendations.append(RefereeRecommendation(
                referee_name=name,
                expertise_match=0.8 + 0.1 * i,
                availability_score=0.9,
                quality_score=0.85,
                workload_score=0.75,
                overall_score=0.82,
                expertise_areas=["relevant_field"],
                rationale=f"Mock recommendation for {name}"
            ))
        
        return recommendations


@pytest.fixture
def mock_orchestrator_for_accuracy():
    """AI orchestrator with mock client for accuracy testing"""
    from src.ai.services.pypdf_processor import PyPDFProcessor
    
    return AIOrchestrator(
        ai_client=MockAIClientForAccuracy(),
        pdf_processor=PyPDFProcessor(),
        cache_enabled=False
    )


@pytest.fixture
def accuracy_validator(mock_orchestrator_for_accuracy):
    """Accuracy validator with mock orchestrator"""
    return AIAccuracyValidator(mock_orchestrator_for_accuracy)


class TestAIAccuracyValidation:
    """Test AI accuracy validation functionality"""
    
    @pytest.mark.asyncio
    async def test_desk_rejection_accuracy_validation(self, accuracy_validator):
        """Test desk rejection accuracy validation"""
        cases = accuracy_validator.generate_mock_historical_cases()
        metrics = await accuracy_validator.validate_desk_rejection_accuracy(cases)
        
        assert metrics.total_cases > 0
        assert 0 <= metrics.accuracy_rate <= 1
        assert len(metrics.precision_by_class) > 0
        assert len(metrics.recall_by_class) > 0
        assert len(metrics.f1_score_by_class) > 0
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_accuracy_validation(self, accuracy_validator):
        """Test referee recommendation accuracy validation"""
        cases = accuracy_validator.generate_mock_historical_cases()
        metrics = await accuracy_validator.validate_referee_recommendation_accuracy(cases)
        
        assert metrics['total_cases'] >= 0
        assert 0 <= metrics['exact_match_rate'] <= 1
        assert 0 <= metrics['partial_match_rate'] <= 1
        assert 0 <= metrics['avg_expertise_relevance'] <= 1
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation(self, accuracy_validator):
        """Test comprehensive validation"""
        results = await accuracy_validator.run_comprehensive_validation()
        
        assert 'desk_rejection' in results
        assert 'referee_recommendation' in results
        
        if results['desk_rejection']:
            assert results['desk_rejection'].total_cases > 0
        
        if results['referee_recommendation']:
            assert results['referee_recommendation']['total_cases'] >= 0
    
    def test_accuracy_metrics_calculation(self, accuracy_validator):
        """Test accuracy metrics calculation"""
        predictions = ["accept", "reject", "accept", "reject", "accept"]
        actuals = ["accept", "reject", "reject", "reject", "accept"]
        
        metrics = accuracy_validator.calculate_accuracy_metrics(predictions, actuals, "Test")
        
        assert metrics.total_cases == 5
        assert metrics.correct_predictions == 4  # 4 out of 5 correct
        assert metrics.accuracy_rate == 0.8
        assert "accept" in metrics.precision_by_class
        assert "reject" in metrics.precision_by_class


# Performance thresholds for accuracy
ACCURACY_THRESHOLDS = {
    'desk_rejection_min_accuracy': 0.7,  # Minimum 70% accuracy
    'desk_rejection_min_precision': 0.6,  # Minimum 60% precision per class
    'desk_rejection_min_recall': 0.6,  # Minimum 60% recall per class
    
    'referee_exact_match_min': 0.1,  # Minimum 10% exact matches
    'referee_partial_match_min': 0.4,  # Minimum 40% partial matches
    'referee_expertise_relevance_min': 0.7,  # Minimum 70% expertise relevance
}


def check_accuracy_requirements(results: Dict[str, Any]) -> List[str]:
    """Check if accuracy meets minimum requirements"""
    issues = []
    
    # Check desk rejection accuracy
    if results.get('desk_rejection'):
        metrics = results['desk_rejection']
        
        if metrics.accuracy_rate < ACCURACY_THRESHOLDS['desk_rejection_min_accuracy']:
            issues.append(f"Desk rejection accuracy {metrics.accuracy_rate:.1%} below threshold {ACCURACY_THRESHOLDS['desk_rejection_min_accuracy']:.1%}")
        
        for class_name, precision in metrics.precision_by_class.items():
            if precision < ACCURACY_THRESHOLDS['desk_rejection_min_precision']:
                issues.append(f"Desk rejection precision for {class_name}: {precision:.1%} below threshold")
        
        for class_name, recall in metrics.recall_by_class.items():
            if recall < ACCURACY_THRESHOLDS['desk_rejection_min_recall']:
                issues.append(f"Desk rejection recall for {class_name}: {recall:.1%} below threshold")
    
    # Check referee recommendation accuracy
    if results.get('referee_recommendation'):
        metrics = results['referee_recommendation']
        
        if metrics['exact_match_rate'] < ACCURACY_THRESHOLDS['referee_exact_match_min']:
            issues.append(f"Referee exact match rate {metrics['exact_match_rate']:.1%} below threshold")
        
        if metrics['partial_match_rate'] < ACCURACY_THRESHOLDS['referee_partial_match_min']:
            issues.append(f"Referee partial match rate {metrics['partial_match_rate']:.1%} below threshold")
        
        if metrics['avg_expertise_relevance'] < ACCURACY_THRESHOLDS['referee_expertise_relevance_min']:
            issues.append(f"Referee expertise relevance {metrics['avg_expertise_relevance']:.1%} below threshold")
    
    return issues


if __name__ == "__main__":
    # Run accuracy validation directly
    async def run_validation():
        from src.ai.services.pypdf_processor import PyPDFProcessor
        
        orchestrator = AIOrchestrator(
            ai_client=MockAIClientForAccuracy(),
            pdf_processor=PyPDFProcessor(),
            cache_enabled=False
        )
        
        validator = AIAccuracyValidator(orchestrator)
        results = await validator.run_comprehensive_validation()
        
        # Check requirements
        issues = check_accuracy_requirements(results)
        if issues:
            print("\n⚠️ Accuracy Issues Detected:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ All accuracy requirements met!")
    
    asyncio.run(run_validation())