"""
Referee database management system
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class RefereeProfile:
    """Referee profile data structure"""
    name: str
    email: str
    institution: str = ""
    expertise: List[str] = None
    relationship: str = "standard"  # friend, colleague, standard
    notes: str = ""
    h_index: Optional[int] = None
    last_contact: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.expertise is None:
            self.expertise = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ReviewRecord:
    """Single review record"""
    referee_email: str
    manuscript_id: str
    journal: str
    invited_date: datetime
    responded_date: Optional[datetime] = None
    decision: Optional[str] = None  # accepted, declined, no_response
    review_submitted_date: Optional[datetime] = None
    report_quality_score: Optional[float] = None
    days_late: int = 0
    reminder_count: int = 0

class RefereeDatabase:
    """Main referee database manager"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Referee profiles
                CREATE TABLE IF NOT EXISTS referees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    institution TEXT,
                    expertise TEXT,  -- JSON array
                    relationship TEXT DEFAULT 'standard' CHECK(relationship IN ('friend', 'colleague', 'standard')),
                    notes TEXT,
                    h_index INTEGER,
                    last_contact TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Review history
                CREATE TABLE IF NOT EXISTS review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_id INTEGER NOT NULL,
                    manuscript_id TEXT NOT NULL,
                    journal TEXT NOT NULL,
                    invited_date TIMESTAMP NOT NULL,
                    responded_date TIMESTAMP,
                    decision TEXT CHECK(decision IN ('accepted', 'declined', 'no_response')),
                    review_submitted_date TIMESTAMP,
                    report_quality_score REAL CHECK(report_quality_score >= 0 AND report_quality_score <= 10),
                    report_length INTEGER,
                    days_to_respond INTEGER,
                    days_to_review INTEGER,
                    days_late INTEGER DEFAULT 0,
                    reminder_count INTEGER DEFAULT 0,
                    reminder_dates TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(referee_id) REFERENCES referees(id),
                    UNIQUE(referee_id, manuscript_id, journal)
                );
                
                -- Referee performance metrics (cached calculations)
                CREATE TABLE IF NOT EXISTS referee_metrics (
                    referee_id INTEGER PRIMARY KEY,
                    total_invitations INTEGER DEFAULT 0,
                    total_accepted INTEGER DEFAULT 0,
                    total_declined INTEGER DEFAULT 0,
                    total_completed INTEGER DEFAULT 0,
                    acceptance_rate REAL,
                    completion_rate REAL,
                    avg_response_time_days REAL,
                    avg_review_time_days REAL,
                    avg_quality_score REAL,
                    on_time_rate REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(referee_id) REFERENCES referees(id)
                );
                
                -- Expertise tracking
                CREATE TABLE IF NOT EXISTS referee_expertise (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_id INTEGER NOT NULL,
                    expertise_area TEXT NOT NULL,
                    confidence_score REAL DEFAULT 0.5,
                    evidence_count INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,  -- publication, report, profile, etc.
                    FOREIGN KEY(referee_id) REFERENCES referees(id),
                    UNIQUE(referee_id, expertise_area)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_referee_email ON referees(email);
                CREATE INDEX IF NOT EXISTS idx_review_manuscript ON review_history(manuscript_id);
                CREATE INDEX IF NOT EXISTS idx_review_dates ON review_history(invited_date, review_submitted_date);
                CREATE INDEX IF NOT EXISTS idx_expertise_area ON referee_expertise(expertise_area);
                
                -- Triggers to update timestamps
                CREATE TRIGGER IF NOT EXISTS update_referee_timestamp 
                AFTER UPDATE ON referees
                BEGIN
                    UPDATE referees SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
            """)
            logger.info(f"Database initialized at {self.db_path}")
    
    def add_or_update_referee(self, profile: RefereeProfile) -> int:
        """Add or update referee profile"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if referee exists
            existing = conn.execute(
                "SELECT id FROM referees WHERE email = ?", 
                (profile.email,)
            ).fetchone()
            
            if existing:
                # Update existing
                referee_id = existing[0]
                conn.execute("""
                    UPDATE referees 
                    SET name = ?, institution = ?, expertise = ?, 
                        relationship = ?, notes = ?, h_index = ?,
                        last_contact = ?
                    WHERE id = ?
                """, (
                    profile.name,
                    profile.institution,
                    json.dumps(profile.expertise),
                    profile.relationship,
                    profile.notes,
                    profile.h_index,
                    profile.last_contact,
                    referee_id
                ))
                logger.info(f"Updated referee {profile.email}")
            else:
                # Insert new
                cursor = conn.execute("""
                    INSERT INTO referees 
                    (name, email, institution, expertise, relationship, 
                     notes, h_index, last_contact, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.name,
                    profile.email,
                    profile.institution,
                    json.dumps(profile.expertise),
                    profile.relationship,
                    profile.notes,
                    profile.h_index,
                    profile.last_contact,
                    profile.created_at
                ))
                referee_id = cursor.lastrowid
                logger.info(f"Added new referee {profile.email}")
            
            # Update expertise tracking
            if profile.expertise:
                self._update_expertise(conn, referee_id, profile.expertise)
            
            return referee_id
    
    def record_review(self, record: ReviewRecord) -> int:
        """Record a review invitation/completion"""
        with sqlite3.connect(self.db_path) as conn:
            # Get referee ID
            referee = conn.execute(
                "SELECT id FROM referees WHERE email = ?",
                (record.referee_email,)
            ).fetchone()
            
            if not referee:
                # Auto-create referee if not exists
                referee_id = self.add_or_update_referee(
                    RefereeProfile(
                        name=record.referee_email.split('@')[0],
                        email=record.referee_email
                    )
                )
            else:
                referee_id = referee[0]
            
            # Calculate time metrics
            days_to_respond = None
            days_to_review = None
            
            if record.responded_date:
                days_to_respond = (record.responded_date - record.invited_date).days
            
            if record.review_submitted_date and record.responded_date:
                days_to_review = (record.review_submitted_date - record.responded_date).days
            
            # Insert or update review record
            try:
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO review_history
                    (referee_id, manuscript_id, journal, invited_date,
                     responded_date, decision, review_submitted_date,
                     report_quality_score, days_to_respond, days_to_review,
                     days_late, reminder_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    referee_id,
                    record.manuscript_id,
                    record.journal,
                    record.invited_date,
                    record.responded_date,
                    record.decision,
                    record.review_submitted_date,
                    record.report_quality_score,
                    days_to_respond,
                    days_to_review,
                    record.days_late,
                    record.reminder_count
                ))
                
                # Update metrics
                self._update_referee_metrics(conn, referee_id)
                
                return cursor.lastrowid
                
            except sqlite3.IntegrityError:
                logger.warning(f"Review record already exists for {record.referee_email} on {record.manuscript_id}")
                return -1
    
    def get_referee_stats(self, email: str) -> Dict:
        """Get comprehensive referee statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get referee info
            referee = conn.execute(
                "SELECT * FROM referees WHERE email = ?",
                (email,)
            ).fetchone()
            
            if not referee:
                return None
            
            referee_id = referee['id']
            
            # Get cached metrics
            metrics = conn.execute(
                "SELECT * FROM referee_metrics WHERE referee_id = ?",
                (referee_id,)
            ).fetchone()
            
            # Get recent reviews
            recent_reviews = conn.execute("""
                SELECT * FROM review_history 
                WHERE referee_id = ? 
                ORDER BY invited_date DESC 
                LIMIT 10
            """, (referee_id,)).fetchall()
            
            # Get expertise areas
            expertise = conn.execute("""
                SELECT expertise_area, confidence_score 
                FROM referee_expertise 
                WHERE referee_id = ?
                ORDER BY confidence_score DESC
            """, (referee_id,)).fetchall()
            
            return {
                'profile': dict(referee),
                'metrics': dict(metrics) if metrics else {},
                'recent_reviews': [dict(r) for r in recent_reviews],
                'expertise': [dict(e) for e in expertise]
            }
    
    def find_referees_by_expertise(self, topics: List[str], 
                                  exclude_emails: List[str] = None,
                                  min_score: float = 0.5) -> List[Dict]:
        """Find referees matching given expertise topics"""
        if not topics:
            return []
        
        exclude_emails = exclude_emails or []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query
            placeholders = ','.join('?' * len(topics))
            exclude_placeholders = ','.join('?' * len(exclude_emails)) if exclude_emails else ''
            
            query = f"""
                SELECT DISTINCT r.*, 
                       AVG(e.confidence_score) as match_score,
                       COUNT(DISTINCT e.expertise_area) as matching_areas
                FROM referees r
                JOIN referee_expertise e ON r.id = e.referee_id
                WHERE e.expertise_area IN ({placeholders})
                AND e.confidence_score >= ?
            """
            
            params = topics + [min_score]
            
            if exclude_emails:
                query += f" AND r.email NOT IN ({exclude_placeholders})"
                params.extend(exclude_emails)
            
            query += """
                GROUP BY r.id
                ORDER BY match_score DESC, matching_areas DESC
            """
            
            results = conn.execute(query, params).fetchall()
            
            return [dict(r) for r in results]
    
    def get_referee_workload(self, email: str, months_back: int = 6) -> Dict:
        """Get current referee workload"""
        with sqlite3.connect(self.db_path) as conn:
            referee = conn.execute(
                "SELECT id FROM referees WHERE email = ?",
                (email,)
            ).fetchone()
            
            if not referee:
                return {'active_reviews': 0, 'completed_recently': 0}
            
            referee_id = referee[0]
            cutoff_date = datetime.now() - timedelta(days=months_back * 30)
            
            # Active reviews (invited but not completed)
            active = conn.execute("""
                SELECT COUNT(*) FROM review_history
                WHERE referee_id = ? 
                AND invited_date > ?
                AND review_submitted_date IS NULL
                AND decision != 'declined'
            """, (referee_id, cutoff_date)).fetchone()[0]
            
            # Recently completed
            completed = conn.execute("""
                SELECT COUNT(*) FROM review_history
                WHERE referee_id = ?
                AND review_submitted_date > ?
            """, (referee_id, cutoff_date)).fetchone()[0]
            
            return {
                'active_reviews': active,
                'completed_recently': completed,
                'total_recent': active + completed
            }
    
    def mark_as_friend(self, email: str) -> bool:
        """Mark a referee as a friend"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE referees SET relationship = 'friend' WHERE email = ?",
                (email,)
            )
            return result.rowcount > 0
    
    def _update_expertise(self, conn, referee_id: int, expertise_areas: List[str]):
        """Update expertise tracking for a referee"""
        for area in expertise_areas:
            conn.execute("""
                INSERT OR REPLACE INTO referee_expertise
                (referee_id, expertise_area, confidence_score, evidence_count, last_seen)
                VALUES (
                    ?,
                    ?,
                    COALESCE(
                        (SELECT confidence_score * 0.9 + 0.1 
                         FROM referee_expertise 
                         WHERE referee_id = ? AND expertise_area = ?),
                        0.5
                    ),
                    COALESCE(
                        (SELECT evidence_count + 1 
                         FROM referee_expertise 
                         WHERE referee_id = ? AND expertise_area = ?),
                        1
                    ),
                    CURRENT_TIMESTAMP
                )
            """, (referee_id, area, referee_id, area, referee_id, area))
    
    def _update_referee_metrics(self, conn, referee_id: int):
        """Update cached referee metrics"""
        # Calculate all metrics
        metrics = conn.execute("""
            SELECT 
                COUNT(*) as total_invitations,
                SUM(CASE WHEN decision = 'accepted' THEN 1 ELSE 0 END) as total_accepted,
                SUM(CASE WHEN decision = 'declined' THEN 1 ELSE 0 END) as total_declined,
                SUM(CASE WHEN review_submitted_date IS NOT NULL THEN 1 ELSE 0 END) as total_completed,
                AVG(days_to_respond) as avg_response_time,
                AVG(days_to_review) as avg_review_time,
                AVG(report_quality_score) as avg_quality,
                AVG(CASE WHEN days_late <= 0 THEN 1.0 ELSE 0.0 END) as on_time_rate
            FROM review_history
            WHERE referee_id = ?
        """, (referee_id,)).fetchone()
        
        # Calculate rates
        acceptance_rate = metrics[1] / metrics[0] if metrics[0] > 0 else 0
        completion_rate = metrics[3] / metrics[1] if metrics[1] > 0 else 0
        
        # Update metrics table
        conn.execute("""
            INSERT OR REPLACE INTO referee_metrics
            (referee_id, total_invitations, total_accepted, total_declined,
             total_completed, acceptance_rate, completion_rate,
             avg_response_time_days, avg_review_time_days, avg_quality_score,
             on_time_rate, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            referee_id,
            metrics[0],  # total_invitations
            metrics[1],  # total_accepted
            metrics[2],  # total_declined
            metrics[3],  # total_completed
            acceptance_rate,
            completion_rate,
            metrics[4],  # avg_response_time
            metrics[5],  # avg_review_time
            metrics[6],  # avg_quality
            metrics[7]   # on_time_rate
        ))
    
    def export_analytics(self, output_path: str = "referee_analytics.xlsx"):
        """Export comprehensive analytics to Excel"""
        with sqlite3.connect(self.db_path) as conn:
            # Get all referee data with metrics
            referees_df = pd.read_sql_query("""
                SELECT r.*, m.*
                FROM referees r
                LEFT JOIN referee_metrics m ON r.id = m.referee_id
                ORDER BY m.total_invitations DESC
            """, conn)
            
            # Get review history
            reviews_df = pd.read_sql_query("""
                SELECT rh.*, r.name, r.email
                FROM review_history rh
                JOIN referees r ON rh.referee_id = r.id
                ORDER BY rh.invited_date DESC
            """, conn)
            
            # Write to Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                referees_df.to_excel(writer, sheet_name='Referees', index=False)
                reviews_df.to_excel(writer, sheet_name='Review History', index=False)
            
            logger.info(f"Analytics exported to {output_path}")

# Convenience functions
def get_db() -> RefereeDatabase:
    """Get or create database instance"""
    return RefereeDatabase()