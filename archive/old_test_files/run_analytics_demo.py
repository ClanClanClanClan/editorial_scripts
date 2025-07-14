#!/usr/bin/env python3
"""
Comprehensive Analytics System Demo

This script demonstrates the full capabilities of the Editorial Scripts
analytics system, including referee performance tracking, predictive analytics,
network analysis, quality assessment, and lean metrics.
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add analytics to path
sys.path.insert(0, str(Path(__file__).parent / "analytics"))

from analytics.core.referee_analytics import RefereeAnalytics
from analytics.core.comparative_analytics import ComparativeRefereeAnalytics
from analytics.predictive.response_predictor import ResponsePredictor
from analytics.predictive.timeline_predictor import TimelinePredictor
from analytics.quality.review_analyzer import ReviewQualityAnalyzer
from analytics.network.referee_network import RefereeNetworkAnalyzer
from analytics.lean.metrics_tracker import LeanMetricsTracker
from analytics.lean.ab_testing import ABTestingFramework
from analytics.api.dashboard_api import create_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyticsSystemDemo:
    """Comprehensive demo of the analytics system"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = db_path
        
        # Initialize all analytics components
        logger.info("Initializing analytics components...")
        
        self.referee_analytics = RefereeAnalytics(db_path)
        self.comparative_analytics = ComparativeRefereeAnalytics(db_path)
        self.response_predictor = ResponsePredictor(db_path)
        self.timeline_predictor = TimelinePredictor(db_path)
        self.quality_analyzer = ReviewQualityAnalyzer(db_path)
        self.network_analyzer = RefereeNetworkAnalyzer(db_path)
        self.lean_tracker = LeanMetricsTracker(db_path)
        self.ab_testing = ABTestingFramework(db_path)
        
        logger.info("✅ All analytics components initialized successfully")
    
    def demo_referee_analytics(self):
        """Demonstrate referee analytics capabilities"""
        logger.info("\n" + "="*50)
        logger.info("REFEREE ANALYTICS DEMO")
        logger.info("="*50)
        
        try:
            # Get a sample referee ID (first available)
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM referees LIMIT 1")
                result = cursor.fetchone()
                
                if not result:
                    logger.warning("No referees found in database. Creating sample data...")
                    self._create_sample_data()
                    cursor.execute("SELECT id FROM referees LIMIT 1")
                    result = cursor.fetchone()
                
                referee_id = result[0]
            
            logger.info(f"Analyzing referee: {referee_id}")
            
            # Calculate comprehensive metrics
            metrics = self.referee_analytics.calculate_referee_metrics(referee_id)
            
            logger.info(f"📊 Overall Score: {metrics.get_overall_score():.1f}/10")
            logger.info(f"⏱️  Average Review Time: {metrics.time_metrics.avg_review_time:.1f} days")
            logger.info(f"⭐ Quality Score: {metrics.quality_metrics.get_overall_quality():.1f}/10")
            logger.info(f"🔒 Reliability Score: {metrics.reliability_metrics.get_reliability_score():.1f}")
            logger.info(f"🎯 Acceptance Rate: {metrics.reliability_metrics.acceptance_rate:.1%}")
            logger.info(f"📚 Expertise Areas: {len(metrics.expertise_metrics.expertise_areas)}")
            
            # Get trends
            trends = self.referee_analytics.get_referee_trends(referee_id)
            if 'error' not in trends:
                logger.info(f"📈 Performance Trend: {trends.get('trend_direction', 'Unknown')}")
            
            # Get percentile rankings
            percentiles = self.comparative_analytics.calculate_percentile_ranks(referee_id)
            logger.info(f"🏆 Overall Percentile: {percentiles.overall_percentile:.1f}th")
            logger.info(f"🏆 Performance Tier: {percentiles.get_performance_tier().value}")
            
            # Get recommendations
            recommendations = metrics.get_recommendations()
            if recommendations:
                logger.info("💡 Improvement Recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    logger.info(f"   {i}. {rec}")
            
        except Exception as e:
            logger.error(f"Error in referee analytics demo: {e}")
    
    def demo_predictive_analytics(self):
        """Demonstrate predictive analytics capabilities"""
        logger.info("\n" + "="*50)
        logger.info("PREDICTIVE ANALYTICS DEMO")
        logger.info("="*50)
        
        try:
            # Get a sample referee
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM referees LIMIT 1")
                result = cursor.fetchone()
                referee_id = result[0] if result else "sample_referee"
            
            # Sample manuscript data
            manuscript_data = {
                'journal_id': 'SICON',
                'priority': 2,
                'revision_round': 0,
                'journal_match': 1,
                'expertise_match': 0.8,
                'complexity_score': 0.6,
                'page_count': 25,
                'current_workload': 2
            }
            
            logger.info(f"Predicting for referee: {referee_id}")
            logger.info(f"Manuscript: {manuscript_data['journal_id']}, Complexity: {manuscript_data['complexity_score']}")
            
            # Response prediction
            response_pred = self.response_predictor.predict_response_probability(
                referee_id, manuscript_data
            )
            
            logger.info(f"🎯 Acceptance Probability: {response_pred['accept_probability']:.1%}")
            logger.info(f"🕐 Estimated Response Time: {response_pred['estimated_response_time']:.1f} days")
            logger.info(f"🔍 Confidence: {response_pred['confidence_score']:.1%}")
            
            if response_pred['prediction_factors']:
                logger.info("📋 Key Factors:")
                for factor in response_pred['prediction_factors'][:3]:
                    logger.info(f"   • {factor}")
            
            # Timeline prediction
            timeline_pred = self.timeline_predictor.predict_review_timeline(
                referee_id, manuscript_data['current_workload'], manuscript_data
            )
            
            logger.info(f"⏰ Expected Review Time: {timeline_pred['expected_days']:.1f} days")
            logger.info(f"📊 Confidence Interval: {timeline_pred['confidence_interval'][0]:.1f} - {timeline_pred['confidence_interval'][1]:.1f} days")
            
            if timeline_pred['risk_factors']:
                logger.info("⚠️  Risk Factors:")
                for risk in timeline_pred['risk_factors'][:2]:
                    logger.info(f"   • {risk}")
            
            if timeline_pred['optimization_suggestions']:
                logger.info("💡 Optimization Suggestions:")
                for suggestion in timeline_pred['optimization_suggestions'][:2]:
                    logger.info(f"   • {suggestion}")
            
            # Model performance
            model_perf = self.response_predictor.get_model_performance()
            if 'response_model' in model_perf:
                logger.info(f"🤖 Model Accuracy: {model_perf['response_model']['accuracy']:.1%}")
            
        except Exception as e:
            logger.error(f"Error in predictive analytics demo: {e}")
    
    def demo_network_analysis(self):
        """Demonstrate network analysis capabilities"""
        logger.info("\n" + "="*50)
        logger.info("NETWORK ANALYSIS DEMO")
        logger.info("="*50)
        
        try:
            # Overall network structure
            structure = self.network_analyzer.analyze_network_structure()
            
            if 'error' not in structure:
                basic = structure['basic_metrics']
                logger.info(f"🕸️  Network Size: {basic['nodes']} referees, {basic['edges']} connections")
                logger.info(f"🔗 Network Density: {basic['density']:.3f}")
                logger.info(f"🏘️  Clustering Coefficient: {basic['clustering_coefficient']:.3f}")
                
                connectivity = structure['connectivity']
                logger.info(f"🌐 Connected Components: {connectivity['num_components']}")
                if connectivity['is_connected']:
                    logger.info(f"📏 Network Diameter: {connectivity['diameter']}")
                    logger.info(f"📐 Average Path Length: {connectivity['avg_path_length']:.2f}")
            
            # Detect communities
            communities = self.network_analyzer.detect_communities()
            if communities:
                logger.info(f"🏘️  Communities Detected: {len(communities)}")
                
                # Show largest communities
                for i, community in enumerate(communities[:3], 1):
                    logger.info(f"   Community {i}: {community.size} members")
                    if community.dominant_expertise:
                        logger.info(f"      Expertise: {', '.join(community.dominant_expertise[:2])}")
                    logger.info(f"      Avg Performance: {community.avg_performance:.1f}")
            
            # Key connectors
            connectors = self.network_analyzer.identify_key_connectors(5)
            if connectors:
                logger.info(f"🔗 Top Network Connectors:")
                for i, connector in enumerate(connectors[:3], 1):
                    logger.info(f"   {i}. {connector['name']} (Score: {connector['connector_score']:.3f})")
                    logger.info(f"      Connections: {connector['num_connections']}")
            
            # Expertise clusters
            expertise = self.network_analyzer.analyze_expertise_clusters()
            if expertise:
                logger.info(f"🎓 Expertise Areas Analyzed: {len(expertise)}")
                
                # Show top expertise areas
                sorted_expertise = sorted(
                    expertise.items(),
                    key=lambda x: x[1]['num_experts'],
                    reverse=True
                )
                
                for area, data in sorted_expertise[:3]:
                    logger.info(f"   • {area}: {data['num_experts']} experts")
                    logger.info(f"     Network Density: {data['network_density']:.3f}")
            
        except Exception as e:
            logger.error(f"Error in network analysis demo: {e}")
    
    def demo_quality_analysis(self):
        """Demonstrate quality analysis capabilities"""
        logger.info("\n" + "="*50)
        logger.info("QUALITY ANALYSIS DEMO")
        logger.info("="*50)
        
        try:
            # Get a sample review
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, referee_id FROM review_history 
                    WHERE submitted_date IS NOT NULL 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if not result:
                    logger.warning("No completed reviews found for quality analysis")
                    return
                
                review_id, referee_id = result
            
            logger.info(f"Analyzing review: {review_id}")
            
            # Note: This would typically analyze actual review text
            # For demo purposes, we'll show the framework structure
            logger.info("📝 Quality Analysis Framework:")
            logger.info("   • Content Analysis (word count, concepts, depth)")
            logger.info("   • Structure Analysis (organization, sections)")
            logger.info("   • Impact Analysis (decision alignment, influence)")
            logger.info("   • Sentiment Analysis (tone, constructiveness)")
            
            # Show quality trends for referee
            trends = self.quality_analyzer.analyze_referee_quality_trends(referee_id)
            
            if 'error' not in trends:
                logger.info(f"📊 Quality Metrics for Referee:")
                logger.info(f"   • Reviews Analyzed: {trends['review_count']}")
                logger.info(f"   • Average Quality: {trends['average_quality']:.1f}/10")
                logger.info(f"   • Quality Trend: {trends['quality_trend']}")
                logger.info(f"   • Average Length: {trends['average_length']:.0f} words")
                logger.info(f"   • Consistency (std): {trends['consistency']:.2f}")
            
            logger.info("💡 Quality Improvement Areas:")
            logger.info("   • Automated quality scoring using NLP")
            logger.info("   • Review completeness assessment")
            logger.info("   • Constructiveness measurement")
            logger.info("   • Technical depth analysis")
            
        except Exception as e:
            logger.error(f"Error in quality analysis demo: {e}")
    
    def demo_lean_metrics(self):
        """Demonstrate lean metrics and process optimization"""
        logger.info("\n" + "="*50)
        logger.info("LEAN METRICS DEMO")
        logger.info("="*50)
        
        try:
            # Cycle time metrics
            cycle_time = self.lean_tracker.calculate_cycle_time_metrics()
            
            if 'error' not in cycle_time:
                logger.info(f"⏱️  Cycle Time Analysis:")
                logger.info(f"   • Average Cycle Time: {cycle_time['avg_cycle_time']:.1f} days")
                logger.info(f"   • Median Cycle Time: {cycle_time['median_cycle_time']:.1f} days")
                logger.info(f"   • Manuscripts Processed: {cycle_time['total_manuscripts']}")
                logger.info(f"   • Completion Rate: {cycle_time['completed_manuscripts']}/{cycle_time['total_manuscripts']}")
                logger.info(f"   • Trend: {cycle_time['trend']}")
                
                percentiles = cycle_time['percentiles']
                logger.info(f"   • 90th Percentile: {percentiles['90th']:.1f} days")
            
            # Automation metrics
            automation = self.lean_tracker.calculate_automation_metrics()
            logger.info(f"🤖 Automation Analysis:")
            logger.info(f"   • Overall Automation Rate: {automation['overall_automation_rate']:.1%}")
            logger.info(f"   • Time Saved: {automation['total_time_saved_minutes']:.0f} minutes")
            
            opportunities = automation['automation_opportunities']
            if opportunities:
                logger.info(f"   • Top Opportunity: {opportunities[0]['process']}")
                logger.info(f"     Potential: {opportunities[0]['potential_automation']:.1%}")
                logger.info(f"     ROI Score: {opportunities[0]['roi_score']:.1f}")
            
            # Quality metrics
            quality = self.lean_tracker.calculate_quality_metrics()
            logger.info(f"⭐ Quality Metrics:")
            logger.info(f"   • First-Time Quality Rate: {quality['first_time_quality_rate']:.1%}")
            logger.info(f"   • Average Review Quality: {quality['avg_review_quality_score']:.1f}/10")
            logger.info(f"   • Decision Consistency: {quality['decision_consistency_rate']:.1%}")
            logger.info(f"   • Quality Trend: {quality['quality_trend']}")
            
            # Customer satisfaction
            satisfaction = self.lean_tracker.calculate_customer_satisfaction_metrics()
            logger.info(f"😊 Customer Satisfaction:")
            logger.info(f"   • Overall Score: {satisfaction['overall_satisfaction_score']:.1%}")
            logger.info(f"   • Timing Satisfaction: {satisfaction['timing_satisfaction']:.1%}")
            logger.info(f"   • Communication Satisfaction: {satisfaction['communication_satisfaction']:.1%}")
            
            # KPI Dashboard
            dashboard = self.lean_tracker.get_kpi_dashboard()
            logger.info(f"📈 Overall Performance Score: {dashboard['overall_performance_score']:.1f}/100")
            
            priorities = dashboard['improvement_priorities']
            if priorities:
                logger.info(f"🎯 Top Improvement Priority: {priorities[0]['area']}")
                logger.info(f"   Current: {priorities[0]['current']:.2f}, Target: {priorities[0]['target']:.2f}")
            
        except Exception as e:
            logger.error(f"Error in lean metrics demo: {e}")
    
    def demo_ab_testing(self):
        """Demonstrate A/B testing framework"""
        logger.info("\n" + "="*50)
        logger.info("A/B TESTING DEMO")
        logger.info("="*50)
        
        try:
            # Create sample A/B tests
            logger.info("🧪 Creating A/B Tests:")
            
            # Referee selection test
            ref_test = self.ab_testing.create_referee_selection_test(
                "AI vs Manual Referee Selection",
                "Compare AI-assisted referee selection with manual selection"
            )
            
            logger.info(f"   • Test 1: {ref_test.name}")
            logger.info(f"     Variants: {len(ref_test.variants)}")
            logger.info(f"     Metrics: {len(ref_test.metrics)}")
            
            for variant in ref_test.variants:
                logger.info(f"       - {variant.name}: {variant.allocation_percent}% allocation")
            
            for metric in ref_test.metrics:
                primary = " (PRIMARY)" if metric.primary else ""
                logger.info(f"       - {metric.name}: {metric.goal}{primary}")
            
            # Reminder strategy test
            reminder_test = self.ab_testing.create_reminder_strategy_test(
                "Reminder Frequency Optimization",
                "Test different reminder frequencies and personalization"
            )
            
            logger.info(f"   • Test 2: {reminder_test.name}")
            logger.info(f"     Variants: {len(reminder_test.variants)}")
            
            # Sample size calculation
            sample_size = ref_test.calculate_sample_size(
                baseline_rate=0.7,  # 70% acceptance rate
                minimum_detectable_effect=0.1  # 10% improvement
            )
            
            logger.info(f"📊 Statistical Design:")
            logger.info(f"   • Required Sample Size: {sample_size} per variant")
            logger.info(f"   • Confidence Level: {ref_test.confidence_level:.1%}")
            logger.info(f"   • Minimum Effect Size: {ref_test.minimum_effect_size:.1%}")
            
            logger.info("💡 A/B Testing Capabilities:")
            logger.info("   • Automated variant assignment")
            logger.info("   • Statistical significance testing")
            logger.info("   • Real-time results tracking")
            logger.info("   • Recommendation generation")
            
        except Exception as e:
            logger.error(f"Error in A/B testing demo: {e}")
    
    def demo_api_server(self):
        """Demonstrate API server capabilities"""
        logger.info("\n" + "="*50)
        logger.info("API SERVER DEMO")
        logger.info("="*50)
        
        try:
            logger.info("🌐 Analytics API Server:")
            logger.info("   • FastAPI-based REST API")
            logger.info("   • Comprehensive endpoint coverage")
            logger.info("   • Real-time analytics")
            logger.info("   • CORS-enabled for web dashboards")
            
            # Create API instance
            api = create_api(self.db_path)
            
            logger.info("\n📚 Available Endpoints:")
            
            endpoints = [
                ("GET /health", "Health check and system status"),
                ("GET /analytics/referee/{id}", "Individual referee metrics"),
                ("GET /analytics/referee/{id}/trends", "Historical trends"),
                ("POST /analytics/predict/response", "Response probability prediction"),
                ("POST /analytics/predict/timeline", "Timeline prediction"),
                ("GET /analytics/network/structure", "Network analysis"),
                ("GET /analytics/lean/dashboard", "Lean KPI dashboard"),
                ("GET /analytics/ab-tests", "Active A/B tests"),
                ("GET /analytics/comparative/top-performers", "Top performers ranking")
            ]
            
            for endpoint, description in endpoints:
                logger.info(f"   • {endpoint:<35} {description}")
            
            logger.info(f"\n🚀 To start the API server:")
            logger.info(f"   python -m analytics.api.dashboard_api")
            logger.info(f"   Then visit: http://localhost:8000/docs")
            
        except Exception as e:
            logger.error(f"Error in API demo: {e}")
    
    def _create_sample_data(self):
        """Create minimal sample data for demo"""
        import sqlite3
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create sample referee
            cursor.execute("""
                INSERT OR IGNORE INTO referees 
                (id, name, email, institution, expertise, active, h_index)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'demo_referee_001',
                'Dr. Demo Reviewer',
                'demo@example.com',
                'Demo University',
                json.dumps({"optimization": 0.9, "machine_learning": 0.7}),
                1,
                25
            ))
            
            # Create sample manuscript
            cursor.execute("""
                INSERT OR IGNORE INTO manuscripts 
                (id, title, journal, submitted_date, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                'demo_manuscript_001',
                'A Novel Optimization Algorithm',
                'SICON',
                '2024-01-01',
                'under_review'
            ))
            
            # Create sample review history
            cursor.execute("""
                INSERT OR IGNORE INTO review_history
                (id, manuscript_id, referee_id, invited_date, responded_date, 
                 decision, submitted_date, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'demo_review_001',
                'demo_manuscript_001',
                'demo_referee_001',
                '2024-01-02',
                '2024-01-04',
                'accepted',
                '2024-01-20',
                8.5
            ))
            
            conn.commit()
            
        logger.info("✅ Sample data created for demo")
    
    def run_full_demo(self):
        """Run the complete analytics system demonstration"""
        logger.info("🚀 Starting Editorial Scripts Analytics System Demo")
        logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"💾 Database: {self.db_path}")
        
        try:
            # Run all demos
            self.demo_referee_analytics()
            self.demo_predictive_analytics()
            self.demo_network_analysis()
            self.demo_quality_analysis()
            self.demo_lean_metrics()
            self.demo_ab_testing()
            self.demo_api_server()
            
            logger.info("\n" + "="*50)
            logger.info("DEMO COMPLETED SUCCESSFULLY! ✅")
            logger.info("="*50)
            
            logger.info("\n📋 Next Steps:")
            logger.info("1. Install requirements: pip install -r analytics_requirements.txt")
            logger.info("2. Configure database connection")
            logger.info("3. Import your existing referee data")
            logger.info("4. Start the API server for real-time analytics")
            logger.info("5. Build custom dashboards using the API")
            logger.info("6. Set up automated A/B tests")
            logger.info("7. Monitor lean metrics for continuous improvement")
            
        except Exception as e:
            logger.error(f"Demo failed with error: {e}")
            raise


def main():
    """Main entry point for the demo"""
    print("🎯 Editorial Scripts Analytics System")
    print("=" * 50)
    print("Comprehensive Demo of Advanced Analytics Capabilities")
    print("=" * 50)
    
    # Initialize and run demo
    demo = AnalyticsSystemDemo()
    demo.run_full_demo()


if __name__ == "__main__":
    main()