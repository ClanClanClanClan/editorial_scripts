"""
Predictive model for review timeline estimation
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


class TimelinePredictor:
    """Predict review completion timelines"""
    
    def __init__(self, db_path: str = "data/referees.db", model_path: str = "models/"):
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        self.timeline_model = None
        self.risk_model = None
        self.scaler = StandardScaler()
        
        self._load_or_train_models()
    
    def predict_review_timeline(self, referee_id: str, current_workload: int, 
                              manuscript_data: Dict) -> Dict:
        """Predict review completion timeline"""
        # Extract features
        features = self._extract_features(referee_id, current_workload, manuscript_data)
        
        if self.timeline_model is None:
            return {
                'expected_days': 21.0,
                'confidence_interval': (14.0, 28.0),
                'confidence_level': 0.0,
                'risk_factors': ['Model not trained'],
                'optimization_suggestions': []
            }
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Predict timeline
        expected_days = self.timeline_model.predict(features_scaled)[0]
        
        # Calculate confidence interval
        if hasattr(self.timeline_model, 'estimators_'):
            # For ensemble methods, use individual estimator predictions
            predictions = [est.predict(features_scaled)[0] 
                          for est in self.timeline_model.estimators_]
            lower_bound = np.percentile(predictions, 10)
            upper_bound = np.percentile(predictions, 90)
            confidence_std = np.std(predictions)
        else:
            # Simple interval based on historical variance
            confidence_std = 5.0
            lower_bound = max(1, expected_days - 2 * confidence_std)
            upper_bound = expected_days + 2 * confidence_std
        
        # Identify risk factors
        risk_factors = self._identify_delay_risks(features, expected_days)
        
        # Generate optimization suggestions
        suggestions = self._generate_timeline_optimizations(
            referee_id, features, expected_days
        )
        
        return {
            'expected_days': float(max(1, expected_days)),
            'confidence_interval': (float(lower_bound), float(upper_bound)),
            'confidence_level': self._calculate_confidence_level(confidence_std),
            'risk_factors': risk_factors,
            'optimization_suggestions': suggestions
        }
    
    def predict_deadline_compliance(self, referee_id: str, deadline_days: int) -> Dict:
        """Predict probability of meeting a specific deadline"""
        # Get historical compliance data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE 
                        WHEN julianday(submitted_date) - julianday(responded_date) <= ? 
                        THEN 1 ELSE 0 
                    END) as on_time
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NOT NULL
            """, (deadline_days, referee_id))
            
            result = cursor.fetchone()
            total = result[0] or 0
            on_time = result[1] or 0
        
        if total == 0:
            base_probability = 0.7  # Default
        else:
            base_probability = on_time / total
        
        # Adjust based on current conditions
        current_workload = self._get_current_workload(referee_id)
        
        # Workload penalty
        if current_workload > 3:
            probability = base_probability * 0.8
        elif current_workload > 5:
            probability = base_probability * 0.6
        else:
            probability = base_probability
        
        return {
            'compliance_probability': float(probability),
            'historical_rate': float(base_probability),
            'current_workload_impact': float(probability / max(base_probability, 0.01)),
            'recommendation': self._get_deadline_recommendation(probability, deadline_days)
        }
    
    def _extract_features(self, referee_id: str, current_workload: int, 
                         manuscript_data: Dict) -> List[float]:
        """Extract features for timeline prediction"""
        features = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get historical review times
            cursor.execute("""
                SELECT 
                    AVG(julianday(submitted_date) - julianday(responded_date)) as avg_time,
                    MIN(julianday(submitted_date) - julianday(responded_date)) as min_time,
                    MAX(julianday(submitted_date) - julianday(responded_date)) as max_time,
                    COUNT(*) as completed_reviews
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NOT NULL
            """, (referee_id,))
            
            stats = cursor.fetchone()
            avg_time = stats[0] or 21
            min_time = stats[1] or 7
            max_time = stats[2] or 42
            completed_reviews = stats[3] or 0
            
            # Get recent performance trend
            cursor.execute("""
                SELECT julianday(submitted_date) - julianday(responded_date) as review_time
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NOT NULL
                ORDER BY submitted_date DESC
                LIMIT 5
            """, (referee_id,))
            
            recent_times = [row[0] for row in cursor.fetchall()]
            
            # Calculate trend
            if len(recent_times) >= 2:
                trend = (recent_times[0] - recent_times[-1]) / len(recent_times)
            else:
                trend = 0
            
            # Get journal-specific average
            journal_id = manuscript_data.get('journal_id')
            if journal_id:
                cursor.execute("""
                    SELECT AVG(julianday(submitted_date) - julianday(responded_date))
                    FROM review_history rh
                    JOIN manuscripts m ON rh.manuscript_id = m.id
                    WHERE rh.referee_id = ?
                    AND m.journal = ?
                    AND rh.decision = 'accepted'
                    AND rh.submitted_date IS NOT NULL
                """, (referee_id, journal_id))
                
                journal_avg = cursor.fetchone()[0] or avg_time
            else:
                journal_avg = avg_time
        
        # Build feature vector
        features.extend([
            # Historical performance
            avg_time,
            min_time,
            max_time,
            max_time - min_time,  # Variability
            
            # Recent trend
            trend,
            recent_times[0] if recent_times else avg_time,  # Most recent time
            
            # Workload factors
            current_workload,
            current_workload ** 2,  # Non-linear workload effect
            
            # Experience
            completed_reviews,
            min(1.0, completed_reviews / 50),  # Experience factor
            
            # Journal-specific
            journal_avg,
            journal_avg / max(avg_time, 1),  # Journal difficulty ratio
            
            # Manuscript factors
            manuscript_data.get('complexity_score', 0.5),
            manuscript_data.get('revision_round', 0),
            manuscript_data.get('page_count', 20) / 20,  # Normalized pages
            
            # Time of year
            datetime.now().month,
            1 if datetime.now().month in [7, 8, 12] else 0,  # Holiday season
            
            # Expertise match
            manuscript_data.get('expertise_match', 0.5)
        ])
        
        return features
    
    def _load_or_train_models(self):
        """Load existing models or train new ones"""
        timeline_model_path = self.model_path / "timeline_model.pkl"
        timeline_scaler_path = self.model_path / "timeline_scaler.pkl"
        
        if timeline_model_path.exists() and timeline_scaler_path.exists():
            self.timeline_model = joblib.load(timeline_model_path)
            self.scaler = joblib.load(timeline_scaler_path)
            logger.info("Loaded existing timeline prediction model")
        else:
            logger.info("Training new timeline prediction model")
            self._train_models()
    
    def _train_models(self):
        """Train timeline prediction model"""
        # Prepare training data
        X, y = self._prepare_training_data()
        
        if len(X) < 50:
            logger.warning("Insufficient data for timeline model training")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.timeline_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        self.timeline_model.fit(X_scaled, y)
        
        # Evaluate using cross-validation
        from sklearn.model_selection import cross_val_score
        scores = cross_val_score(self.timeline_model, X_scaled, y, cv=5, 
                               scoring='neg_mean_absolute_error')
        
        logger.info(f"Timeline model MAE: {-scores.mean():.2f} days")
        
        # Save models
        joblib.dump(self.timeline_model, self.model_path / "timeline_model.pkl")
        joblib.dump(self.scaler, self.model_path / "timeline_scaler.pkl")
    
    def _prepare_training_data(self) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data from historical reviews"""
        X = []
        y = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get completed reviews with timing data
            cursor.execute("""
                SELECT 
                    rh.*,
                    m.journal,
                    m.page_count,
                    julianday(rh.submitted_date) - julianday(rh.responded_date) as actual_days
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE rh.decision = 'accepted'
                AND rh.submitted_date IS NOT NULL
                AND rh.responded_date IS NOT NULL
                ORDER BY rh.submitted_date DESC
                LIMIT 5000
            """)
            
            reviews = cursor.fetchall()
            
            for review in reviews:
                # Get workload at time of review
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM review_history
                    WHERE referee_id = ?
                    AND decision = 'accepted'
                    AND responded_date <= ?
                    AND (submitted_date IS NULL OR submitted_date >= ?)
                """, (review['referee_id'], review['responded_date'], review['responded_date']))
                
                workload = cursor.fetchone()[0]
                
                # Create manuscript data
                manuscript_data = {
                    'journal_id': review['journal'],
                    'page_count': review['page_count'] or 20,
                    'complexity_score': 0.5,  # Default
                    'revision_round': 0,  # Default
                    'expertise_match': 0.7  # Default
                }
                
                # Extract features
                features = self._extract_features(
                    review['referee_id'], 
                    workload, 
                    manuscript_data
                )
                
                X.append(features)
                y.append(review['actual_days'])
        
        return X, y
    
    def _identify_delay_risks(self, features: List[float], expected_days: float) -> List[str]:
        """Identify factors that might cause delays"""
        risks = []
        
        # High workload
        if features[6] > 3:  # current_workload
            risks.append(f"High current workload ({int(features[6])} active reviews)")
        
        # High variability
        if features[3] > 20:  # max_time - min_time
            risks.append("High historical variability in review times")
        
        # Negative trend
        if features[4] > 2:  # trend
            risks.append("Recent reviews taking longer than average")
        
        # Complex manuscript
        if features[12] > 0.7:  # complexity_score
            risks.append("Complex manuscript may require more time")
        
        # Holiday season
        if features[16] == 1:  # holiday season
            risks.append("Holiday season may cause delays")
        
        # Low expertise match
        if features[17] < 0.3:  # expertise_match
            risks.append("Limited expertise match may slow review")
        
        # Expected time already high
        if expected_days > 28:
            risks.append("Already expecting longer than typical review time")
        
        return risks
    
    def _generate_timeline_optimizations(self, referee_id: str, features: List[float], 
                                       expected_days: float) -> List[str]:
        """Generate suggestions to optimize timeline"""
        suggestions = []
        
        # Workload management
        if features[6] > 3:  # current_workload
            suggestions.append("Consider declining if workload is too high")
            suggestions.append("Prioritize reviews by deadline to manage workload")
        
        # Early start
        if expected_days > 21:
            suggestions.append("Start review early to allow buffer time")
        
        # Break down task
        if features[14] > 1.5:  # page_count normalized
            suggestions.append("Break review into sections for long manuscripts")
        
        # Use templates
        if features[8] < 10:  # completed_reviews
            suggestions.append("Use review templates to streamline process")
        
        # Time blocking
        suggestions.append("Block dedicated time slots for review completion")
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _calculate_confidence_level(self, std_dev: float) -> float:
        """Calculate confidence level based on prediction variance"""
        # Lower std deviation = higher confidence
        # Normalize to 0-1 scale
        max_std = 10.0  # Maximum expected standard deviation
        confidence = max(0, 1 - (std_dev / max_std))
        return float(confidence)
    
    def _get_current_workload(self, referee_id: str) -> int:
        """Get current active review count"""
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
    
    def _get_deadline_recommendation(self, probability: float, deadline_days: int) -> str:
        """Generate recommendation based on compliance probability"""
        if probability > 0.8:
            return f"High confidence in meeting {deadline_days}-day deadline"
        elif probability > 0.6:
            return f"Moderate confidence - consider buffer time for {deadline_days}-day deadline"
        elif probability > 0.4:
            return f"Low confidence - consider extending deadline beyond {deadline_days} days"
        else:
            return f"Very low confidence - strongly recommend alternative referee or extended deadline"
    
    def analyze_timeline_factors(self, referee_id: str) -> Dict:
        """Analyze factors affecting referee's review timelines"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get review time by various factors
            cursor.execute("""
                SELECT 
                    m.journal,
                    AVG(julianday(rh.submitted_date) - julianday(rh.responded_date)) as avg_time,
                    COUNT(*) as count
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE rh.referee_id = ?
                AND rh.decision = 'accepted'
                AND rh.submitted_date IS NOT NULL
                GROUP BY m.journal
                HAVING count >= 3
            """, (referee_id,))
            
            journal_times = {row[0]: {'avg_time': row[1], 'count': row[2]} 
                           for row in cursor.fetchall()}
            
            # Get review time by month
            cursor.execute("""
                SELECT 
                    strftime('%m', responded_date) as month,
                    AVG(julianday(submitted_date) - julianday(responded_date)) as avg_time
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NOT NULL
                GROUP BY month
            """, (referee_id,))
            
            monthly_times = {int(row[0]): row[1] for row in cursor.fetchall()}
            
            # Get workload impact
            cursor.execute("""
                WITH WorkloadReviews AS (
                    SELECT 
                        rh1.id,
                        julianday(rh1.submitted_date) - julianday(rh1.responded_date) as review_time,
                        (
                            SELECT COUNT(*)
                            FROM review_history rh2
                            WHERE rh2.referee_id = rh1.referee_id
                            AND rh2.decision = 'accepted'
                            AND rh2.responded_date <= rh1.responded_date
                            AND (rh2.submitted_date IS NULL OR rh2.submitted_date >= rh1.responded_date)
                        ) as concurrent_reviews
                    FROM review_history rh1
                    WHERE rh1.referee_id = ?
                    AND rh1.decision = 'accepted'
                    AND rh1.submitted_date IS NOT NULL
                )
                SELECT 
                    concurrent_reviews,
                    AVG(review_time) as avg_time,
                    COUNT(*) as count
                FROM WorkloadReviews
                GROUP BY concurrent_reviews
                ORDER BY concurrent_reviews
            """, (referee_id,))
            
            workload_impact = {row[0]: {'avg_time': row[1], 'count': row[2]} 
                             for row in cursor.fetchall()}
        
        return {
            'journal_specific_times': journal_times,
            'monthly_patterns': monthly_times,
            'workload_impact': workload_impact,
            'insights': self._generate_timeline_insights(
                journal_times, monthly_times, workload_impact
            )
        }
    
    def _generate_timeline_insights(self, journal_times: Dict, monthly_times: Dict, 
                                  workload_impact: Dict) -> List[str]:
        """Generate insights from timeline analysis"""
        insights = []
        
        # Journal insights
        if journal_times:
            fastest_journal = min(journal_times.items(), key=lambda x: x[1]['avg_time'])
            slowest_journal = max(journal_times.items(), key=lambda x: x[1]['avg_time'])
            
            if fastest_journal[1]['avg_time'] < slowest_journal[1]['avg_time'] * 0.7:
                insights.append(
                    f"Reviews for {fastest_journal[0]} are typically 30% faster than {slowest_journal[0]}"
                )
        
        # Monthly insights
        if monthly_times:
            summer_avg = np.mean([monthly_times.get(m, 21) for m in [6, 7, 8]])
            winter_avg = np.mean([monthly_times.get(m, 21) for m in [12, 1, 2]])
            
            if summer_avg > winter_avg * 1.2:
                insights.append("Summer reviews take 20% longer on average")
        
        # Workload insights
        if len(workload_impact) > 2:
            low_load = workload_impact.get(1, {}).get('avg_time', 21)
            high_load = max(workload_impact.keys())
            high_load_time = workload_impact[high_load]['avg_time']
            
            if high_load_time > low_load * 1.5:
                insights.append(
                    f"Review time increases by {int((high_load_time/low_load - 1) * 100)}% "
                    f"with {high_load} concurrent reviews"
                )
        
        return insights