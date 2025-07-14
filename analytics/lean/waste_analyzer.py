"""
Waste Analyzer - Identifies and quantifies process waste in editorial workflows
Following Lean Six Sigma principles
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class WasteType(Enum):
    """Types of waste in editorial processes (TIMWOOD)"""
    TRANSPORTATION = "transportation"  # Unnecessary manuscript movement
    INVENTORY = "inventory"  # Manuscripts waiting in queues
    MOTION = "motion"  # Unnecessary actions/clicks
    WAITING = "waiting"  # Idle time between process steps
    OVERPRODUCTION = "overproduction"  # Excessive reviews/reports
    OVERPROCESSING = "overprocessing"  # Redundant quality checks
    DEFECTS = "defects"  # Errors requiring rework


@dataclass
class WasteMetric:
    """Individual waste measurement"""
    waste_type: WasteType
    value: float
    unit: str
    description: str
    impact_score: float  # 0-100 severity
    timestamp: datetime = field(default_factory=datetime.now)
    
    
@dataclass
class WasteAnalysisResult:
    """Complete waste analysis for a process"""
    process_name: str
    total_waste_score: float
    waste_metrics: List[WasteMetric]
    efficiency_ratio: float  # Value-added time / Total time
    recommendations: List[str]
    potential_savings_hours: float
    analysis_timestamp: datetime = field(default_factory=datetime.now)


class WasteAnalyzer:
    """
    Analyzes editorial processes to identify and quantify waste
    """
    
    def __init__(self):
        self.waste_thresholds = {
            WasteType.WAITING: 48,  # hours
            WasteType.INVENTORY: 10,  # manuscripts
            WasteType.MOTION: 5,  # extra steps
            WasteType.DEFECTS: 0.05,  # 5% error rate
            WasteType.OVERPROCESSING: 3,  # redundant reviews
        }
        
    def analyze_referee_workflow(
        self, 
        workflow_data: Dict[str, any]
    ) -> WasteAnalysisResult:
        """
        Analyze referee assignment workflow for waste
        """
        waste_metrics = []
        
        # Analyze waiting time
        if 'average_assignment_time' in workflow_data:
            wait_time = workflow_data['average_assignment_time']
            if wait_time > self.waste_thresholds[WasteType.WAITING]:
                waste_metrics.append(WasteMetric(
                    waste_type=WasteType.WAITING,
                    value=wait_time - self.waste_thresholds[WasteType.WAITING],
                    unit="hours",
                    description="Excessive time to assign referees",
                    impact_score=min(80, wait_time)
                ))
        
        # Analyze inventory (manuscripts in queue)
        if 'manuscripts_in_queue' in workflow_data:
            queue_size = workflow_data['manuscripts_in_queue']
            if queue_size > self.waste_thresholds[WasteType.INVENTORY]:
                waste_metrics.append(WasteMetric(
                    waste_type=WasteType.INVENTORY,
                    value=queue_size,
                    unit="manuscripts",
                    description="Too many manuscripts waiting for review",
                    impact_score=min(90, queue_size * 5)
                ))
        
        # Analyze defects (declined invitations)
        if 'invitation_decline_rate' in workflow_data:
            decline_rate = workflow_data['invitation_decline_rate']
            if decline_rate > self.waste_thresholds[WasteType.DEFECTS]:
                waste_metrics.append(WasteMetric(
                    waste_type=WasteType.DEFECTS,
                    value=decline_rate * 100,
                    unit="percent",
                    description="High referee invitation decline rate",
                    impact_score=decline_rate * 100
                ))
        
        # Calculate overall metrics
        total_waste_score = sum(m.impact_score for m in waste_metrics) / len(waste_metrics) if waste_metrics else 0
        efficiency_ratio = self._calculate_efficiency_ratio(workflow_data)
        recommendations = self._generate_recommendations(waste_metrics)
        potential_savings = self._estimate_savings(waste_metrics)
        
        return WasteAnalysisResult(
            process_name="Referee Assignment Workflow",
            total_waste_score=total_waste_score,
            waste_metrics=waste_metrics,
            efficiency_ratio=efficiency_ratio,
            recommendations=recommendations,
            potential_savings_hours=potential_savings,
            analysis_timestamp=datetime.now()
        )
    
    def analyze_review_process(
        self,
        review_data: Dict[str, any]
    ) -> WasteAnalysisResult:
        """
        Analyze review process for waste
        """
        waste_metrics = []
        
        # Analyze overprocessing (multiple reviews for desk rejections)
        if 'unnecessary_reviews' in review_data:
            extra_reviews = review_data['unnecessary_reviews']
            if extra_reviews > 0:
                waste_metrics.append(WasteMetric(
                    waste_type=WasteType.OVERPROCESSING,
                    value=extra_reviews,
                    unit="reviews",
                    description="Reviews conducted for manuscripts that should have been desk rejected",
                    impact_score=extra_reviews * 20
                ))
        
        # Analyze motion waste (unnecessary steps)
        if 'redundant_actions' in review_data:
            redundant = review_data['redundant_actions']
            if redundant > self.waste_thresholds[WasteType.MOTION]:
                waste_metrics.append(WasteMetric(
                    waste_type=WasteType.MOTION,
                    value=redundant,
                    unit="actions",
                    description="Redundant actions in review process",
                    impact_score=redundant * 10
                ))
        
        # Generate analysis result
        total_waste_score = sum(m.impact_score for m in waste_metrics) / len(waste_metrics) if waste_metrics else 0
        
        return WasteAnalysisResult(
            process_name="Peer Review Process",
            total_waste_score=total_waste_score,
            waste_metrics=waste_metrics,
            efficiency_ratio=self._calculate_efficiency_ratio(review_data),
            recommendations=self._generate_recommendations(waste_metrics),
            potential_savings_hours=self._estimate_savings(waste_metrics),
            analysis_timestamp=datetime.now()
        )
    
    def _calculate_efficiency_ratio(self, process_data: Dict) -> float:
        """Calculate value-added time ratio"""
        if 'value_added_time' in process_data and 'total_time' in process_data:
            return process_data['value_added_time'] / process_data['total_time']
        return 0.5  # Default assumption
    
    def _generate_recommendations(self, waste_metrics: List[WasteMetric]) -> List[str]:
        """Generate improvement recommendations based on waste analysis"""
        recommendations = []
        
        for metric in waste_metrics:
            if metric.waste_type == WasteType.WAITING:
                recommendations.append(
                    f"Implement automated referee suggestion to reduce assignment time by {metric.value:.0f} hours"
                )
            elif metric.waste_type == WasteType.INVENTORY:
                recommendations.append(
                    f"Increase editorial capacity or streamline desk rejection to reduce queue by {metric.value:.0f} manuscripts"
                )
            elif metric.waste_type == WasteType.DEFECTS:
                recommendations.append(
                    f"Improve referee matching algorithm to reduce decline rate by {metric.value:.1f}%"
                )
            elif metric.waste_type == WasteType.OVERPROCESSING:
                recommendations.append(
                    f"Implement AI-powered desk rejection to avoid {metric.value:.0f} unnecessary reviews"
                )
            elif metric.waste_type == WasteType.MOTION:
                recommendations.append(
                    f"Streamline workflow to eliminate {metric.value:.0f} redundant steps"
                )
                
        return recommendations
    
    def _estimate_savings(self, waste_metrics: List[WasteMetric]) -> float:
        """Estimate potential time savings in hours"""
        total_savings = 0.0
        
        for metric in waste_metrics:
            if metric.waste_type == WasteType.WAITING:
                total_savings += metric.value * 0.8  # 80% of wait time can be eliminated
            elif metric.waste_type == WasteType.OVERPROCESSING:
                total_savings += metric.value * 20  # 20 hours per unnecessary review
            elif metric.waste_type == WasteType.MOTION:
                total_savings += metric.value * 0.5  # 30 minutes per redundant action
                
        return total_savings
    
    def compare_journal_efficiency(
        self,
        journal_data: Dict[str, Dict]
    ) -> Dict[str, float]:
        """
        Compare waste levels across multiple journals
        """
        journal_scores = {}
        
        for journal_code, data in journal_data.items():
            result = self.analyze_referee_workflow(data)
            journal_scores[journal_code] = {
                'waste_score': result.total_waste_score,
                'efficiency_ratio': result.efficiency_ratio,
                'potential_savings': result.potential_savings_hours
            }
            
        return journal_scores
    
    def generate_waste_report(
        self,
        analysis_results: List[WasteAnalysisResult]
    ) -> str:
        """
        Generate comprehensive waste analysis report
        """
        report = "# Waste Analysis Report\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for result in analysis_results:
            report += f"## {result.process_name}\n\n"
            report += f"**Total Waste Score**: {result.total_waste_score:.1f}/100\n"
            report += f"**Efficiency Ratio**: {result.efficiency_ratio:.2%}\n"
            report += f"**Potential Savings**: {result.potential_savings_hours:.1f} hours\n\n"
            
            if result.waste_metrics:
                report += "### Identified Waste\n\n"
                for metric in result.waste_metrics:
                    report += f"- **{metric.waste_type.value.title()}**: "
                    report += f"{metric.value:.1f} {metric.unit} - {metric.description}\n"
                
                report += "\n### Recommendations\n\n"
                for rec in result.recommendations:
                    report += f"- {rec}\n"
            
            report += "\n---\n\n"
            
        return report