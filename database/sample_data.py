#!/usr/bin/env python3
"""
Sample data loader for Editorial Scripts database
Creates realistic test data for development and testing
"""

import asyncio
import asyncpg
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import random
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config import settings

class SampleDataLoader:
    """Loads sample data into the database"""
    
    def __init__(self):
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        self.conn = await asyncpg.connect(
            user=settings.database.user,
            password=settings.database.password,
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name
        )
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            await self.conn.close()
    
    def generate_referees(self) -> List[Dict[str, Any]]:
        """Generate sample referee data"""
        
        institutions = [
            "MIT", "Stanford University", "Harvard University", "UC Berkeley",
            "Princeton University", "Carnegie Mellon", "Caltech", "Yale University",
            "University of Toronto", "Oxford University", "Cambridge University",
            "ETH Zurich", "EPFL", "University of Tokyo", "KAIST",
            "Technical University of Munich", "Imperial College London"
        ]
        
        expertise_areas = [
            "optimization", "machine learning", "numerical analysis", "control theory",
            "computational finance", "operations research", "mathematical modeling",
            "algorithm design", "probability theory", "statistics", "linear algebra",
            "differential equations", "scientific computing", "data science",
            "artificial intelligence", "network analysis", "game theory"
        ]
        
        first_names = [
            "Sarah", "Michael", "Jennifer", "David", "Lisa", "James", "Maria", "Robert",
            "Emma", "John", "Anna", "Christopher", "Laura", "Matthew", "Jessica",
            "Daniel", "Amy", "Andrew", "Michelle", "Brian", "Nicole", "Kevin"
        ]
        
        last_names = [
            "Chen", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
            "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson"
        ]
        
        referees = []
        for i in range(50):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            name = f"{'Dr.' if random.random() < 0.7 else 'Prof.'} {first_name} {last_name}"
            
            # Generate expertise (2-4 areas)
            ref_expertise = random.sample(expertise_areas, random.randint(2, 4))
            
            # Generate journal coverage (1-3 journals)
            journals = random.sample(['SICON', 'SIFIN', 'MF', 'MOR', 'JOTA', 'FS'], random.randint(1, 3))
            
            referee = {
                'id': str(uuid.uuid4()),
                'name': name,
                'email': f"{first_name.lower()}.{last_name.lower()}@{random.choice(['edu', 'ac.uk', 'org'])}",
                'institution': random.choice(institutions),
                'expertise_areas': ref_expertise,
                'journals': journals,
                'status': random.choices(['active', 'inactive'], weights=[0.85, 0.15])[0],
                'workload_score': round(random.uniform(0.1, 0.9), 2),
                'quality_score': round(random.uniform(0.6, 0.95), 2),
                'response_time_avg': random.randint(3, 21),  # 3-21 days
                'acceptance_rate': round(random.uniform(0.4, 0.8), 2),
                'metadata': {
                    'years_experience': random.randint(3, 25),
                    'total_reviews': random.randint(5, 150),
                    'preferred_areas': ref_expertise[:2]
                }
            }
            referees.append(referee)
        
        return referees
    
    def generate_manuscripts(self) -> List[Dict[str, Any]]:
        """Generate sample manuscript data"""
        
        title_templates = [
            "A Novel Approach to {topic} in {domain}",
            "Efficient Algorithms for {topic} Problems",
            "On the {property} of {topic} Methods",
            "Optimization Techniques for {domain} Applications",
            "Convergence Analysis of {topic} Algorithms",
            "Machine Learning Approaches to {domain}",
            "Numerical Methods for {topic} in {domain}",
            "Robust {topic} under {constraint} Constraints"
        ]
        
        topics = [
            "convex optimization", "linear programming", "nonlinear optimization",
            "stochastic programming", "integer programming", "semidefinite programming",
            "portfolio optimization", "risk management", "derivative pricing",
            "numerical analysis", "finite element methods", "spectral methods"
        ]
        
        domains = [
            "Financial Mathematics", "Scientific Computing", "Operations Research",
            "Control Theory", "Machine Learning", "Signal Processing"
        ]
        
        properties = [
            "Convergence Properties", "Stability Analysis", "Computational Complexity",
            "Robustness", "Efficiency", "Accuracy"
        ]
        
        constraints = [
            "Resource", "Budget", "Time", "Uncertainty", "Noise"
        ]
        
        manuscripts = []
        for i in range(25):
            template = random.choice(title_templates)
            title = template.format(
                topic=random.choice(topics),
                domain=random.choice(domains),
                property=random.choice(properties),
                constraint=random.choice(constraints)
            )
            
            # Generate abstract
            abstract = f"This paper presents a comprehensive study of {random.choice(topics)} " \
                      f"with applications to {random.choice(domains).lower()}. " \
                      f"We develop novel theoretical results and demonstrate " \
                      f"improved performance over existing methods. " \
                      f"Extensive numerical experiments validate our approach."
            
            # Generate keywords
            keywords = random.sample([
                "optimization", "algorithm", "convergence", "numerical methods",
                "computational efficiency", "mathematical modeling", "analysis",
                "machine learning", "statistics", "probability"
            ], random.randint(3, 6))
            
            # Generate authors
            num_authors = random.randint(1, 4)
            authors = [f"Author {i+1}" for i in range(num_authors)]
            
            manuscript = {
                'id': str(uuid.uuid4()),
                'title': title,
                'abstract': abstract,
                'keywords': keywords,
                'authors': authors,
                'journal_code': random.choice(['SICON', 'SIFIN', 'MF', 'MOR', 'JOTA', 'FS']),
                'submission_date': datetime.now() - timedelta(days=random.randint(1, 365)),
                'status': random.choices(
                    ['submitted', 'under_review', 'accepted', 'rejected'],
                    weights=[0.3, 0.4, 0.2, 0.1]
                )[0],
                'metadata': {
                    'pages': random.randint(15, 45),
                    'figures': random.randint(3, 12),
                    'references': random.randint(20, 80),
                    'submission_round': random.randint(1, 3)
                }
            }
            manuscripts.append(manuscript)
        
        return manuscripts
    
    def generate_reviews(self, manuscripts: List[Dict], referees: List[Dict]) -> List[Dict[str, Any]]:
        """Generate sample review data"""
        reviews = []
        
        for manuscript in manuscripts:
            if manuscript['status'] in ['under_review', 'accepted', 'rejected']:
                # Assign 2-3 referees per manuscript
                num_referees = random.randint(2, 3)
                selected_referees = random.sample(referees, num_referees)
                
                for referee in selected_referees:
                    invitation_date = manuscript['submission_date'] + timedelta(days=random.randint(1, 7))
                    response_date = invitation_date + timedelta(days=random.randint(1, referee['response_time_avg']))
                    review_date = response_date + timedelta(days=random.randint(14, 45))
                    
                    review = {
                        'id': str(uuid.uuid4()),
                        'manuscript_id': manuscript['id'],
                        'referee_id': referee['id'],
                        'invitation_date': invitation_date,
                        'response_date': response_date,
                        'review_submitted_date': review_date,
                        'decision': random.choices(
                            ['accept', 'reject', 'major_revision', 'minor_revision'],
                            weights=[0.2, 0.1, 0.4, 0.3]
                        )[0],
                        'quality_score': round(random.uniform(0.6, 0.95), 2),
                        'timeliness_score': round(random.uniform(0.7, 1.0), 2),
                        'review_content': "This is a sample review content. The manuscript presents interesting ideas...",
                        'metadata': {
                            'recommendation_confidence': round(random.uniform(0.6, 0.9), 2),
                            'expertise_match': round(random.uniform(0.7, 0.95), 2)
                        }
                    }
                    reviews.append(review)
        
        return reviews
    
    def generate_analytics(self, referees: List[Dict], manuscripts: List[Dict]) -> tuple:
        """Generate sample analytics data"""
        
        # Referee analytics
        referee_analytics = []
        current_date = date.today()
        
        for referee in referees:
            for months_back in [1, 3, 6, 12]:
                period_end = current_date
                period_start = current_date - timedelta(days=months_back * 30)
                
                analytics = {
                    'id': str(uuid.uuid4()),
                    'referee_id': referee['id'],
                    'journal_code': random.choice(referee['journals']),
                    'period_start': period_start,
                    'period_end': period_end,
                    'total_invitations': random.randint(2, 15),
                    'total_acceptances': random.randint(1, 12),
                    'total_reviews': random.randint(1, 10),
                    'avg_response_time': round(random.uniform(2.0, 14.0), 2),
                    'avg_review_time': round(random.uniform(14.0, 35.0), 2),
                    'quality_metrics': {
                        'review_thoroughness': round(random.uniform(0.7, 0.95), 2),
                        'recommendation_accuracy': round(random.uniform(0.6, 0.9), 2),
                        'constructive_feedback': round(random.uniform(0.8, 0.95), 2)
                    },
                    'performance_tier': random.choices(
                        ['excellent', 'good', 'fair', 'poor'],
                        weights=[0.2, 0.5, 0.25, 0.05]
                    )[0]
                }
                referee_analytics.append(analytics)
        
        # Journal analytics
        journal_analytics = []
        journals = ['SICON', 'SIFIN', 'MF', 'MOR', 'JOTA', 'FS']
        
        for journal in journals:
            for months_back in [1, 3, 6, 12]:
                period_end = current_date
                period_start = current_date - timedelta(days=months_back * 30)
                
                total_subs = random.randint(10, 50)
                desk_rejects = random.randint(2, total_subs // 3)
                
                analytics = {
                    'id': str(uuid.uuid4()),
                    'journal_code': journal,
                    'period_start': period_start,
                    'period_end': period_end,
                    'total_submissions': total_subs,
                    'total_desk_rejections': desk_rejects,
                    'total_accepted': random.randint(2, (total_subs - desk_rejects) // 2),
                    'total_rejected': random.randint(1, (total_subs - desk_rejects) // 3),
                    'avg_review_time': round(random.uniform(45.0, 90.0), 2),
                    'avg_time_to_decision': round(random.uniform(60.0, 120.0), 2),
                    'referee_pool_size': random.randint(20, 80),
                    'metrics': {
                        'acceptance_rate': round(random.uniform(0.15, 0.35), 2),
                        'desk_rejection_rate': round(desk_rejects / total_subs, 2),
                        'avg_rounds_to_decision': round(random.uniform(1.2, 2.1), 1)
                    }
                }
                journal_analytics.append(analytics)
        
        return referee_analytics, journal_analytics
    
    async def load_referees(self, referees: List[Dict]):
        """Load referee data"""
        print(f"  Loading {len(referees)} referees...")
        
        for referee in referees:
            await self.conn.execute("""
                INSERT INTO referees (
                    id, name, email, institution, expertise_areas, journals,
                    status, workload_score, quality_score, response_time_avg,
                    acceptance_rate, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, 
                uuid.UUID(referee['id']),
                referee['name'],
                referee['email'],
                referee['institution'],
                referee['expertise_areas'],
                referee['journals'],
                referee['status'],
                referee['workload_score'],
                referee['quality_score'],
                referee['response_time_avg'],
                referee['acceptance_rate'],
                json.dumps(referee['metadata'])
            )
    
    async def load_manuscripts(self, manuscripts: List[Dict]):
        """Load manuscript data"""
        print(f"  Loading {len(manuscripts)} manuscripts...")
        
        for manuscript in manuscripts:
            await self.conn.execute("""
                INSERT INTO manuscripts (
                    id, title, abstract, keywords, authors, journal_code,
                    submission_date, status, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                uuid.UUID(manuscript['id']),
                manuscript['title'],
                manuscript['abstract'],
                manuscript['keywords'],
                manuscript['authors'],
                manuscript['journal_code'],
                manuscript['submission_date'],
                manuscript['status'],
                json.dumps(manuscript['metadata'])
            )
    
    async def load_reviews(self, reviews: List[Dict]):
        """Load review data"""
        print(f"  Loading {len(reviews)} reviews...")
        
        for review in reviews:
            await self.conn.execute("""
                INSERT INTO reviews (
                    id, manuscript_id, referee_id, invitation_date,
                    response_date, review_submitted_date, decision,
                    quality_score, timeliness_score, review_content, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                uuid.UUID(review['id']),
                uuid.UUID(review['manuscript_id']),
                uuid.UUID(review['referee_id']),
                review['invitation_date'],
                review['response_date'],
                review['review_submitted_date'],
                review['decision'],
                review['quality_score'],
                review['timeliness_score'],
                review['review_content'],
                json.dumps(review['metadata'])
            )
    
    async def load_analytics(self, referee_analytics: List[Dict], journal_analytics: List[Dict]):
        """Load analytics data"""
        print(f"  Loading {len(referee_analytics)} referee analytics records...")
        
        for analytics in referee_analytics:
            await self.conn.execute("""
                INSERT INTO referee_analytics (
                    id, referee_id, journal_code, period_start, period_end,
                    total_invitations, total_acceptances, total_reviews,
                    avg_response_time, avg_review_time, quality_metrics, performance_tier
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                uuid.UUID(analytics['id']),
                uuid.UUID(analytics['referee_id']),
                analytics['journal_code'],
                analytics['period_start'],
                analytics['period_end'],
                analytics['total_invitations'],
                analytics['total_acceptances'],
                analytics['total_reviews'],
                analytics['avg_response_time'],
                analytics['avg_review_time'],
                json.dumps(analytics['quality_metrics']),
                analytics['performance_tier']
            )
        
        print(f"  Loading {len(journal_analytics)} journal analytics records...")
        
        for analytics in journal_analytics:
            await self.conn.execute("""
                INSERT INTO journal_analytics (
                    id, journal_code, period_start, period_end,
                    total_submissions, total_desk_rejections, total_accepted,
                    total_rejected, avg_review_time, avg_time_to_decision,
                    referee_pool_size, metrics
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                uuid.UUID(analytics['id']),
                analytics['journal_code'],
                analytics['period_start'],
                analytics['period_end'],
                analytics['total_submissions'],
                analytics['total_desk_rejections'],
                analytics['total_accepted'],
                analytics['total_rejected'],
                analytics['avg_review_time'],
                analytics['avg_time_to_decision'],
                analytics['referee_pool_size'],
                json.dumps(analytics['metrics'])
            )
    
    async def load_sample_data(self):
        """Load all sample data"""
        print("🎯 Generating sample data...")
        
        # Generate data
        referees = self.generate_referees()
        manuscripts = self.generate_manuscripts()
        reviews = self.generate_reviews(manuscripts, referees)
        referee_analytics, journal_analytics = self.generate_analytics(referees, manuscripts)
        
        print("📊 Loading sample data into database...")
        
        # Load data in order (respecting foreign keys)
        await self.load_referees(referees)
        await self.load_manuscripts(manuscripts)
        await self.load_reviews(reviews)
        await self.load_analytics(referee_analytics, journal_analytics)
        
        print("✅ Sample data loaded successfully!")
        print()
        print("📈 Data Summary:")
        print(f"  Referees: {len(referees)}")
        print(f"  Manuscripts: {len(manuscripts)}")
        print(f"  Reviews: {len(reviews)}")
        print(f"  Referee Analytics: {len(referee_analytics)}")
        print(f"  Journal Analytics: {len(journal_analytics)}")


async def main():
    """Main function"""
    loader = SampleDataLoader()
    
    try:
        await loader.connect()
        await loader.load_sample_data()
    except Exception as e:
        print(f"❌ Error loading sample data: {e}")
        return False
    finally:
        await loader.disconnect()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)