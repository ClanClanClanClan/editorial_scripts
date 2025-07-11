"""
Predictive model for referee response behavior
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


class ResponsePredictor:
    """Machine learning model for predicting referee responses"""
    
    def __init__(self, db_path: str = "data/referees.db", model_path: str = "models/"):
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        self.response_model = None
        self.time_model = None
        self.scaler = StandardScaler()
        
        self._load_or_train_models()
    
    def predict_response_probability(self, referee_id: str, manuscript_data: Dict) -> Dict:
        """Predict likelihood of accepting review invitation"""
        # Extract features
        features = self._extract_features(referee_id, manuscript_data)
        
        if self.response_model is None:
            return {
                'accept_probability': 0.5,
                'confidence_score': 0.0,
                'prediction_factors': ['Model not trained'],
                'estimated_response_time': 7.0
            }
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Predict probability
        probability = self.response_model.predict_proba(features_scaled)[0][1]
        
        # Predict response time
        response_time = self.time_model.predict(features_scaled)[0]
        
        # Get feature importance for explanation
        feature_importance = self._get_feature_importance(features)
        
        return {
            'accept_probability': float(probability),
            'confidence_score': self._calculate_confidence(features_scaled),
            'prediction_factors': self._explain_prediction(feature_importance),
            'estimated_response_time': float(max(0, response_time))
        }
    
    def _extract_features(self, referee_id: str, manuscript_data: Dict) -> List[float]:
        """Extract features for prediction"""
        features = []
        
        # Get referee historical data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic referee stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_invitations,
                    SUM(CASE WHEN decision = 'accepted' THEN 1 ELSE 0 END) as accepted,
                    AVG(CASE WHEN responded_date IS NOT NULL 
                        THEN julianday(responded_date) - julianday(invited_date) 
                        ELSE NULL END) as avg_response_time,
                    MAX(invited_date) as last_invitation
                FROM review_history
                WHERE referee_id = ?
            """, (referee_id,))
            
            stats = cursor.fetchone()
            total_invitations = stats[0] or 0
            accepted = stats[1] or 0
            avg_response_time = stats[2] or 7
            last_invitation = stats[3]
            
            # Current workload
            cursor.execute("""
                SELECT COUNT(*)
                FROM review_history
                WHERE referee_id = ?
                AND decision = 'accepted'
                AND submitted_date IS NULL
            """, (referee_id,))
            
            current_workload = cursor.fetchone()[0]
            
            # Recent activity (last 90 days)
            cursor.execute("""
                SELECT COUNT(*)
                FROM review_history
                WHERE referee_id = ?
                AND invited_date >= date('now', '-90 days')
            """, (referee_id,))
            
            recent_invitations = cursor.fetchone()[0]
        
        # Calculate features
        features.extend([
            # Historical acceptance rate
            accepted / max(total_invitations, 1),
            
            # Average response time
            avg_response_time,
            
            # Current workload
            current_workload,
            
            # Days since last invitation
            self._days_since_date(last_invitation) if last_invitation else 365,
            
            # Recent invitation frequency
            recent_invitations,
            
            # Manuscript features
            manuscript_data.get('priority', 2),  # 1=high, 2=normal, 3=low
            manuscript_data.get('revision_round', 0),
            
            # Time features
            datetime.now().weekday(),  # Day of week
            datetime.now().month,  # Month
            
            # Journal match (1 if referee has reviewed for this journal before)
            manuscript_data.get('journal_match', 0),
            
            # Expertise match score
            manuscript_data.get('expertise_match', 0.5),
            
            # Total career invitations
            total_invitations
        ])
        
        return features
    
    def _load_or_train_models(self):
        """Load existing models or train new ones"""
        response_model_path = self.model_path / "response_model.pkl"
        time_model_path = self.model_path / "time_model.pkl"
        scaler_path = self.model_path / "scaler.pkl"
        
        if response_model_path.exists() and time_model_path.exists() and scaler_path.exists():
            # Load existing models
            self.response_model = joblib.load(response_model_path)
            self.time_model = joblib.load(time_model_path)
            self.scaler = joblib.load(scaler_path)
            logger.info("Loaded existing prediction models")
        else:
            # Train new models
            logger.info("Training new prediction models")
            self._train_models()
    
    def _train_models(self):
        """Train prediction models on historical data"""
        # Get training data
        X, y_response, y_time = self._prepare_training_data()
        
        if len(X) < 100:
            logger.warning("Insufficient training data for prediction models")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_resp_train, y_resp_test, y_time_train, y_time_test = \
            train_test_split(X_scaled, y_response, y_time, test_size=0.2, random_state=42)
        
        # Train response prediction model
        self.response_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.response_model.fit(X_train, y_resp_train)
        
        # Train response time model
        self.time_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.time_model.fit(X_train, y_time_train)
        
        # Evaluate models
        response_score = self.response_model.score(X_test, y_resp_test)
        time_score = self.time_model.score(X_test, y_time_test)
        
        logger.info(f"Response model accuracy: {response_score:.2f}")
        logger.info(f"Time model R²: {time_score:.2f}")
        
        # Save models
        joblib.dump(self.response_model, self.model_path / "response_model.pkl")
        joblib.dump(self.time_model, self.model_path / "time_model.pkl")
        joblib.dump(self.scaler, self.model_path / "scaler.pkl")
    
    def _prepare_training_data(self) -> Tuple[List[List[float]], List[int], List[float]]:
        """Prepare training data from historical records"""
        X = []
        y_response = []
        y_time = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all review invitations with outcomes
            cursor.execute("""
                SELECT 
                    rh.*,
                    m.journal,
                    m.keywords
                FROM review_history rh
                JOIN manuscripts m ON rh.manuscript_id = m.id
                WHERE rh.responded_date IS NOT NULL
                ORDER BY rh.invited_date DESC
                LIMIT 10000
            """)
            
            for row in cursor.fetchall():
                # Skip if no decision
                if row['decision'] is None:
                    continue
                
                # Create mock manuscript data
                manuscript_data = {
                    'journal_id': row['journal'],
                    'priority': 2,
                    'revision_round': 0,
                    'journal_match': 1,  # Since they reviewed for this journal
                    'expertise_match': 0.7  # Default estimate
                }
                
                # Extract features
                features = self._extract_features(row['referee_id'], manuscript_data)
                X.append(features)
                
                # Response (1 = accepted, 0 = declined)
                y_response.append(1 if row['decision'] == 'accepted' else 0)
                
                # Response time in days
                response_time = (datetime.fromisoformat(row['responded_date']) - 
                               datetime.fromisoformat(row['invited_date'])).days
                y_time.append(response_time)
        
        return X, y_response, y_time
    
    def _calculate_confidence(self, features_scaled: np.ndarray) -> float:
        """Calculate prediction confidence"""
        if self.response_model is None:
            return 0.0
        
        # Get probability predictions
        probabilities = self.response_model.predict_proba(features_scaled)[0]
        
        # Confidence is how certain the model is (distance from 0.5)
        confidence = abs(probabilities[1] - 0.5) * 2
        
        return float(confidence)
    
    def _get_feature_importance(self, features: List[float]) -> Dict[str, float]:
        """Get feature importance for the prediction"""
        if self.response_model is None or not hasattr(self.response_model, 'feature_importances_'):
            return {}
        
        feature_names = [
            'historical_acceptance_rate',
            'avg_response_time',
            'current_workload',
            'days_since_last_invitation',
            'recent_invitations',
            'manuscript_priority',
            'revision_round',
            'day_of_week',
            'month',
            'journal_match',
            'expertise_match',
            'total_career_invitations'
        ]
        
        importances = self.response_model.feature_importances_
        
        # Create importance dictionary
        importance_dict = {}
        for name, importance, value in zip(feature_names, importances, features):
            importance_dict[name] = {
                'importance': float(importance),
                'value': float(value)
            }
        
        return importance_dict
    
    def _explain_prediction(self, feature_importance: Dict[str, Dict]) -> List[str]:
        """Generate human-readable explanation of prediction"""
        if not feature_importance:
            return ["Model not available for explanation"]
        
        explanations = []
        
        # Sort by importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1]['importance'],
            reverse=True
        )
        
        # Top 3 factors
        for feature, data in sorted_features[:3]:
            value = data['value']
            
            if feature == 'historical_acceptance_rate':
                if value > 0.7:
                    explanations.append("High historical acceptance rate")
                elif value < 0.3:
                    explanations.append("Low historical acceptance rate")
            
            elif feature == 'current_workload':
                if value >= 3:
                    explanations.append("High current workload may reduce acceptance")
                elif value == 0:
                    explanations.append("No current reviews increases acceptance likelihood")
            
            elif feature == 'expertise_match':
                if value > 0.8:
                    explanations.append("Strong expertise match with manuscript")
                elif value < 0.3:
                    explanations.append("Limited expertise match may reduce acceptance")
            
            elif feature == 'days_since_last_invitation':
                if value > 90:
                    explanations.append("Long gap since last invitation")
                elif value < 7:
                    explanations.append("Recently invited may affect response")
            
            elif feature == 'journal_match':
                if value == 1:
                    explanations.append("Has reviewed for this journal before")
        
        return explanations
    
    def _days_since_date(self, date_str: str) -> float:
        """Calculate days since a date"""
        try:
            date = datetime.fromisoformat(date_str)
            return (datetime.now() - date).days
        except:
            return 365  # Default to 1 year
    
    def update_model(self, new_data: List[Dict]):
        """Update model with new response data"""
        # This would implement online learning or periodic retraining
        logger.info(f"Updating model with {len(new_data)} new data points")
        
        # For now, just retrain periodically
        if len(new_data) > 100:
            self._train_models()
    
    def get_model_performance(self) -> Dict:
        """Get current model performance metrics"""
        if self.response_model is None:
            return {'status': 'Models not trained'}
        
        # Load recent test data
        X, y_response, y_time = self._prepare_training_data()
        
        if len(X) < 10:
            return {'status': 'Insufficient data for evaluation'}
        
        # Take last 20% as test set
        test_size = int(len(X) * 0.2)
        X_test = self.scaler.transform(X[-test_size:])
        y_resp_test = y_response[-test_size:]
        y_time_test = y_time[-test_size:]
        
        # Calculate metrics
        response_accuracy = self.response_model.score(X_test, y_resp_test)
        time_r2 = self.time_model.score(X_test, y_time_test)
        
        # Calculate mean absolute error for time prediction
        time_predictions = self.time_model.predict(X_test)
        time_mae = np.mean(np.abs(time_predictions - y_time_test))
        
        return {
            'response_model': {
                'accuracy': float(response_accuracy),
                'test_samples': len(y_resp_test)
            },
            'time_model': {
                'r2_score': float(time_r2),
                'mean_absolute_error_days': float(time_mae),
                'test_samples': len(y_time_test)
            },
            'last_trained': datetime.now().isoformat()
        }