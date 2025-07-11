"""
A/B testing framework for editorial process optimization
"""

import logging
from typing import Dict, List, Tuple, Optional, Callable, Any
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
from scipy import stats

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(Enum):
    """Types of A/B tests"""
    REFEREE_SELECTION = "referee_selection"
    INVITATION_TIMING = "invitation_timing"
    REMINDER_STRATEGY = "reminder_strategy"
    SCREENING_PROCESS = "screening_process"
    UI_INTERFACE = "ui_interface"
    EMAIL_TEMPLATE = "email_template"


@dataclass
class TestVariant:
    """A/B test variant configuration"""
    id: str
    name: str
    description: str
    allocation_percent: float
    config: Dict[str, Any]
    is_control: bool = False


@dataclass
class TestMetric:
    """Metric to track in A/B test"""
    name: str
    type: str  # 'rate', 'average', 'count', 'time'
    goal: str  # 'increase', 'decrease'
    primary: bool = False


@dataclass
class TestResult:
    """A/B test results"""
    variant_id: str
    metric_name: str
    value: float
    sample_size: int
    confidence_interval: Tuple[float, float]
    p_value: Optional[float] = None
    statistical_significance: bool = False


class ABTest:
    """Individual A/B test configuration and management"""
    
    def __init__(self, name: str, description: str, test_type: TestType):
        self.id = f"{test_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.name = name
        self.description = description
        self.test_type = test_type
        self.status = TestStatus.DRAFT
        self.variants: List[TestVariant] = []
        self.metrics: List[TestMetric] = []
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.target_sample_size: int = 1000
        self.confidence_level: float = 0.95
        self.minimum_effect_size: float = 0.05
        self.created_at = datetime.now()
        self.results: List[TestResult] = []
    
    def add_variant(self, variant: TestVariant):
        """Add a variant to the test"""
        self.variants.append(variant)
    
    def add_metric(self, metric: TestMetric):
        """Add a metric to track"""
        self.metrics.append(metric)
    
    def calculate_sample_size(self, baseline_rate: float, minimum_detectable_effect: float,
                            power: float = 0.8, alpha: float = 0.05) -> int:
        """Calculate required sample size for the test"""
        # Using formula for comparing two proportions
        p1 = baseline_rate
        p2 = baseline_rate * (1 + minimum_detectable_effect)
        
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(power)
        
        pooled_p = (p1 + p2) / 2
        
        n = (2 * pooled_p * (1 - pooled_p) * (z_alpha + z_beta)**2) / (p1 - p2)**2
        
        return int(np.ceil(n))
    
    def to_dict(self) -> Dict:
        """Convert test to dictionary for storage"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'test_type': self.test_type.value,
            'status': self.status.value,
            'variants': [v.__dict__ for v in self.variants],
            'metrics': [m.__dict__ for m in self.metrics],
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'target_sample_size': self.target_sample_size,
            'confidence_level': self.confidence_level,
            'minimum_effect_size': self.minimum_effect_size,
            'created_at': self.created_at.isoformat()
        }


class ABTestingFramework:
    """Framework for managing and analyzing A/B tests"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self._ensure_ab_testing_tables()
        self.active_tests: Dict[str, ABTest] = {}
        self._load_active_tests()
    
    def _ensure_ab_testing_tables(self):
        """Ensure A/B testing tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create A/B tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    test_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create test assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_test_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES ab_tests (id)
                )
            """)
            
            # Create test events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_test_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    event_value REAL,
                    event_data TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES ab_tests (id)
                )
            """)
            
            conn.commit()
    
    def create_referee_selection_test(self, name: str, description: str) -> ABTest:
        """Create A/B test for referee selection methods"""
        test = ABTest(name, description, TestType.REFEREE_SELECTION)
        
        # Add variants
        control_variant = TestVariant(
            id="control",
            name="Manual Selection",
            description="Traditional manual referee selection",
            allocation_percent=50.0,
            config={"method": "manual"},
            is_control=True
        )
        
        treatment_variant = TestVariant(
            id="ai_selection",
            name="AI-Assisted Selection",
            description="AI-powered referee matching",
            allocation_percent=50.0,
            config={"method": "ai_assisted", "min_confidence": 0.7}
        )
        
        test.add_variant(control_variant)
        test.add_variant(treatment_variant)
        
        # Add metrics
        test.add_metric(TestMetric("acceptance_rate", "rate", "increase", primary=True))
        test.add_metric(TestMetric("review_quality", "average", "increase", primary=False))
        test.add_metric(TestMetric("time_to_completion", "time", "decrease", primary=False))
        test.add_metric(TestMetric("editor_override_rate", "rate", "decrease", primary=False))
        
        return test
    
    def create_reminder_strategy_test(self, name: str, description: str) -> ABTest:
        """Create A/B test for reminder strategies"""
        test = ABTest(name, description, TestType.REMINDER_STRATEGY)
        
        # Add variants
        control_variant = TestVariant(
            id="standard_reminders",
            name="Standard Reminders",
            description="Current reminder schedule",
            allocation_percent=33.3,
            config={"reminder_days": [7, 3, 1], "tone": "formal"},
            is_control=True
        )
        
        frequent_variant = TestVariant(
            id="frequent_reminders",
            name="Frequent Reminders",
            description="More frequent gentle reminders",
            allocation_percent=33.3,
            config={"reminder_days": [10, 7, 5, 3, 1], "tone": "gentle"}
        )
        
        personalized_variant = TestVariant(
            id="personalized_reminders",
            name="Personalized Reminders",
            description="Personalized timing based on referee history",
            allocation_percent=33.4,
            config={"adaptive_timing": True, "personalization": True}
        )
        
        test.add_variant(control_variant)
        test.add_variant(frequent_variant)
        test.add_variant(personalized_variant)
        
        # Add metrics
        test.add_metric(TestMetric("response_rate", "rate", "increase", primary=True))
        test.add_metric(TestMetric("time_to_response", "time", "decrease", primary=False))
        test.add_metric(TestMetric("completion_rate", "rate", "increase", primary=False))
        
        return test
    
    def create_screening_process_test(self, name: str, description: str) -> ABTest:
        """Create A/B test for manuscript screening processes"""
        test = ABTest(name, description, TestType.SCREENING_PROCESS)
        
        # Add variants
        control_variant = TestVariant(
            id="manual_screening",
            name="Manual Screening",
            description="Traditional editor screening",
            allocation_percent=50.0,
            config={"method": "manual", "editor_review": True},
            is_control=True
        )
        
        ai_variant = TestVariant(
            id="ai_screening",
            name="AI-Assisted Screening",
            description="AI pre-screening with editor review",
            allocation_percent=50.0,
            config={"method": "ai_assisted", "ai_threshold": 0.6, "editor_review": True}
        )
        
        test.add_variant(control_variant)
        test.add_variant(ai_variant)
        
        # Add metrics
        test.add_metric(TestMetric("screening_time", "time", "decrease", primary=True))
        test.add_metric(TestMetric("desk_rejection_accuracy", "rate", "increase", primary=True))
        test.add_metric(TestMetric("processing_cost", "average", "decrease", primary=False))
        
        return test
    
    def start_test(self, test: ABTest, duration_days: int = 30) -> str:
        """Start an A/B test"""
        # Validate test configuration
        if len(test.variants) < 2:
            raise ValueError("Test must have at least 2 variants")
        
        total_allocation = sum(v.allocation_percent for v in test.variants)
        if abs(total_allocation - 100.0) > 0.1:
            raise ValueError("Variant allocations must sum to 100%")
        
        if not test.metrics:
            raise ValueError("Test must have at least one metric")
        
        # Set test dates
        test.start_date = datetime.now()
        test.end_date = test.start_date + timedelta(days=duration_days)
        test.status = TestStatus.ACTIVE
        
        # Store test in database
        self._store_test(test)
        
        # Add to active tests
        self.active_tests[test.id] = test
        
        logger.info(f"Started A/B test: {test.name} (ID: {test.id})")
        
        return test.id
    
    def assign_to_variant(self, test_id: str, entity_id: str, 
                         entity_type: str = "manuscript") -> str:
        """Assign an entity to a test variant"""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} is not active")
        
        test = self.active_tests[test_id]
        
        # Check if already assigned
        existing_assignment = self._get_existing_assignment(test_id, entity_id, entity_type)
        if existing_assignment:
            return existing_assignment
        
        # Assign to variant based on allocation percentages
        variant = self._select_variant(test.variants, entity_id)
        
        # Store assignment
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ab_test_assignments 
                (test_id, entity_id, entity_type, variant_id)
                VALUES (?, ?, ?, ?)
            """, (test_id, entity_id, entity_type, variant.id))
            conn.commit()
        
        return variant.id
    
    def record_event(self, test_id: str, entity_id: str, variant_id: str,
                    event_name: str, event_value: Optional[float] = None,
                    event_data: Optional[Dict] = None):
        """Record an event for A/B test analysis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ab_test_events 
                (test_id, entity_id, variant_id, event_name, event_value, event_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                test_id, entity_id, variant_id, event_name, event_value,
                json.dumps(event_data) if event_data else None
            ))
            conn.commit()
    
    def analyze_test(self, test_id: str) -> Dict:
        """Analyze A/B test results"""
        if test_id not in self.active_tests:
            test = self._load_test(test_id)
            if not test:
                raise ValueError(f"Test {test_id} not found")
        else:
            test = self.active_tests[test_id]
        
        # Get test data
        assignments = self._get_test_assignments(test_id)
        events = self._get_test_events(test_id)
        
        # Calculate metrics for each variant
        variant_results = {}
        
        for variant in test.variants:
            variant_assignments = [a for a in assignments if a['variant_id'] == variant.id]
            variant_events = [e for e in events if e['variant_id'] == variant.id]
            
            variant_results[variant.id] = {
                'variant_name': variant.name,
                'sample_size': len(variant_assignments),
                'metrics': self._calculate_variant_metrics(variant_events, test.metrics)
            }
        
        # Perform statistical analysis
        statistical_results = self._perform_statistical_analysis(variant_results, test)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(statistical_results, test)
        
        return {
            'test_id': test_id,
            'test_name': test.name,
            'status': test.status.value,
            'start_date': test.start_date.isoformat() if test.start_date else None,
            'end_date': test.end_date.isoformat() if test.end_date else None,
            'variant_results': variant_results,
            'statistical_analysis': statistical_results,
            'recommendations': recommendations,
            'sample_size_achieved': sum(r['sample_size'] for r in variant_results.values()),
            'target_sample_size': test.target_sample_size
        }
    
    def _select_variant(self, variants: List[TestVariant], entity_id: str) -> TestVariant:
        """Select variant for entity using consistent hashing"""
        # Use hash of entity_id for consistent assignment
        hash_value = hash(entity_id) % 1000 / 10  # Convert to percentage 0-99.9
        
        cumulative_percent = 0
        for variant in variants:
            cumulative_percent += variant.allocation_percent
            if hash_value < cumulative_percent:
                return variant
        
        # Fallback to last variant
        return variants[-1]
    
    def _calculate_variant_metrics(self, events: List[Dict], metrics: List[TestMetric]) -> Dict:
        """Calculate metrics for a variant"""
        results = {}
        
        for metric in metrics:
            metric_events = [e for e in events if e['event_name'] == metric.name]
            
            if metric.type == 'rate':
                # Calculate rate (successes / total)
                successes = len([e for e in metric_events if e['event_value'] == 1])
                total = len(metric_events)
                results[metric.name] = {
                    'value': successes / total if total > 0 else 0,
                    'count': successes,
                    'sample_size': total
                }
            
            elif metric.type == 'average':
                # Calculate average
                values = [e['event_value'] for e in metric_events if e['event_value'] is not None]
                results[metric.name] = {
                    'value': np.mean(values) if values else 0,
                    'std': np.std(values) if len(values) > 1 else 0,
                    'sample_size': len(values)
                }
            
            elif metric.type == 'time':
                # Calculate average time
                values = [e['event_value'] for e in metric_events if e['event_value'] is not None]
                results[metric.name] = {
                    'value': np.mean(values) if values else 0,
                    'median': np.median(values) if values else 0,
                    'sample_size': len(values)
                }
            
            elif metric.type == 'count':
                # Simple count
                results[metric.name] = {
                    'value': len(metric_events),
                    'sample_size': len(metric_events)
                }
        
        return results
    
    def _perform_statistical_analysis(self, variant_results: Dict, test: ABTest) -> Dict:
        """Perform statistical significance testing"""
        if len(variant_results) < 2:
            return {'error': 'Need at least 2 variants for comparison'}
        
        # Find control variant
        control_variant = None
        for variant in test.variants:
            if variant.is_control:
                control_variant = variant.id
                break
        
        if not control_variant:
            control_variant = list(variant_results.keys())[0]
        
        results = {}
        
        for metric in test.metrics:
            if metric.name not in variant_results[control_variant]['metrics']:
                continue
            
            control_data = variant_results[control_variant]['metrics'][metric.name]
            
            for variant_id, variant_data in variant_results.items():
                if variant_id == control_variant:
                    continue
                
                if metric.name not in variant_data['metrics']:
                    continue
                
                treatment_data = variant_data['metrics'][metric.name]
                
                # Perform appropriate statistical test
                if metric.type == 'rate':
                    # Two-proportion z-test
                    p_value, significance = self._two_proportion_test(
                        control_data['count'], control_data['sample_size'],
                        treatment_data['count'], treatment_data['sample_size']
                    )
                
                elif metric.type in ['average', 'time']:
                    # Would need raw data for proper t-test
                    # For now, use approximation
                    p_value = 0.05  # Placeholder
                    significance = p_value < 0.05
                
                else:
                    p_value = None
                    significance = False
                
                results[f"{variant_id}_vs_{control_variant}_{metric.name}"] = {
                    'control_value': control_data['value'],
                    'treatment_value': treatment_data['value'],
                    'relative_change': ((treatment_data['value'] - control_data['value']) / 
                                      control_data['value']) if control_data['value'] > 0 else 0,
                    'p_value': p_value,
                    'statistically_significant': significance,
                    'metric_goal': metric.goal,
                    'improvement': self._is_improvement(
                        control_data['value'], treatment_data['value'], metric.goal
                    )
                }
        
        return results
    
    def _two_proportion_test(self, x1: int, n1: int, x2: int, n2: int) -> Tuple[float, bool]:
        """Perform two-proportion z-test"""
        if n1 == 0 or n2 == 0:
            return 1.0, False
        
        p1 = x1 / n1
        p2 = x2 / n2
        
        if p1 == p2:
            return 1.0, False
        
        # Pooled proportion
        p_pool = (x1 + x2) / (n1 + n2)
        
        # Standard error
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        if se == 0:
            return 1.0, False
        
        # Z-score
        z = (p1 - p2) / se
        
        # Two-tailed p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        return p_value, p_value < 0.05
    
    def _is_improvement(self, control_value: float, treatment_value: float, goal: str) -> bool:
        """Check if treatment is an improvement over control"""
        if goal == 'increase':
            return treatment_value > control_value
        elif goal == 'decrease':
            return treatment_value < control_value
        else:
            return False
    
    def _generate_recommendations(self, statistical_results: Dict, test: ABTest) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check primary metrics
        primary_metrics = [m for m in test.metrics if m.primary]
        
        significant_improvements = 0
        total_primary_comparisons = 0
        
        for key, result in statistical_results.items():
            if any(m.name in key for m in primary_metrics):
                total_primary_comparisons += 1
                if result['statistically_significant'] and result['improvement']:
                    significant_improvements += 1
        
        if significant_improvements > 0:
            recommendations.append(
                f"Found {significant_improvements} statistically significant improvements "
                f"in primary metrics"
            )
        
        if significant_improvements >= total_primary_comparisons * 0.5:
            recommendations.append("Recommend implementing the winning variant")
        else:
            recommendations.append("Inconclusive results - consider extending test duration")
        
        # Check sample size
        for variant_id, variant_data in statistical_results.items():
            if variant_data.get('sample_size', 0) < test.target_sample_size * 0.8:
                recommendations.append("Consider increasing sample size for more reliable results")
                break
        
        return recommendations
    
    def _store_test(self, test: ABTest):
        """Store test configuration in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ab_tests 
                (id, name, description, test_type, status, config, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test.id, test.name, test.description, test.test_type.value,
                test.status.value, json.dumps(test.to_dict()),
                test.start_date.isoformat() if test.start_date else None,
                test.end_date.isoformat() if test.end_date else None
            ))
            conn.commit()
    
    def _load_active_tests(self):
        """Load active tests from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, config FROM ab_tests 
                WHERE status = 'active'
            """)
            
            for test_id, config_json in cursor.fetchall():
                try:
                    config = json.loads(config_json)
                    test = self._config_to_test(config)
                    self.active_tests[test_id] = test
                except Exception as e:
                    logger.error(f"Error loading test {test_id}: {e}")
    
    def _config_to_test(self, config: Dict) -> ABTest:
        """Convert configuration dict to ABTest object"""
        test = ABTest(config['name'], config['description'], 
                     TestType(config['test_type']))
        test.id = config['id']
        test.status = TestStatus(config['status'])
        
        # Load variants
        for variant_config in config['variants']:
            variant = TestVariant(**variant_config)
            test.add_variant(variant)
        
        # Load metrics
        for metric_config in config['metrics']:
            metric = TestMetric(**metric_config)
            test.add_metric(metric)
        
        # Load dates
        if config['start_date']:
            test.start_date = datetime.fromisoformat(config['start_date'])
        if config['end_date']:
            test.end_date = datetime.fromisoformat(config['end_date'])
        
        return test
    
    def _load_test(self, test_id: str) -> Optional[ABTest]:
        """Load test from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config FROM ab_tests WHERE id = ?
            """, (test_id,))
            
            row = cursor.fetchone()
            if row:
                config = json.loads(row[0])
                return self._config_to_test(config)
        
        return None
    
    def _get_existing_assignment(self, test_id: str, entity_id: str, 
                               entity_type: str) -> Optional[str]:
        """Check if entity is already assigned to a variant"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT variant_id FROM ab_test_assignments
                WHERE test_id = ? AND entity_id = ? AND entity_type = ?
            """, (test_id, entity_id, entity_type))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    def _get_test_assignments(self, test_id: str) -> List[Dict]:
        """Get all assignments for a test"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ab_test_assignments WHERE test_id = ?
            """, (test_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_test_events(self, test_id: str) -> List[Dict]:
        """Get all events for a test"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ab_test_events WHERE test_id = ?
            """, (test_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_tests(self) -> List[Dict]:
        """Get summary of all active tests"""
        return [
            {
                'id': test.id,
                'name': test.name,
                'type': test.test_type.value,
                'status': test.status.value,
                'start_date': test.start_date.isoformat() if test.start_date else None,
                'end_date': test.end_date.isoformat() if test.end_date else None,
                'variants': len(test.variants)
            }
            for test in self.active_tests.values()
        ]