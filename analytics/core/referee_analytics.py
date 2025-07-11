"""
Core referee analytics module for comprehensive performance tracking
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path

from ..models.referee_metrics import (
    RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
    ReliabilityMetrics, ExpertiseMetrics, JournalSpecificMetrics
)

logger = logging.getLogger(__name__)


class RefereeAnalytics:
    """Comprehensive analytics for individual referee performance"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self._ensure_analytics_tables()
    
    def _ensure_analytics_tables(self):
        """Ensure analytics-specific tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create analytics cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referee_analytics_cache (
                    referee_id TEXT PRIMARY KEY,
                    metrics_json TEXT NOT NULL,
                    calculated_at TIMESTAMP NOT NULL,
                    valid_until TIMESTAMP NOT NULL
                )
            """)
            
            # Create historical metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referee_metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_id TEXT NOT NULL,
                    metric_date DATE NOT NULL,
                    overall_score REAL,
                    speed_score REAL,
                    quality_score REAL,
                    reliability_score REAL,
                    workload INTEGER,
                    UNIQUE(referee_id, metric_date)
                )
            """)
            
            conn.commit()
    
    def calculate_referee_metrics(self, referee_id: str, force_refresh: bool = False) -> RefereeMetrics:
        """Calculate comprehensive metrics for a referee"""
        # Check cache first
        if not force_refresh:
            cached_metrics = self._get_cached_metrics(referee_id)
            if cached_metrics:
                return cached_metrics
        
        # Get referee data
        referee_data = self._get_referee_data(referee_id)
        if not referee_data:
            raise ValueError(f"Referee {referee_id} not found")
        
        # Get review history
        review_history = self._get_review_history(referee_id)
        
        # Calculate metric categories
        time_metrics = self._calculate_time_metrics(review_history)
        quality_metrics = self._calculate_quality_metrics(review_history)
        workload_metrics = self._calculate_workload_metrics(referee_id, review_history)
        reliability_metrics = self._calculate_reliability_metrics(review_history)
        expertise_metrics = self._calculate_expertise_metrics(referee_id, referee_data)
        journal_metrics = self._calculate_journal_metrics(review_history)
        
        # Create metrics object
        metrics = RefereeMetrics(
            referee_id=referee_id,
            name=referee_data['name'],
            email=referee_data['email'],
            institution=referee_data['institution'] or 'Unknown',
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics,
            journal_metrics=journal_metrics
        )
        
        # Cache the metrics
        self._cache_metrics(metrics)
        
        # Store historical data point
        self._store_historical_metrics(metrics)
        
        return metrics
    
    def _calculate_time_metrics(self, review_history: List[Dict]) -> TimeMetrics:
        """Calculate time-related metrics"""
        response_times = []
        review_times = []
        on_time_count = 0
        total_completed = 0
        
        for review in review_history:
            # Response time (invitation to accept/decline)
            if review['responded_date'] and review['invited_date']:
                resp_time = (review['responded_date'] - review['invited_date']).days
                response_times.append(resp_time)
            
            # Review time (accept to submit)
            if review['submitted_date'] and review['responded_date'] and review['decision'] == 'accepted':
                rev_time = (review['submitted_date'] - review['responded_date']).days
                review_times.append(rev_time)
                total_completed += 1
                
                # Check if on time
                if review['due_date'] and review['submitted_date'] <= review['due_date']:
                    on_time_count += 1
        
        # Calculate metrics
        avg_response_time = np.mean(response_times) if response_times else 7.0
        avg_review_time = np.mean(review_times) if review_times else 21.0
        
        return TimeMetrics(
            avg_response_time=avg_response_time,
            avg_review_time=avg_review_time,
            fastest_review=min(review_times) if review_times else 0,
            slowest_review=max(review_times) if review_times else 0,
            response_time_std=np.std(response_times) if len(response_times) > 1 else 0,
            review_time_std=np.std(review_times) if len(review_times) > 1 else 0,
            on_time_rate=on_time_count / total_completed if total_completed > 0 else 1.0
        )
    
    def _calculate_quality_metrics(self, review_history: List[Dict]) -> QualityMetrics:
        """Calculate quality-related metrics"""
        quality_scores = []
        report_lengths = []
        
        for review in review_history:
            if review['quality_score'] is not None:
                quality_scores.append(review['quality_score'])
            if review['report_length']:
                report_lengths.append(review['report_length'])
        
        avg_quality = np.mean(quality_scores) if quality_scores else 7.0
        quality_std = np.std(quality_scores) if len(quality_scores) > 1 else 0
        
        # Calculate thoroughness based on report length
        avg_length = np.mean(report_lengths) if report_lengths else 1000
        thoroughness = min(1.0, avg_length / 2000)  # Normalize to 2000 words
        
        return QualityMetrics(
            avg_quality_score=avg_quality,
            quality_consistency=quality_std,
            report_thoroughness=thoroughness,
            constructiveness_score=avg_quality * 0.9,  # Placeholder - would use NLP
            technical_accuracy=avg_quality * 0.95,  # Placeholder
            clarity_score=8.0,  # Placeholder
            actionability_score=7.5  # Placeholder
        )
    
    def _calculate_workload_metrics(self, referee_id: str, review_history: List[Dict]) -> WorkloadMetrics:
        """Calculate workload and capacity metrics"""
        now = datetime.now()
        
        # Count current active reviews
        current_reviews = self._count_active_reviews(referee_id)
        
        # Count completed reviews by period
        completed_30d = sum(1 for r in review_history 
                           if r['submitted_date'] and 
                           (now - r['submitted_date']).days <= 30)
        completed_90d = sum(1 for r in review_history 
                           if r['submitted_date'] and 
                           (now - r['submitted_date']).days <= 90)
        completed_365d = sum(1 for r in review_history 
                            if r['submitted_date'] and 
                            (now - r['submitted_date']).days <= 365)
        
        # Calculate monthly average
        months_active = len(set((r['invited_date'].year, r['invited_date'].month) 
                               for r in review_history if r['invited_date']))
        monthly_avg = len(review_history) / max(months_active, 1)
        
        # Find peak concurrent reviews
        peak_capacity = self._calculate_peak_capacity(review_history)
        
        # Calculate availability score (inverse of current load)
        availability = max(0, 1 - (current_reviews / max(peak_capacity, 3)))
        
        # Calculate burnout risk
        burnout_risk = self._calculate_burnout_risk(
            current_reviews, completed_30d, monthly_avg
        )
        
        return WorkloadMetrics(
            current_reviews=current_reviews,
            completed_reviews_30d=completed_30d,
            completed_reviews_90d=completed_90d,
            completed_reviews_365d=completed_365d,
            monthly_average=monthly_avg,
            peak_capacity=peak_capacity,
            availability_score=availability,
            burnout_risk_score=burnout_risk
        )
    
    def _calculate_reliability_metrics(self, review_history: List[Dict]) -> ReliabilityMetrics:
        """Calculate reliability and communication metrics"""
        total_invitations = len(review_history)
        accepted = sum(1 for r in review_history if r['decision'] == 'accepted')
        declined = sum(1 for r in review_history if r['decision'] == 'declined')
        no_response = sum(1 for r in review_history if r['decision'] is None)
        
        # Count completed reviews
        completed = sum(1 for r in review_history 
                       if r['decision'] == 'accepted' and r['submitted_date'] is not None)
        
        # Count withdrawals
        withdrawals = sum(1 for r in review_history 
                         if r['decision'] == 'accepted' and r['submitted_date'] is None)
        
        # Calculate reminder effectiveness
        responded_after_reminder = sum(1 for r in review_history 
                                     if r['reminder_count'] > 0 and r['decision'] is not None)
        total_reminders_sent = sum(1 for r in review_history if r['reminder_count'] > 0)
        
        return ReliabilityMetrics(
            acceptance_rate=accepted / total_invitations if total_invitations > 0 else 0,
            completion_rate=completed / accepted if accepted > 0 else 1.0,
            ghost_rate=no_response / total_invitations if total_invitations > 0 else 0,
            decline_after_accept_rate=withdrawals / accepted if accepted > 0 else 0,
            reminder_effectiveness=responded_after_reminder / total_reminders_sent 
                                 if total_reminders_sent > 0 else 1.0,
            communication_score=0.8,  # Placeholder
            excuse_frequency=0.1  # Placeholder
        )
    
    def _calculate_expertise_metrics(self, referee_id: str, referee_data: Dict) -> ExpertiseMetrics:
        """Calculate expertise-related metrics"""
        # Get expertise from database
        expertise = self._get_referee_expertise(referee_id)
        
        # Parse expertise data
        expertise_areas = list(expertise.keys())
        expertise_confidence = {area: data['confidence'] 
                              for area, data in expertise.items()}
        
        # Count reviewed topics
        reviewed_topics = self._get_reviewed_topics(referee_id)
        
        # Calculate breadth and depth
        breadth = len(expertise_areas) / 10  # Normalize to 10 areas
        depth = np.mean(list(expertise_confidence.values())) if expertise_confidence else 0
        
        return ExpertiseMetrics(
            expertise_areas=expertise_areas,
            expertise_confidence=expertise_confidence,
            h_index=referee_data.get('h_index'),
            recent_publications=0,  # Would need external data
            citation_count=0,  # Would need external data
            years_experience=self._estimate_years_experience(referee_data),
            reviewed_topics=reviewed_topics,
            expertise_breadth=min(1.0, breadth),
            expertise_depth=depth
        )
    
    def _calculate_journal_metrics(self, review_history: List[Dict]) -> Dict[str, JournalSpecificMetrics]:
        """Calculate journal-specific metrics"""
        journal_metrics = {}
        
        # Group reviews by journal
        journal_reviews = {}
        for review in review_history:
            journal = review.get('journal_id', 'unknown')
            if journal not in journal_reviews:
                journal_reviews[journal] = []
            journal_reviews[journal].append(review)
        
        # Calculate metrics for each journal
        for journal_id, reviews in journal_reviews.items():
            completed = [r for r in reviews if r['submitted_date'] is not None]
            accepted = [r for r in reviews if r['decision'] == 'accepted']
            
            quality_scores = [r['quality_score'] for r in completed 
                            if r['quality_score'] is not None]
            review_times = [(r['submitted_date'] - r['responded_date']).days 
                           for r in completed if r['responded_date'] and r['submitted_date']]
            
            metrics = JournalSpecificMetrics(
                journal_id=journal_id,
                reviews_completed=len(completed),
                acceptance_rate=len(accepted) / len(reviews) if reviews else 0,
                avg_quality_score=np.mean(quality_scores) if quality_scores else 0,
                avg_review_time=np.mean(review_times) if review_times else 21,
                familiarity_score=min(1.0, len(completed) / 10)  # Normalize to 10 reviews
            )
            
            journal_metrics[journal_id] = metrics
        
        return journal_metrics
    
    def _get_referee_data(self, referee_id: str) -> Optional[Dict]:
        """Get referee basic data from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, email, institution, expertise, h_index, created_at
                FROM referees
                WHERE id = ?
            """, (referee_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'name': row[0],
                    'email': row[1],
                    'institution': row[2],
                    'expertise': row[3],
                    'h_index': row[4],
                    'created_at': row[5]
                }
            return None
    
    def _get_review_history(self, referee_id: str) -> List[Dict]:
        """Get complete review history for a referee"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rh.*,
                    m.journal AS journal_id
                FROM review_history rh
                LEFT JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE rh.referee_id = ?
                ORDER BY rh.invited_date DESC
            """, (referee_id,))
            
            reviews = []
            for row in cursor.fetchall():
                review = dict(row)
                # Convert date strings to datetime objects
                for date_field in ['invited_date', 'responded_date', 'due_date', 'submitted_date']:
                    if review[date_field]:
                        try:
                            review[date_field] = datetime.fromisoformat(review[date_field])
                        except:
                            review[date_field] = None
                reviews.append(review)
            
            return reviews
    
    def _count_active_reviews(self, referee_id: str) -> int:
        """Count currently active reviews"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NULL
            """, (referee_id,))
            
            return cursor.fetchone()[0]
    
    def _calculate_peak_capacity(self, review_history: List[Dict]) -> int:
        """Calculate maximum concurrent reviews handled"""
        if not review_history:
            return 0
        
        # Create timeline of review start/end events
        events = []
        for review in review_history:
            if review['decision'] == 'accepted' and review['responded_date']:
                events.append((review['responded_date'], 1))  # Start
                if review['submitted_date']:
                    events.append((review['submitted_date'], -1))  # End
                else:
                    # Assume 30 days if not submitted
                    events.append((review['responded_date'] + timedelta(days=30), -1))
        
        # Sort events by date
        events.sort(key=lambda x: x[0])
        
        # Find peak concurrent reviews
        current_load = 0
        peak_load = 0
        for date, change in events:
            current_load += change
            peak_load = max(peak_load, current_load)
        
        return peak_load
    
    def _calculate_burnout_risk(self, current_reviews: int, recent_completed: int, 
                               monthly_avg: float) -> float:
        """Calculate burnout risk score"""
        # Factors contributing to burnout
        workload_factor = min(1.0, current_reviews / 5)  # 5+ reviews is high
        
        # Recent completion rate vs average
        if monthly_avg > 0:
            pace_factor = min(1.0, recent_completed / monthly_avg)
        else:
            pace_factor = 0.5
        
        # Combine factors
        burnout_risk = (workload_factor * 0.6 + pace_factor * 0.4)
        
        return burnout_risk
    
    def _get_referee_expertise(self, referee_id: str) -> Dict:
        """Get referee expertise areas with confidence scores"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT expertise_area, confidence_score, evidence_count
                FROM referee_expertise
                WHERE referee_id = ?
                ORDER BY confidence_score DESC
            """, (referee_id,))
            
            expertise = {}
            for row in cursor.fetchall():
                expertise[row[0]] = {
                    'confidence': row[1],
                    'evidence_count': row[2]
                }
            
            return expertise
    
    def _get_reviewed_topics(self, referee_id: str) -> Dict[str, int]:
        """Get topics reviewed by referee with counts"""
        # This would ideally extract topics from manuscript metadata
        # For now, return placeholder data
        return {
            "optimization": 5,
            "machine_learning": 3,
            "control_theory": 2
        }
    
    def _estimate_years_experience(self, referee_data: Dict) -> int:
        """Estimate years of experience based on available data"""
        if referee_data.get('created_at'):
            try:
                created = datetime.fromisoformat(referee_data['created_at'])
                return (datetime.now() - created).days // 365
            except:
                pass
        return 5  # Default estimate
    
    def _get_cached_metrics(self, referee_id: str) -> Optional[RefereeMetrics]:
        """Retrieve cached metrics if still valid"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metrics_json, valid_until
                FROM referee_analytics_cache
                WHERE referee_id = ?
            """, (referee_id,))
            
            row = cursor.fetchone()
            if row and datetime.fromisoformat(row[1]) > datetime.now():
                # Parse and return cached metrics
                import json
                metrics_dict = json.loads(row[0])
                # Would need to reconstruct RefereeMetrics object
                return None  # Placeholder
        
        return None
    
    def _cache_metrics(self, metrics: RefereeMetrics):
        """Cache calculated metrics"""
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Cache for 24 hours
            valid_until = datetime.now() + timedelta(hours=24)
            
            cursor.execute("""
                INSERT OR REPLACE INTO referee_analytics_cache
                (referee_id, metrics_json, calculated_at, valid_until)
                VALUES (?, ?, ?, ?)
            """, (
                metrics.referee_id,
                json.dumps(metrics.to_dict()),
                datetime.now().isoformat(),
                valid_until.isoformat()
            ))
            
            conn.commit()
    
    def _store_historical_metrics(self, metrics: RefereeMetrics):
        """Store daily historical metrics for trend analysis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO referee_metrics_history
                (referee_id, metric_date, overall_score, speed_score, 
                 quality_score, reliability_score, workload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.referee_id,
                datetime.now().date().isoformat(),
                metrics.get_overall_score(),
                1 - (metrics.time_metrics.avg_review_time / 30),
                metrics.quality_metrics.get_overall_quality() / 10,
                metrics.reliability_metrics.get_reliability_score(),
                metrics.workload_metrics.current_reviews
            ))
            
            conn.commit()
    
    def get_referee_trends(self, referee_id: str, days: int = 90) -> Dict:
        """Get historical trends for a referee"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            cursor.execute("""
                SELECT *
                FROM referee_metrics_history
                WHERE referee_id = ?
                AND metric_date >= ?
                ORDER BY metric_date
            """, (referee_id, start_date.isoformat()))
            
            history = [dict(row) for row in cursor.fetchall()]
            
            if not history:
                return {'error': 'No historical data available'}
            
            # Extract trend data
            dates = [h['metric_date'] for h in history]
            overall_scores = [h['overall_score'] for h in history]
            
            return {
                'dates': dates,
                'overall_scores': overall_scores,
                'speed_scores': [h['speed_score'] for h in history],
                'quality_scores': [h['quality_score'] for h in history],
                'reliability_scores': [h['reliability_score'] for h in history],
                'workload': [h['workload'] for h in history],
                'trend_direction': self._calculate_trend_direction(overall_scores)
            }
    
    def _calculate_trend_direction(self, scores: List[float]) -> str:
        """Calculate trend direction from scores"""
        if len(scores) < 2:
            return "insufficient_data"
        
        # Simple linear regression
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        
        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"