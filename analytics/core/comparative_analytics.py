"""
Comparative analytics for benchmarking referees against peers
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
import sqlite3
from pathlib import Path
from collections import defaultdict

from ..models.referee_metrics import RefereeMetrics, PercentileRanks, PerformanceTier
from .referee_analytics import RefereeAnalytics

logger = logging.getLogger(__name__)


class ComparativeRefereeAnalytics:
    """Compare referees against benchmarks and peers"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self.analytics = RefereeAnalytics(db_path)
        self._ensure_benchmark_tables()
    
    def _ensure_benchmark_tables(self):
        """Ensure benchmark and comparison tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create benchmark metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referee_benchmarks (
                    category TEXT PRIMARY KEY,
                    metrics_json TEXT NOT NULL,
                    sample_size INTEGER,
                    updated_at TIMESTAMP
                )
            """)
            
            # Create peer groups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referee_peer_groups (
                    referee_id TEXT PRIMARY KEY,
                    peer_group TEXT NOT NULL,
                    expertise_cluster TEXT,
                    performance_tier TEXT,
                    updated_at TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def calculate_percentile_ranks(self, referee_id: str) -> PercentileRanks:
        """Calculate percentile rankings for a referee across all dimensions"""
        # Get referee metrics
        referee_metrics = self.analytics.calculate_referee_metrics(referee_id)
        
        # Get all referee metrics for comparison
        all_metrics = self._get_all_referee_metrics()
        
        # Calculate percentiles
        speed_percentile = self._calculate_speed_percentile(
            referee_metrics.time_metrics.avg_review_time, 
            [m.time_metrics.avg_review_time for m in all_metrics]
        )
        
        quality_percentile = self._calculate_percentile(
            referee_metrics.quality_metrics.get_overall_quality(),
            [m.quality_metrics.get_overall_quality() for m in all_metrics]
        )
        
        reliability_percentile = self._calculate_percentile(
            referee_metrics.reliability_metrics.get_reliability_score(),
            [m.reliability_metrics.get_reliability_score() for m in all_metrics]
        )
        
        expertise_percentile = self._calculate_percentile(
            referee_metrics.expertise_metrics.get_expertise_score(),
            [m.expertise_metrics.get_expertise_score() for m in all_metrics]
        )
        
        overall_percentile = self._calculate_percentile(
            referee_metrics.get_overall_score(),
            [m.get_overall_score() for m in all_metrics]
        )
        
        return PercentileRanks(
            speed_percentile=speed_percentile,
            quality_percentile=quality_percentile,
            reliability_percentile=reliability_percentile,
            expertise_percentile=expertise_percentile,
            overall_percentile=overall_percentile
        )
    
    def get_peer_comparison(self, referee_id: str) -> Dict:
        """Compare referee against peers in same field and experience level"""
        referee_metrics = self.analytics.calculate_referee_metrics(referee_id)
        
        # Find comparable peers
        peers = self._find_comparable_peers(referee_id, referee_metrics)
        
        # Calculate peer averages
        peer_metrics = [self.analytics.calculate_referee_metrics(p) for p in peers]
        
        # Calculate field averages
        field_avg = self._calculate_field_average(referee_metrics.expertise_metrics.expertise_areas)
        
        # Calculate journal averages
        journal_avg = self._calculate_journal_average(list(referee_metrics.journal_metrics.keys()))
        
        return {
            'referee_metrics': referee_metrics.to_dict(),
            'peer_average': self._calculate_metrics_average(peer_metrics),
            'field_average': field_avg,
            'journal_average': journal_avg,
            'peer_count': len(peers),
            'comparison_insights': self._generate_comparison_insights(
                referee_metrics, peer_metrics, field_avg, journal_avg
            )
        }
    
    def get_performance_distribution(self, metric_type: str = 'overall') -> Dict:
        """Get performance distribution across all referees"""
        all_metrics = self._get_all_referee_metrics()
        
        if metric_type == 'overall':
            scores = [m.get_overall_score() for m in all_metrics]
        elif metric_type == 'speed':
            scores = [30 - m.time_metrics.avg_review_time for m in all_metrics]
        elif metric_type == 'quality':
            scores = [m.quality_metrics.get_overall_quality() for m in all_metrics]
        elif metric_type == 'reliability':
            scores = [m.reliability_metrics.get_reliability_score() * 10 for m in all_metrics]
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")
        
        # Calculate distribution statistics
        return {
            'mean': np.mean(scores),
            'median': np.median(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'percentiles': {
                '10th': np.percentile(scores, 10),
                '25th': np.percentile(scores, 25),
                '50th': np.percentile(scores, 50),
                '75th': np.percentile(scores, 75),
                '90th': np.percentile(scores, 90)
            },
            'distribution': self._create_histogram(scores)
        }
    
    def identify_top_performers(self, limit: int = 10, category: Optional[str] = None) -> List[Dict]:
        """Identify top performing referees overall or by category"""
        all_metrics = self._get_all_referee_metrics()
        
        # Sort by relevant metric
        if category == 'speed':
            sorted_metrics = sorted(all_metrics, 
                                  key=lambda m: m.time_metrics.avg_review_time)
        elif category == 'quality':
            sorted_metrics = sorted(all_metrics, 
                                  key=lambda m: m.quality_metrics.get_overall_quality(), 
                                  reverse=True)
        elif category == 'reliability':
            sorted_metrics = sorted(all_metrics, 
                                  key=lambda m: m.reliability_metrics.get_reliability_score(), 
                                  reverse=True)
        else:
            sorted_metrics = sorted(all_metrics, 
                                  key=lambda m: m.get_overall_score(), 
                                  reverse=True)
        
        # Return top performers
        top_performers = []
        for i, metrics in enumerate(sorted_metrics[:limit]):
            percentile_ranks = self.calculate_percentile_ranks(metrics.referee_id)
            
            top_performers.append({
                'rank': i + 1,
                'referee_id': metrics.referee_id,
                'name': metrics.name,
                'institution': metrics.institution,
                'overall_score': metrics.get_overall_score(),
                'category_score': self._get_category_score(metrics, category),
                'percentile_ranks': {
                    'overall': percentile_ranks.overall_percentile,
                    'speed': percentile_ranks.speed_percentile,
                    'quality': percentile_ranks.quality_percentile,
                    'reliability': percentile_ranks.reliability_percentile
                },
                'performance_tier': percentile_ranks.get_performance_tier().value,
                'key_strengths': self._identify_key_strengths(metrics)
            })
        
        return top_performers
    
    def benchmark_by_journal(self, journal_id: str) -> Dict:
        """Get benchmark metrics for a specific journal"""
        # Get all referees who have reviewed for this journal
        journal_referees = self._get_journal_referees(journal_id)
        
        # Calculate metrics for each
        metrics_list = []
        for referee_id in journal_referees:
            try:
                metrics = self.analytics.calculate_referee_metrics(referee_id)
                if journal_id in metrics.journal_metrics:
                    metrics_list.append(metrics)
            except Exception as e:
                logger.warning(f"Error calculating metrics for referee {referee_id}: {e}")
        
        if not metrics_list:
            return {'error': 'No data available for this journal'}
        
        # Calculate benchmark statistics
        return {
            'journal_id': journal_id,
            'referee_count': len(metrics_list),
            'benchmarks': {
                'avg_acceptance_rate': np.mean([m.journal_metrics[journal_id].acceptance_rate 
                                               for m in metrics_list]),
                'avg_review_time': np.mean([m.journal_metrics[journal_id].avg_review_time 
                                           for m in metrics_list]),
                'avg_quality_score': np.mean([m.journal_metrics[journal_id].avg_quality_score 
                                             for m in metrics_list]),
                'avg_familiarity': np.mean([m.journal_metrics[journal_id].familiarity_score 
                                           for m in metrics_list])
            },
            'top_performers': self._get_journal_top_performers(metrics_list, journal_id)[:5],
            'performance_distribution': self._get_journal_performance_distribution(metrics_list, journal_id)
        }
    
    def benchmark_by_expertise(self, expertise_area: str) -> Dict:
        """Get benchmark metrics for referees with specific expertise"""
        # Get all referees with this expertise
        expertise_referees = self._get_expertise_referees(expertise_area)
        
        # Calculate metrics
        metrics_list = []
        for referee_id in expertise_referees:
            try:
                metrics = self.analytics.calculate_referee_metrics(referee_id)
                if expertise_area in metrics.expertise_metrics.expertise_areas:
                    metrics_list.append(metrics)
            except Exception as e:
                logger.warning(f"Error calculating metrics for referee {referee_id}: {e}")
        
        if not metrics_list:
            return {'error': 'No data available for this expertise area'}
        
        return {
            'expertise_area': expertise_area,
            'referee_count': len(metrics_list),
            'benchmarks': {
                'avg_overall_score': np.mean([m.get_overall_score() for m in metrics_list]),
                'avg_review_time': np.mean([m.time_metrics.avg_review_time for m in metrics_list]),
                'avg_quality_score': np.mean([m.quality_metrics.get_overall_quality() for m in metrics_list]),
                'avg_acceptance_rate': np.mean([m.reliability_metrics.acceptance_rate for m in metrics_list]),
                'avg_h_index': np.mean([m.expertise_metrics.h_index or 0 for m in metrics_list])
            },
            'top_experts': self._get_expertise_top_performers(metrics_list, expertise_area)[:5],
            'expertise_confidence_distribution': self._get_expertise_confidence_distribution(
                metrics_list, expertise_area
            )
        }
    
    def _calculate_percentile(self, value: float, all_values: List[float]) -> float:
        """Calculate percentile rank for a value"""
        if not all_values:
            return 50.0
        
        # Count values less than the given value
        less_than = sum(1 for v in all_values if v < value)
        equal_to = sum(1 for v in all_values if v == value)
        
        # Calculate percentile
        percentile = (less_than + 0.5 * equal_to) / len(all_values) * 100
        
        return round(percentile, 1)
    
    def _calculate_speed_percentile(self, review_time: float, all_times: List[float]) -> float:
        """Calculate speed percentile (lower time = higher percentile)"""
        if not all_times:
            return 50.0
        
        # For speed, lower is better, so we count values greater than
        greater_than = sum(1 for t in all_times if t > review_time)
        equal_to = sum(1 for t in all_times if t == review_time)
        
        percentile = (greater_than + 0.5 * equal_to) / len(all_times) * 100
        
        return round(percentile, 1)
    
    def _get_all_referee_metrics(self) -> List[RefereeMetrics]:
        """Get metrics for all referees"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM referees WHERE active = 1")
            referee_ids = [row[0] for row in cursor.fetchall()]
        
        metrics_list = []
        for referee_id in referee_ids:
            try:
                metrics = self.analytics.calculate_referee_metrics(referee_id)
                metrics_list.append(metrics)
            except Exception as e:
                logger.warning(f"Error calculating metrics for referee {referee_id}: {e}")
        
        return metrics_list
    
    def _find_comparable_peers(self, referee_id: str, referee_metrics: RefereeMetrics) -> List[str]:
        """Find referees with similar expertise and experience"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get referees with overlapping expertise
            expertise_areas = referee_metrics.expertise_metrics.expertise_areas
            if not expertise_areas:
                return []
            
            # Build query for expertise overlap
            placeholders = ','.join(['?' for _ in expertise_areas])
            query = f"""
                SELECT DISTINCT r.id
                FROM referees r
                JOIN referee_expertise re ON r.id = re.referee_id
                WHERE re.expertise_area IN ({placeholders})
                AND r.id != ?
                AND r.active = 1
                GROUP BY r.id
                HAVING COUNT(DISTINCT re.expertise_area) >= ?
            """
            
            # Find peers with at least 50% expertise overlap
            min_overlap = max(1, len(expertise_areas) // 2)
            cursor.execute(query, expertise_areas + [referee_id, min_overlap])
            
            peer_ids = [row[0] for row in cursor.fetchall()]
            
            # Further filter by experience level
            filtered_peers = []
            for peer_id in peer_ids[:20]:  # Limit to 20 for performance
                try:
                    peer_metrics = self.analytics.calculate_referee_metrics(peer_id)
                    # Similar experience level (within 50%)
                    exp_ratio = (peer_metrics.expertise_metrics.years_experience / 
                               max(referee_metrics.expertise_metrics.years_experience, 1))
                    if 0.5 <= exp_ratio <= 2.0:
                        filtered_peers.append(peer_id)
                except:
                    continue
            
            return filtered_peers
    
    def _calculate_metrics_average(self, metrics_list: List[RefereeMetrics]) -> Dict:
        """Calculate average metrics from a list of referee metrics"""
        if not metrics_list:
            return {}
        
        return {
            'overall_score': np.mean([m.get_overall_score() for m in metrics_list]),
            'time_metrics': {
                'avg_response_time': np.mean([m.time_metrics.avg_response_time for m in metrics_list]),
                'avg_review_time': np.mean([m.time_metrics.avg_review_time for m in metrics_list]),
                'on_time_rate': np.mean([m.time_metrics.on_time_rate for m in metrics_list])
            },
            'quality_metrics': {
                'avg_quality_score': np.mean([m.quality_metrics.avg_quality_score for m in metrics_list]),
                'report_thoroughness': np.mean([m.quality_metrics.report_thoroughness for m in metrics_list])
            },
            'reliability_metrics': {
                'acceptance_rate': np.mean([m.reliability_metrics.acceptance_rate for m in metrics_list]),
                'completion_rate': np.mean([m.reliability_metrics.completion_rate for m in metrics_list]),
                'ghost_rate': np.mean([m.reliability_metrics.ghost_rate for m in metrics_list])
            },
            'workload_metrics': {
                'monthly_average': np.mean([m.workload_metrics.monthly_average for m in metrics_list]),
                'current_reviews': np.mean([m.workload_metrics.current_reviews for m in metrics_list])
            }
        }
    
    def _calculate_field_average(self, expertise_areas: List[str]) -> Dict:
        """Calculate average metrics for referees in the same field"""
        if not expertise_areas:
            return {}
        
        # Get cached field benchmarks
        field_key = '_'.join(sorted(expertise_areas[:3]))  # Use top 3 areas
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metrics_json
                FROM referee_benchmarks
                WHERE category = ?
            """, (f"field_{field_key}",))
            
            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row[0])
        
        # Calculate if not cached
        field_referees = set()
        for area in expertise_areas:
            field_referees.update(self._get_expertise_referees(area))
        
        field_metrics = []
        for referee_id in list(field_referees)[:50]:  # Limit for performance
            try:
                metrics = self.analytics.calculate_referee_metrics(referee_id)
                field_metrics.append(metrics)
            except:
                continue
        
        if field_metrics:
            avg = self._calculate_metrics_average(field_metrics)
            self._cache_benchmark(f"field_{field_key}", avg)
            return avg
        
        return {}
    
    def _calculate_journal_average(self, journal_ids: List[str]) -> Dict:
        """Calculate average metrics for referees who review for the same journals"""
        if not journal_ids:
            return {}
        
        # Get the most reviewed journal
        primary_journal = journal_ids[0] if journal_ids else None
        if not primary_journal:
            return {}
        
        return self.benchmark_by_journal(primary_journal).get('benchmarks', {})
    
    def _generate_comparison_insights(self, referee_metrics: RefereeMetrics, 
                                    peer_metrics: List[RefereeMetrics],
                                    field_avg: Dict, journal_avg: Dict) -> List[str]:
        """Generate insights from comparison data"""
        insights = []
        
        # Compare to peers
        if peer_metrics:
            peer_avg_score = np.mean([m.get_overall_score() for m in peer_metrics])
            if referee_metrics.get_overall_score() > peer_avg_score * 1.2:
                insights.append("Performing significantly above peer average")
            elif referee_metrics.get_overall_score() < peer_avg_score * 0.8:
                insights.append("Performance below peer average - consider improvement areas")
        
        # Speed insights
        if field_avg.get('time_metrics'):
            field_review_time = field_avg['time_metrics'].get('avg_review_time', 21)
            if referee_metrics.time_metrics.avg_review_time < field_review_time * 0.8:
                insights.append("Exceptionally fast reviewer compared to field average")
            elif referee_metrics.time_metrics.avg_review_time > field_review_time * 1.5:
                insights.append("Review times significantly longer than field average")
        
        # Quality insights
        if referee_metrics.quality_metrics.quality_consistency < 1.0:
            insights.append("Highly consistent review quality")
        elif referee_metrics.quality_metrics.quality_consistency > 2.0:
            insights.append("Review quality varies significantly - aim for more consistency")
        
        # Workload insights
        if referee_metrics.workload_metrics.burnout_risk_score > 0.7:
            insights.append("High burnout risk detected - consider reducing workload")
        
        # Expertise insights
        if referee_metrics.expertise_metrics.expertise_breadth > 0.7:
            insights.append("Broad expertise across multiple areas")
        elif referee_metrics.expertise_metrics.expertise_depth > 0.8:
            insights.append("Deep specialization in core expertise areas")
        
        return insights
    
    def _create_histogram(self, scores: List[float], bins: int = 10) -> Dict:
        """Create histogram data for score distribution"""
        hist, bin_edges = np.histogram(scores, bins=bins)
        
        return {
            'bins': [(bin_edges[i], bin_edges[i+1]) for i in range(len(bin_edges)-1)],
            'counts': hist.tolist(),
            'frequencies': (hist / len(scores)).tolist()
        }
    
    def _get_category_score(self, metrics: RefereeMetrics, category: Optional[str]) -> float:
        """Get score for specific category"""
        if category == 'speed':
            return 30 - metrics.time_metrics.avg_review_time  # Invert for higher = better
        elif category == 'quality':
            return metrics.quality_metrics.get_overall_quality()
        elif category == 'reliability':
            return metrics.reliability_metrics.get_reliability_score() * 10
        else:
            return metrics.get_overall_score()
    
    def _identify_key_strengths(self, metrics: RefereeMetrics) -> List[str]:
        """Identify key strengths of a referee"""
        strengths = []
        
        # Check each dimension
        if metrics.time_metrics.avg_review_time < 14:
            strengths.append("Fast reviewer")
        
        if metrics.quality_metrics.get_overall_quality() > 8.5:
            strengths.append("Exceptional review quality")
        
        if metrics.reliability_metrics.get_reliability_score() > 0.9:
            strengths.append("Highly reliable")
        
        if metrics.expertise_metrics.h_index and metrics.expertise_metrics.h_index > 30:
            strengths.append("Leading expert in field")
        
        if metrics.workload_metrics.monthly_average > 3:
            strengths.append("High volume contributor")
        
        return strengths
    
    def _get_journal_referees(self, journal_id: str) -> List[str]:
        """Get all referees who have reviewed for a journal"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT r.referee_id
                FROM review_history r
                JOIN manuscripts m ON r.manuscript_id = m.id
                WHERE m.journal = ?
            """, (journal_id,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def _get_expertise_referees(self, expertise_area: str) -> List[str]:
        """Get all referees with specific expertise"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT referee_id
                FROM referee_expertise
                WHERE expertise_area = ?
                AND confidence_score > 0.5
            """, (expertise_area,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def _get_journal_top_performers(self, metrics_list: List[RefereeMetrics], 
                                   journal_id: str) -> List[Dict]:
        """Get top performers for a specific journal"""
        # Sort by journal-specific performance
        sorted_metrics = sorted(
            metrics_list,
            key=lambda m: (
                m.journal_metrics[journal_id].avg_quality_score * 0.5 +
                (1 / max(m.journal_metrics[journal_id].avg_review_time, 1)) * 30 * 0.3 +
                m.journal_metrics[journal_id].familiarity_score * 0.2
            ),
            reverse=True
        )
        
        top_performers = []
        for metrics in sorted_metrics[:5]:
            journal_metrics = metrics.journal_metrics[journal_id]
            top_performers.append({
                'referee_id': metrics.referee_id,
                'name': metrics.name,
                'reviews_completed': journal_metrics.reviews_completed,
                'avg_quality_score': journal_metrics.avg_quality_score,
                'avg_review_time': journal_metrics.avg_review_time,
                'acceptance_rate': journal_metrics.acceptance_rate
            })
        
        return top_performers
    
    def _get_journal_performance_distribution(self, metrics_list: List[RefereeMetrics], 
                                            journal_id: str) -> Dict:
        """Get performance distribution for journal-specific metrics"""
        quality_scores = [m.journal_metrics[journal_id].avg_quality_score for m in metrics_list]
        review_times = [m.journal_metrics[journal_id].avg_review_time for m in metrics_list]
        
        return {
            'quality_distribution': self._create_histogram(quality_scores, bins=5),
            'review_time_distribution': self._create_histogram(review_times, bins=5)
        }
    
    def _get_expertise_top_performers(self, metrics_list: List[RefereeMetrics], 
                                    expertise_area: str) -> List[Dict]:
        """Get top performers in specific expertise area"""
        # Sort by expertise confidence and overall performance
        sorted_metrics = sorted(
            metrics_list,
            key=lambda m: (
                m.expertise_metrics.expertise_confidence.get(expertise_area, 0) * 0.3 +
                m.get_overall_score() / 10 * 0.7
            ),
            reverse=True
        )
        
        top_performers = []
        for metrics in sorted_metrics[:5]:
            top_performers.append({
                'referee_id': metrics.referee_id,
                'name': metrics.name,
                'institution': metrics.institution,
                'expertise_confidence': metrics.expertise_metrics.expertise_confidence.get(expertise_area, 0),
                'overall_score': metrics.get_overall_score(),
                'h_index': metrics.expertise_metrics.h_index
            })
        
        return top_performers
    
    def _get_expertise_confidence_distribution(self, metrics_list: List[RefereeMetrics], 
                                             expertise_area: str) -> Dict:
        """Get distribution of expertise confidence scores"""
        confidence_scores = [
            m.expertise_metrics.expertise_confidence.get(expertise_area, 0) 
            for m in metrics_list
        ]
        
        return self._create_histogram(confidence_scores, bins=5)
    
    def _cache_benchmark(self, category: str, metrics: Dict):
        """Cache benchmark metrics"""
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO referee_benchmarks
                (category, metrics_json, sample_size, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                category,
                json.dumps(metrics),
                len(metrics.get('sample_ids', [])),
                datetime.now().isoformat()
            ))
            
            conn.commit()