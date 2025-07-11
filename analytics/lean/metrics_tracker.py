"""
Lean metrics tracking system for editorial process optimization
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of lean metrics"""
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    SPEED = "speed"
    WASTE = "waste"
    VALUE_ADD = "value_add"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


@dataclass
class LeanMetric:
    """Individual lean metric"""
    name: str
    value: float
    target: float
    unit: str
    metric_type: MetricType
    trend: str  # 'improving', 'declining', 'stable'
    last_updated: datetime
    
    @property
    def performance_ratio(self) -> float:
        """Calculate performance vs target ratio"""
        if self.target == 0:
            return 1.0
        return self.value / self.target
    
    @property
    def status(self) -> str:
        """Get status based on performance"""
        ratio = self.performance_ratio
        if ratio >= 1.0:
            return "on_target"
        elif ratio >= 0.8:
            return "near_target"
        else:
            return "below_target"


@dataclass
class ValueStreamMetrics:
    """Metrics for value stream analysis"""
    total_time: float  # Total process time
    value_added_time: float  # Time spent on value-adding activities
    waste_time: float  # Time spent on waste
    efficiency_ratio: float  # Value-added / Total time
    bottlenecks: List[str]  # Identified bottlenecks
    cycle_time: float  # Average cycle time
    lead_time: float  # Total lead time


class LeanMetricsTracker:
    """Track and analyze lean metrics for editorial processes"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self._ensure_lean_tables()
    
    def _ensure_lean_tables(self):
        """Ensure lean metrics tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create lean metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lean_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    target_value REAL,
                    unit TEXT,
                    metric_type TEXT,
                    journal_id TEXT,
                    measured_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create process timeline table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manuscript_id TEXT NOT NULL,
                    journal_id TEXT,
                    process_step TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    is_value_added BOOLEAN DEFAULT FALSE,
                    step_owner TEXT,
                    notes TEXT
                )
            """)
            
            # Create bottleneck tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bottleneck_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_name TEXT NOT NULL,
                    bottleneck_step TEXT NOT NULL,
                    impact_score REAL,
                    frequency INTEGER,
                    avg_delay_days REAL,
                    identified_date DATE,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            conn.commit()
    
    def calculate_cycle_time_metrics(self, journal_id: Optional[str] = None, 
                                   days: int = 90) -> Dict:
        """Calculate cycle time metrics for editorial process"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Base query for manuscripts in time period
            base_query = """
                SELECT 
                    m.id,
                    m.journal,
                    m.submitted_date,
                    m.decision_date,
                    m.status,
                    julianday(m.decision_date) - julianday(m.submitted_date) as total_days
                FROM manuscripts m
                WHERE m.submitted_date >= date('now', '-{} days')
            """.format(days)
            
            if journal_id:
                base_query += " AND m.journal = ?"
                params = (journal_id,)
            else:
                params = ()
            
            cursor.execute(base_query + " ORDER BY m.submitted_date", params)
            manuscripts = cursor.fetchall()
        
        if not manuscripts:
            return {'error': 'No manuscripts found for the specified period'}
        
        # Calculate metrics
        total_times = [m[5] for m in manuscripts if m[5] is not None]
        
        metrics = {
            'total_manuscripts': len(manuscripts),
            'completed_manuscripts': len(total_times),
            'avg_cycle_time': np.mean(total_times) if total_times else 0,
            'median_cycle_time': np.median(total_times) if total_times else 0,
            'min_cycle_time': np.min(total_times) if total_times else 0,
            'max_cycle_time': np.max(total_times) if total_times else 0,
            'std_cycle_time': np.std(total_times) if total_times else 0,
            'percentiles': {
                '25th': np.percentile(total_times, 25) if total_times else 0,
                '75th': np.percentile(total_times, 75) if total_times else 0,
                '90th': np.percentile(total_times, 90) if total_times else 0
            }
        }
        
        # Calculate trend
        if len(total_times) >= 10:
            recent_half = total_times[-len(total_times)//2:]
            early_half = total_times[:len(total_times)//2]
            
            recent_avg = np.mean(recent_half)
            early_avg = np.mean(early_half)
            
            if recent_avg < early_avg * 0.9:
                metrics['trend'] = 'improving'
            elif recent_avg > early_avg * 1.1:
                metrics['trend'] = 'declining'
            else:
                metrics['trend'] = 'stable'
        else:
            metrics['trend'] = 'insufficient_data'
        
        return metrics
    
    def analyze_value_stream(self, journal_id: str) -> ValueStreamMetrics:
        """Analyze value stream for a specific journal"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get process timeline data
            cursor.execute("""
                SELECT 
                    pt.manuscript_id,
                    pt.process_step,
                    pt.start_time,
                    pt.end_time,
                    pt.is_value_added
                FROM process_timeline pt
                WHERE pt.journal_id = ?
                AND pt.end_time IS NOT NULL
                ORDER BY pt.manuscript_id, pt.start_time
            """, (journal_id,))
            
            timeline_data = cursor.fetchall()
        
        if not timeline_data:
            # Create default analysis based on review history
            return self._create_default_value_stream(journal_id)
        
        # Analyze timeline data
        manuscript_times = {}
        
        for row in timeline_data:
            manuscript_id = row[0]
            if manuscript_id not in manuscript_times:
                manuscript_times[manuscript_id] = {
                    'total_time': 0,
                    'value_added_time': 0,
                    'waste_time': 0,
                    'steps': []
                }
            
            # Calculate step duration
            start_time = datetime.fromisoformat(row[2])
            end_time = datetime.fromisoformat(row[3])
            duration = (end_time - start_time).total_seconds() / (24 * 3600)  # Days
            
            manuscript_times[manuscript_id]['total_time'] += duration
            manuscript_times[manuscript_id]['steps'].append(row[1])
            
            if row[4]:  # is_value_added
                manuscript_times[manuscript_id]['value_added_time'] += duration
            else:
                manuscript_times[manuscript_id]['waste_time'] += duration
        
        # Calculate aggregate metrics
        total_times = [m['total_time'] for m in manuscript_times.values()]
        value_added_times = [m['value_added_time'] for m in manuscript_times.values()]
        waste_times = [m['waste_time'] for m in manuscript_times.values()]
        
        avg_total_time = np.mean(total_times) if total_times else 0
        avg_value_added_time = np.mean(value_added_times) if value_added_times else 0
        avg_waste_time = np.mean(waste_times) if waste_times else 0
        
        efficiency_ratio = avg_value_added_time / avg_total_time if avg_total_time > 0 else 0
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(journal_id)
        
        return ValueStreamMetrics(
            total_time=avg_total_time,
            value_added_time=avg_value_added_time,
            waste_time=avg_waste_time,
            efficiency_ratio=efficiency_ratio,
            bottlenecks=bottlenecks,
            cycle_time=avg_total_time,
            lead_time=avg_total_time  # Simplified
        )
    
    def _create_default_value_stream(self, journal_id: str) -> ValueStreamMetrics:
        """Create default value stream analysis from review data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get review timeline data
            cursor.execute("""
                SELECT 
                    rh.manuscript_id,
                    rh.invited_date,
                    rh.responded_date,
                    rh.due_date,
                    rh.submitted_date,
                    rh.decision
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE m.journal = ?
                AND rh.invited_date >= date('now', '-90 days')
            """, (journal_id,))
            
            reviews = cursor.fetchall()
        
        if not reviews:
            return ValueStreamMetrics(0, 0, 0, 0, [], 0, 0)
        
        # Analyze review process times
        total_times = []
        value_added_times = []
        waste_times = []
        
        for review in reviews:
            if review[4] and review[1]:  # submitted_date and invited_date
                total_time = (datetime.fromisoformat(review[4]) - 
                            datetime.fromisoformat(review[1])).days
                
                # Assume 70% is value-added (actual review work)
                value_added = total_time * 0.7
                waste = total_time * 0.3
                
                total_times.append(total_time)
                value_added_times.append(value_added)
                waste_times.append(waste)
        
        avg_total = np.mean(total_times) if total_times else 0
        avg_value = np.mean(value_added_times) if value_added_times else 0
        avg_waste = np.mean(waste_times) if waste_times else 0
        
        efficiency = avg_value / avg_total if avg_total > 0 else 0
        
        return ValueStreamMetrics(
            total_time=avg_total,
            value_added_time=avg_value,
            waste_time=avg_waste,
            efficiency_ratio=efficiency,
            bottlenecks=[],
            cycle_time=avg_total,
            lead_time=avg_total
        )
    
    def _identify_bottlenecks(self, journal_id: str) -> List[str]:
        """Identify process bottlenecks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Look for steps that take longer than average
            cursor.execute("""
                SELECT 
                    process_step,
                    AVG(julianday(end_time) - julianday(start_time)) as avg_duration,
                    COUNT(*) as frequency
                FROM process_timeline
                WHERE journal_id = ?
                AND end_time IS NOT NULL
                GROUP BY process_step
                HAVING frequency >= 5
                ORDER BY avg_duration DESC
            """, (journal_id,))
            
            bottlenecks = []
            results = cursor.fetchall()
            
            if results:
                avg_durations = [r[1] for r in results]
                overall_avg = np.mean(avg_durations)
                
                for step, duration, freq in results:
                    if duration > overall_avg * 1.5:  # 50% longer than average
                        bottlenecks.append(step)
        
        return bottlenecks
    
    def calculate_automation_metrics(self) -> Dict:
        """Calculate automation and efficiency metrics"""
        # Define automatable processes
        automatable_processes = [
            'manuscript_intake',
            'initial_screening',
            'referee_selection',
            'reminder_sending',
            'status_tracking',
            'report_generation'
        ]
        
        # For each process, calculate automation rate
        automation_metrics = {}
        
        for process in automatable_processes:
            # This would be configured based on actual implementation
            # For now, use estimated values
            automation_metrics[process] = {
                'total_instances': 100,
                'automated_instances': 45,  # Example
                'automation_rate': 0.45,
                'time_saved_per_instance': 30,  # minutes
                'total_time_saved': 1350  # minutes
            }
        
        overall_automation_rate = np.mean([m['automation_rate'] for m in automation_metrics.values()])
        total_time_saved = sum(m['total_time_saved'] for m in automation_metrics.values())
        
        return {
            'overall_automation_rate': overall_automation_rate,
            'total_time_saved_minutes': total_time_saved,
            'process_breakdown': automation_metrics,
            'automation_opportunities': self._identify_automation_opportunities()
        }
    
    def _identify_automation_opportunities(self) -> List[Dict]:
        """Identify opportunities for further automation"""
        opportunities = [
            {
                'process': 'Manuscript quality screening',
                'current_automation': 0.20,
                'potential_automation': 0.85,
                'estimated_savings_hours_per_month': 40,
                'implementation_effort': 'medium',
                'roi_score': 8.5
            },
            {
                'process': 'Referee matching',
                'current_automation': 0.30,
                'potential_automation': 0.90,
                'estimated_savings_hours_per_month': 60,
                'implementation_effort': 'high',
                'roi_score': 9.2
            },
            {
                'process': 'Follow-up reminders',
                'current_automation': 0.70,
                'potential_automation': 0.95,
                'estimated_savings_hours_per_month': 15,
                'implementation_effort': 'low',
                'roi_score': 7.8
            }
        ]
        
        return sorted(opportunities, key=lambda x: x['roi_score'], reverse=True)
    
    def calculate_quality_metrics(self, journal_id: Optional[str] = None) -> Dict:
        """Calculate quality-related lean metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Base queries
            if journal_id:
                journal_filter = "WHERE m.journal = ?"
                params = (journal_id,)
            else:
                journal_filter = ""
                params = ()
            
            # First-time quality rate
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN m.revision_count = 0 THEN 1 ELSE 0 END) as first_time_quality
                FROM manuscripts m
                {journal_filter}
                AND m.submitted_date >= date('now', '-90 days')
            """, params)
            
            quality_result = cursor.fetchone()
            total_manuscripts = quality_result[0] or 0
            first_time_quality = quality_result[1] or 0
            
            first_time_quality_rate = first_time_quality / total_manuscripts if total_manuscripts > 0 else 0
            
            # Review quality scores
            cursor.execute(f"""
                SELECT AVG(rh.quality_score)
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                {journal_filter.replace('m.journal', 'm.journal')}
                AND rh.quality_score IS NOT NULL
                AND rh.submitted_date >= date('now', '-90 days')
            """, params)
            
            avg_review_quality = cursor.fetchone()[0] or 0
            
            # Decision consistency (reviews aligning with final decision)
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_reviews,
                    SUM(CASE 
                        WHEN (rh.recommendation LIKE '%accept%' AND m.decision = 'accepted') OR
                             (rh.recommendation LIKE '%reject%' AND m.decision = 'rejected')
                        THEN 1 ELSE 0 
                    END) as aligned_reviews
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                {journal_filter}
                AND rh.recommendation IS NOT NULL
                AND m.decision IS NOT NULL
                AND rh.submitted_date >= date('now', '-90 days')
            """, params)
            
            consistency_result = cursor.fetchone()
            total_reviews = consistency_result[0] or 0
            aligned_reviews = consistency_result[1] or 0
            
            decision_consistency = aligned_reviews / total_reviews if total_reviews > 0 else 0
        
        return {
            'first_time_quality_rate': first_time_quality_rate,
            'avg_review_quality_score': avg_review_quality,
            'decision_consistency_rate': decision_consistency,
            'quality_trend': self._calculate_quality_trend(journal_id),
            'defect_rate': 1 - first_time_quality_rate,  # Inverse of first-time quality
            'target_quality_rate': 0.85,  # Target 85% first-time quality
            'quality_improvement_opportunities': self._identify_quality_improvements()
        }
    
    def _calculate_quality_trend(self, journal_id: Optional[str]) -> str:
        """Calculate trend in quality metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get quality scores over time
            if journal_id:
                cursor.execute("""
                    SELECT 
                        DATE(rh.submitted_date) as date,
                        AVG(rh.quality_score) as avg_quality
                    FROM review_history rh
                    JOIN manuscripts m ON rh.manuscript_id = m.id
                    WHERE m.journal = ?
                    AND rh.quality_score IS NOT NULL
                    AND rh.submitted_date >= date('now', '-90 days')
                    GROUP BY DATE(rh.submitted_date)
                    ORDER BY date
                """, (journal_id,))
            else:
                cursor.execute("""
                    SELECT 
                        DATE(submitted_date) as date,
                        AVG(quality_score) as avg_quality
                    FROM review_history
                    WHERE quality_score IS NOT NULL
                    AND submitted_date >= date('now', '-90 days')
                    GROUP BY DATE(submitted_date)
                    ORDER BY date
                """)
            
            quality_data = cursor.fetchall()
        
        if len(quality_data) < 10:
            return 'insufficient_data'
        
        # Calculate trend using linear regression
        quality_scores = [d[1] for d in quality_data]
        x = np.arange(len(quality_scores))
        slope = np.polyfit(x, quality_scores, 1)[0]
        
        if slope > 0.05:
            return 'improving'
        elif slope < -0.05:
            return 'declining'
        else:
            return 'stable'
    
    def _identify_quality_improvements(self) -> List[str]:
        """Identify opportunities for quality improvement"""
        improvements = [
            "Implement automated quality checks before review assignment",
            "Provide referee training materials and guidelines",
            "Create review templates for consistency",
            "Implement peer review of reviewer reports",
            "Add quality feedback loop from editors to reviewers"
        ]
        
        return improvements
    
    def calculate_customer_satisfaction_metrics(self) -> Dict:
        """Calculate customer (author/referee) satisfaction metrics"""
        # This would ideally be based on surveys and feedback
        # For now, use proxy metrics
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Response time satisfaction (based on meeting deadlines)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN submitted_date <= due_date THEN 1 ELSE 0 END) as on_time
                FROM review_history
                WHERE submitted_date IS NOT NULL
                AND due_date IS NOT NULL
                AND invited_date >= date('now', '-90 days')
            """)
            
            timing_result = cursor.fetchone()
            total_reviews = timing_result[0] or 0
            on_time_reviews = timing_result[1] or 0
            
            timing_satisfaction = on_time_reviews / total_reviews if total_reviews > 0 else 0
            
            # Communication satisfaction (based on response rates)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_invites,
                    SUM(CASE WHEN decision IS NOT NULL THEN 1 ELSE 0 END) as responded
                FROM review_history
                WHERE invited_date >= date('now', '-90 days')
            """)
            
            comm_result = cursor.fetchone()
            total_invites = comm_result[0] or 0
            responded = comm_result[1] or 0
            
            communication_satisfaction = responded / total_invites if total_invites > 0 else 0
        
        # Overall satisfaction (weighted combination)
        overall_satisfaction = (timing_satisfaction * 0.6 + communication_satisfaction * 0.4)
        
        return {
            'overall_satisfaction_score': overall_satisfaction,
            'timing_satisfaction': timing_satisfaction,
            'communication_satisfaction': communication_satisfaction,
            'target_satisfaction': 0.85,
            'satisfaction_trend': 'stable',  # Would calculate from historical data
            'improvement_actions': [
                "Implement proactive deadline management",
                "Improve invitation response tracking",
                "Add satisfaction surveys for authors and referees",
                "Create feedback mechanism for process improvements"
            ]
        }
    
    def store_metric(self, metric_name: str, value: float, target: Optional[float] = None,
                    unit: str = "", metric_type: MetricType = MetricType.EFFICIENCY,
                    journal_id: Optional[str] = None):
        """Store a lean metric in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO lean_metrics 
                (metric_name, metric_value, target_value, unit, metric_type, journal_id, measured_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_name, value, target, unit, metric_type.value, 
                journal_id, datetime.now().date()
            ))
            
            conn.commit()
    
    def get_kpi_dashboard(self, journal_id: Optional[str] = None) -> Dict:
        """Get comprehensive KPI dashboard"""
        cycle_time = self.calculate_cycle_time_metrics(journal_id)
        automation = self.calculate_automation_metrics()
        quality = self.calculate_quality_metrics(journal_id)
        satisfaction = self.calculate_customer_satisfaction_metrics()
        
        if journal_id:
            value_stream = self.analyze_value_stream(journal_id)
        else:
            value_stream = None
        
        # Calculate overall performance score
        key_metrics = [
            ('cycle_time', cycle_time.get('avg_cycle_time', 60), 45, False),  # Lower is better
            ('automation_rate', automation['overall_automation_rate'], 0.8, True),  # Higher is better
            ('quality_rate', quality['first_time_quality_rate'], 0.85, True),
            ('satisfaction', satisfaction['overall_satisfaction_score'], 0.85, True)
        ]
        
        performance_scores = []
        for name, value, target, higher_better in key_metrics:
            if higher_better:
                score = min(1.0, value / target) if target > 0 else 0
            else:
                score = min(1.0, target / value) if value > 0 else 0
            performance_scores.append(score)
        
        overall_performance = np.mean(performance_scores) * 100
        
        return {
            'overall_performance_score': overall_performance,
            'cycle_time_metrics': cycle_time,
            'automation_metrics': automation,
            'quality_metrics': quality,
            'satisfaction_metrics': satisfaction,
            'value_stream_metrics': value_stream.__dict__ if value_stream else None,
            'key_performance_indicators': {
                'cycle_time_days': cycle_time.get('avg_cycle_time', 0),
                'automation_rate_pct': automation['overall_automation_rate'] * 100,
                'first_time_quality_pct': quality['first_time_quality_rate'] * 100,
                'customer_satisfaction_pct': satisfaction['overall_satisfaction_score'] * 100
            },
            'improvement_priorities': self._get_improvement_priorities(
                cycle_time, automation, quality, satisfaction
            )
        }
    
    def _get_improvement_priorities(self, cycle_time: Dict, automation: Dict, 
                                  quality: Dict, satisfaction: Dict) -> List[Dict]:
        """Identify top improvement priorities"""
        priorities = []
        
        # Cycle time
        if cycle_time.get('avg_cycle_time', 0) > 60:
            priorities.append({
                'area': 'Cycle Time',
                'current': cycle_time.get('avg_cycle_time', 0),
                'target': 45,
                'impact': 'high',
                'actions': ['Identify bottlenecks', 'Automate screening', 'Parallel processing']
            })
        
        # Automation
        if automation['overall_automation_rate'] < 0.7:
            priorities.append({
                'area': 'Automation',
                'current': automation['overall_automation_rate'],
                'target': 0.8,
                'impact': 'high',
                'actions': ['Implement AI screening', 'Automate reminders', 'Smart routing']
            })
        
        # Quality
        if quality['first_time_quality_rate'] < 0.8:
            priorities.append({
                'area': 'Quality',
                'current': quality['first_time_quality_rate'],
                'target': 0.85,
                'impact': 'medium',
                'actions': ['Reviewer training', 'Quality templates', 'Feedback loops']
            })
        
        return sorted(priorities, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['impact']], reverse=True)