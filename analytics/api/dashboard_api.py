"""
Analytics Dashboard API for editorial metrics and insights
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..core.referee_analytics import RefereeAnalytics
from ..core.comparative_analytics import ComparativeRefereeAnalytics
from ..predictive.response_predictor import ResponsePredictor
from ..predictive.timeline_predictor import TimelinePredictor
from ..quality.review_analyzer import ReviewQualityAnalyzer
from ..network.referee_network import RefereeNetworkAnalyzer
from ..lean.metrics_tracker import LeanMetricsTracker
from ..lean.ab_testing import ABTestingFramework

logger = logging.getLogger(__name__)

# Pydantic models for API
class RefereeMetricsRequest(BaseModel):
    referee_id: str
    force_refresh: bool = False

class PredictionRequest(BaseModel):
    referee_id: str
    manuscript_data: Dict[str, Any]

class QualityAnalysisRequest(BaseModel):
    review_id: str

class NetworkAnalysisRequest(BaseModel):
    referee_id: Optional[str] = None
    analysis_type: str = Field(..., description="One of: structure, communities, connectors, position")

class LeanMetricsRequest(BaseModel):
    journal_id: Optional[str] = None
    days: int = 90

class ABTestRequest(BaseModel):
    test_type: str
    name: str
    description: str

# API Response models
class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]


class AnalyticsDashboardAPI:
    """FastAPI application for analytics dashboard"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.app = FastAPI(
            title="Editorial Analytics API",
            description="Comprehensive analytics API for editorial workflow optimization",
            version="1.0.0"
        )
        
        # Initialize analytics components
        self.referee_analytics = RefereeAnalytics(db_path)
        self.comparative_analytics = ComparativeRefereeAnalytics(db_path)
        self.response_predictor = ResponsePredictor(db_path)
        self.timeline_predictor = TimelinePredictor(db_path)
        self.quality_analyzer = ReviewQualityAnalyzer(db_path)
        self.network_analyzer = RefereeNetworkAnalyzer(db_path)
        self.lean_tracker = LeanMetricsTracker(db_path)
        self.ab_testing = ABTestingFramework(db_path)
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            return HealthResponse(
                status="healthy",
                version="1.0.0",
                components={
                    "referee_analytics": "operational",
                    "predictive_models": "operational",
                    "quality_analyzer": "operational",
                    "network_analyzer": "operational",
                    "lean_tracker": "operational",
                    "ab_testing": "operational"
                }
            )
        
        # Referee Analytics Endpoints
        @self.app.get("/analytics/referee/{referee_id}", response_model=APIResponse)
        async def get_referee_metrics(
            referee_id: str = Path(..., description="Referee ID"),
            force_refresh: bool = Query(False, description="Force metrics recalculation")
        ):
            """Get comprehensive metrics for a referee"""
            try:
                metrics = self.referee_analytics.calculate_referee_metrics(
                    referee_id, force_refresh
                )
                return APIResponse(success=True, data=metrics.to_dict())
            except Exception as e:
                logger.error(f"Error getting referee metrics: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/referee/{referee_id}/trends", response_model=APIResponse)
        async def get_referee_trends(
            referee_id: str = Path(..., description="Referee ID"),
            days: int = Query(90, description="Number of days for trend analysis")
        ):
            """Get historical trends for a referee"""
            try:
                trends = self.referee_analytics.get_referee_trends(referee_id, days)
                return APIResponse(success=True, data=trends)
            except Exception as e:
                logger.error(f"Error getting referee trends: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/referee/{referee_id}/percentiles", response_model=APIResponse)
        async def get_referee_percentiles(
            referee_id: str = Path(..., description="Referee ID")
        ):
            """Get percentile rankings for a referee"""
            try:
                percentiles = self.comparative_analytics.calculate_percentile_ranks(referee_id)
                return APIResponse(success=True, data=percentiles.__dict__)
            except Exception as e:
                logger.error(f"Error getting referee percentiles: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/referee/{referee_id}/comparison", response_model=APIResponse)
        async def get_peer_comparison(
            referee_id: str = Path(..., description="Referee ID")
        ):
            """Get peer comparison for a referee"""
            try:
                comparison = self.comparative_analytics.get_peer_comparison(referee_id)
                return APIResponse(success=True, data=comparison)
            except Exception as e:
                logger.error(f"Error getting peer comparison: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Predictive Analytics Endpoints
        @self.app.post("/analytics/predict/response", response_model=APIResponse)
        async def predict_response(request: PredictionRequest):
            """Predict referee response probability"""
            try:
                prediction = self.response_predictor.predict_response_probability(
                    request.referee_id, request.manuscript_data
                )
                return APIResponse(success=True, data=prediction)
            except Exception as e:
                logger.error(f"Error predicting response: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/analytics/predict/timeline", response_model=APIResponse)
        async def predict_timeline(request: PredictionRequest):
            """Predict review timeline"""
            try:
                current_workload = request.manuscript_data.get('current_workload', 0)
                prediction = self.timeline_predictor.predict_review_timeline(
                    request.referee_id, current_workload, request.manuscript_data
                )
                return APIResponse(success=True, data=prediction)
            except Exception as e:
                logger.error(f"Error predicting timeline: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/predict/model-performance", response_model=APIResponse)
        async def get_model_performance():
            """Get predictive model performance metrics"""
            try:
                performance = self.response_predictor.get_model_performance()
                return APIResponse(success=True, data=performance)
            except Exception as e:
                logger.error(f"Error getting model performance: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Quality Analysis Endpoints
        @self.app.get("/analytics/quality/review/{review_id}", response_model=APIResponse)
        async def analyze_review_quality(
            review_id: str = Path(..., description="Review ID")
        ):
            """Analyze quality of a specific review"""
            try:
                analysis = self.quality_analyzer.analyze_review_quality(review_id)
                return APIResponse(success=True, data=analysis.__dict__)
            except Exception as e:
                logger.error(f"Error analyzing review quality: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/quality/referee/{referee_id}/trends", response_model=APIResponse)
        async def get_quality_trends(
            referee_id: str = Path(..., description="Referee ID"),
            limit: int = Query(20, description="Number of recent reviews to analyze")
        ):
            """Get quality trends for a referee"""
            try:
                trends = self.quality_analyzer.analyze_referee_quality_trends(
                    referee_id, limit
                )
                return APIResponse(success=True, data=trends)
            except Exception as e:
                logger.error(f"Error getting quality trends: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Network Analysis Endpoints
        @self.app.get("/analytics/network/structure", response_model=APIResponse)
        async def get_network_structure():
            """Get overall network structure analysis"""
            try:
                structure = self.network_analyzer.analyze_network_structure()
                return APIResponse(success=True, data=structure)
            except Exception as e:
                logger.error(f"Error analyzing network structure: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/network/communities", response_model=APIResponse)
        async def get_network_communities():
            """Get network communities/clusters"""
            try:
                communities = self.network_analyzer.detect_communities()
                community_data = [
                    {
                        'id': c.id,
                        'size': c.size,
                        'members': c.members,
                        'dominant_expertise': c.dominant_expertise,
                        'avg_performance': c.avg_performance,
                        'internal_density': c.internal_density
                    }
                    for c in communities
                ]
                return APIResponse(success=True, data={'communities': community_data})
            except Exception as e:
                logger.error(f"Error detecting communities: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/network/connectors", response_model=APIResponse)
        async def get_key_connectors(
            top_k: int = Query(10, description="Number of top connectors to return")
        ):
            """Get key connector nodes in the network"""
            try:
                connectors = self.network_analyzer.identify_key_connectors(top_k)
                return APIResponse(success=True, data={'connectors': connectors})
            except Exception as e:
                logger.error(f"Error identifying connectors: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/network/referee/{referee_id}/position", response_model=APIResponse)
        async def get_referee_position(
            referee_id: str = Path(..., description="Referee ID")
        ):
            """Get referee's position in the network"""
            try:
                position = self.network_analyzer.analyze_referee_position(referee_id)
                return APIResponse(success=True, data=position)
            except Exception as e:
                logger.error(f"Error analyzing referee position: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/network/referee/{referee_id}/collaborations", response_model=APIResponse)
        async def find_collaboration_opportunities(
            referee_id: str = Path(..., description="Referee ID"),
            limit: int = Query(5, description="Number of opportunities to return")
        ):
            """Find collaboration opportunities for a referee"""
            try:
                opportunities = self.network_analyzer.find_collaboration_opportunities(
                    referee_id, limit
                )
                return APIResponse(success=True, data={'opportunities': opportunities})
            except Exception as e:
                logger.error(f"Error finding collaborations: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/network/expertise", response_model=APIResponse)
        async def get_expertise_clusters():
            """Get expertise-based clustering analysis"""
            try:
                clusters = self.network_analyzer.analyze_expertise_clusters()
                return APIResponse(success=True, data=clusters)
            except Exception as e:
                logger.error(f"Error analyzing expertise clusters: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Lean Metrics Endpoints
        @self.app.get("/analytics/lean/cycle-time", response_model=APIResponse)
        async def get_cycle_time_metrics(
            journal_id: Optional[str] = Query(None, description="Journal ID"),
            days: int = Query(90, description="Number of days to analyze")
        ):
            """Get cycle time metrics"""
            try:
                metrics = self.lean_tracker.calculate_cycle_time_metrics(journal_id, days)
                return APIResponse(success=True, data=metrics)
            except Exception as e:
                logger.error(f"Error calculating cycle time: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/lean/value-stream/{journal_id}", response_model=APIResponse)
        async def get_value_stream_analysis(
            journal_id: str = Path(..., description="Journal ID")
        ):
            """Get value stream analysis for a journal"""
            try:
                analysis = self.lean_tracker.analyze_value_stream(journal_id)
                return APIResponse(success=True, data=analysis.__dict__)
            except Exception as e:
                logger.error(f"Error analyzing value stream: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/lean/automation", response_model=APIResponse)
        async def get_automation_metrics():
            """Get automation metrics"""
            try:
                metrics = self.lean_tracker.calculate_automation_metrics()
                return APIResponse(success=True, data=metrics)
            except Exception as e:
                logger.error(f"Error calculating automation metrics: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/lean/quality", response_model=APIResponse)
        async def get_quality_metrics(
            journal_id: Optional[str] = Query(None, description="Journal ID")
        ):
            """Get quality metrics"""
            try:
                metrics = self.lean_tracker.calculate_quality_metrics(journal_id)
                return APIResponse(success=True, data=metrics)
            except Exception as e:
                logger.error(f"Error calculating quality metrics: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/lean/satisfaction", response_model=APIResponse)
        async def get_satisfaction_metrics():
            """Get customer satisfaction metrics"""
            try:
                metrics = self.lean_tracker.calculate_customer_satisfaction_metrics()
                return APIResponse(success=True, data=metrics)
            except Exception as e:
                logger.error(f"Error calculating satisfaction metrics: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/lean/dashboard", response_model=APIResponse)
        async def get_lean_dashboard(
            journal_id: Optional[str] = Query(None, description="Journal ID")
        ):
            """Get comprehensive lean KPI dashboard"""
            try:
                dashboard = self.lean_tracker.get_kpi_dashboard(journal_id)
                return APIResponse(success=True, data=dashboard)
            except Exception as e:
                logger.error(f"Error getting lean dashboard: {e}")
                return APIResponse(success=False, error=str(e))
        
        # A/B Testing Endpoints
        @self.app.get("/analytics/ab-tests", response_model=APIResponse)
        async def get_active_tests():
            """Get all active A/B tests"""
            try:
                tests = self.ab_testing.get_active_tests()
                return APIResponse(success=True, data={'tests': tests})
            except Exception as e:
                logger.error(f"Error getting active tests: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/analytics/ab-tests/referee-selection", response_model=APIResponse)
        async def create_referee_selection_test(request: ABTestRequest):
            """Create A/B test for referee selection"""
            try:
                test = self.ab_testing.create_referee_selection_test(
                    request.name, request.description
                )
                test_id = self.ab_testing.start_test(test)
                return APIResponse(success=True, data={
                    'test_id': test_id,
                    'test_config': test.to_dict()
                })
            except Exception as e:
                logger.error(f"Error creating test: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/analytics/ab-tests/reminder-strategy", response_model=APIResponse)
        async def create_reminder_strategy_test(request: ABTestRequest):
            """Create A/B test for reminder strategies"""
            try:
                test = self.ab_testing.create_reminder_strategy_test(
                    request.name, request.description
                )
                test_id = self.ab_testing.start_test(test)
                return APIResponse(success=True, data={
                    'test_id': test_id,
                    'test_config': test.to_dict()
                })
            except Exception as e:
                logger.error(f"Error creating test: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/ab-tests/{test_id}/analysis", response_model=APIResponse)
        async def analyze_test(
            test_id: str = Path(..., description="Test ID")
        ):
            """Analyze A/B test results"""
            try:
                analysis = self.ab_testing.analyze_test(test_id)
                return APIResponse(success=True, data=analysis)
            except Exception as e:
                logger.error(f"Error analyzing test: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Comparative Analytics Endpoints
        @self.app.get("/analytics/comparative/top-performers", response_model=APIResponse)
        async def get_top_performers(
            limit: int = Query(10, description="Number of top performers"),
            category: Optional[str] = Query(None, description="Category: speed, quality, reliability")
        ):
            """Get top performing referees"""
            try:
                performers = self.comparative_analytics.identify_top_performers(limit, category)
                return APIResponse(success=True, data={'top_performers': performers})
            except Exception as e:
                logger.error(f"Error getting top performers: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/comparative/distribution/{metric_type}", response_model=APIResponse)
        async def get_performance_distribution(
            metric_type: str = Path(..., description="Metric type: overall, speed, quality, reliability")
        ):
            """Get performance distribution across all referees"""
            try:
                distribution = self.comparative_analytics.get_performance_distribution(metric_type)
                return APIResponse(success=True, data=distribution)
            except Exception as e:
                logger.error(f"Error getting distribution: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/comparative/journal/{journal_id}/benchmark", response_model=APIResponse)
        async def get_journal_benchmark(
            journal_id: str = Path(..., description="Journal ID")
        ):
            """Get benchmark metrics for a journal"""
            try:
                benchmark = self.comparative_analytics.benchmark_by_journal(journal_id)
                return APIResponse(success=True, data=benchmark)
            except Exception as e:
                logger.error(f"Error getting journal benchmark: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/comparative/expertise/{expertise_area}/benchmark", response_model=APIResponse)
        async def get_expertise_benchmark(
            expertise_area: str = Path(..., description="Expertise area")
        ):
            """Get benchmark metrics for an expertise area"""
            try:
                benchmark = self.comparative_analytics.benchmark_by_expertise(expertise_area)
                return APIResponse(success=True, data=benchmark)
            except Exception as e:
                logger.error(f"Error getting expertise benchmark: {e}")
                return APIResponse(success=False, error=str(e))
        
        # Timeline Analysis Endpoints
        @self.app.get("/analytics/timeline/referee/{referee_id}/factors", response_model=APIResponse)
        async def get_timeline_factors(
            referee_id: str = Path(..., description="Referee ID")
        ):
            """Analyze factors affecting referee's review timelines"""
            try:
                factors = self.timeline_predictor.analyze_timeline_factors(referee_id)
                return APIResponse(success=True, data=factors)
            except Exception as e:
                logger.error(f"Error analyzing timeline factors: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/analytics/timeline/referee/{referee_id}/compliance", response_model=APIResponse)
        async def predict_deadline_compliance(
            referee_id: str = Path(..., description="Referee ID"),
            deadline_days: int = Query(21, description="Deadline in days")
        ):
            """Predict deadline compliance probability"""
            try:
                compliance = self.timeline_predictor.predict_deadline_compliance(
                    referee_id, deadline_days
                )
                return APIResponse(success=True, data=compliance)
            except Exception as e:
                logger.error(f"Error predicting compliance: {e}")
                return APIResponse(success=False, error=str(e))
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """Run the API server"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            debug=debug,
            reload=debug
        )


# Create API instance
def create_api(db_path: str = "data/referees.db") -> AnalyticsDashboardAPI:
    """Create and return API instance"""
    return AnalyticsDashboardAPI(db_path)


if __name__ == "__main__":
    # Run the API server
    api = create_api()
    api.run(debug=True)