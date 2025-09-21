"""
Session State Management System for Editorial Assistant

This module provides automatic progress tracking and session recovery
to handle potential session interruptions during development.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    """Task completion status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """Individual task tracking."""

    id: str
    name: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_minutes: float | None = None
    dependencies: list[str] = None
    outputs: list[str] = None  # Files created
    notes: str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.outputs is None:
            self.outputs = []


@dataclass
class SessionState:
    """Complete session state."""

    session_id: str
    started_at: datetime
    last_updated: datetime
    current_phase: str
    current_week: int
    current_day: int
    tasks: dict[str, Task]
    completed_files: list[str]
    key_learnings: list[str]
    next_actions: list[str]
    blockers: list[str]
    progress_percentage: float
    progress_log: list[dict[str, Any]] = None

    def __post_init__(self):
        if self.progress_log is None:
            self.progress_log = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "current_phase": self.current_phase,
            "current_week": self.current_week,
            "current_day": self.current_day,
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "completed_files": self.completed_files,
            "key_learnings": self.key_learnings,
            "next_actions": self.next_actions,
            "blockers": self.blockers,
            "progress_percentage": self.progress_percentage,
            "progress_log": self.progress_log or [],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        tasks = {}
        for k, v in data["tasks"].items():
            v["status"] = TaskStatus(v["status"])
            v["priority"] = TaskPriority(v["priority"])
            if v["started_at"]:
                v["started_at"] = datetime.fromisoformat(v["started_at"])
            if v["completed_at"]:
                v["completed_at"] = datetime.fromisoformat(v["completed_at"])
            tasks[k] = Task(**v)

        return cls(
            session_id=data["session_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            current_phase=data["current_phase"],
            current_week=data["current_week"],
            current_day=data["current_day"],
            tasks=tasks,
            completed_files=data["completed_files"],
            key_learnings=data["key_learnings"],
            next_actions=data["next_actions"],
            blockers=data["blockers"],
            progress_percentage=data["progress_percentage"],
            progress_log=data.get("progress_log", []),
        )


class SessionManager:
    """Manages session state and automatic progress saving."""

    def __init__(self, project_root: Path):
        """
        Initialize session manager.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.session_dir = self.project_root / ".session_state"
        self.session_dir.mkdir(exist_ok=True)

        # Current session file
        self.session_file = self.session_dir / "current_session.json"
        self.backup_dir = self.session_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Load or create session
        self.session = self._load_or_create_session()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = f"editorial_assistant_session_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _load_or_create_session(self) -> SessionState:
        """Load existing session or create new one."""
        if self.session_file.exists():
            try:
                with open(self.session_file) as f:
                    data = json.load(f)
                    session = SessionState.from_dict(data)

                    # Update last accessed
                    session.last_updated = datetime.now()

                    print(f"📂 Resumed session {session.session_id}")
                    print(f"   Phase: {session.current_phase}")
                    print(f"   Week {session.current_week}, Day {session.current_day}")
                    print(f"   Progress: {session.progress_percentage:.1f}%")

                    return session

            except Exception as e:
                print(f"⚠️  Error loading session: {e}")
                print("🔄 Creating new session...")

        # Create new session
        session = SessionState(
            session_id=self._generate_session_id(),
            started_at=datetime.now(),
            last_updated=datetime.now(),
            current_phase="Phase 1: Foundation",
            current_week=1,
            current_day=1,
            tasks={},
            completed_files=[],
            key_learnings=[],
            next_actions=[],
            blockers=[],
            progress_percentage=0.0,
            progress_log=[],
        )

        print(f"🚀 Started new session {session.session_id}")
        return session

    def save_session(self) -> None:
        """Save current session state."""
        try:
            # Create backup first
            if self.session_file.exists():
                backup_file = (
                    self.backup_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(self.session_file) as src, open(backup_file, "w") as dst:
                    dst.write(src.read())

            # Save current session
            self.session.last_updated = datetime.now()
            with open(self.session_file, "w") as f:
                json.dump(self.session.to_dict(), f, indent=2, default=str)

            print(f"💾 Session saved: {self.session.session_id}")

        except Exception as e:
            print(f"❌ Error saving session: {e}")

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: list[str] = None,
    ) -> None:
        """Add new task to session."""
        task = Task(
            id=task_id,
            name=name,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            dependencies=dependencies or [],
        )

        self.session.tasks[task_id] = task
        self.save_session()
        print(f"📝 Added task: {name}")

    def start_task(self, task_id: str) -> None:
        """Mark task as started."""
        if task_id in self.session.tasks:
            task = self.session.tasks[task_id]
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()

            self.save_session()
            print(f"▶️  Started task: {task.name}")
        else:
            print(f"❌ Task not found: {task_id}")

    def complete_task(self, task_id: str, outputs: list[str] = None, notes: str = "") -> None:
        """Mark task as completed."""
        if task_id in self.session.tasks:
            task = self.session.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.notes = notes

            if task.started_at:
                duration = (task.completed_at - task.started_at).total_seconds() / 60
                task.duration_minutes = duration

            if outputs:
                task.outputs = outputs
                self.session.completed_files.extend(outputs)

            # Update progress
            completed_tasks = sum(
                1 for t in self.session.tasks.values() if t.status == TaskStatus.COMPLETED
            )
            total_tasks = len(self.session.tasks)
            self.session.progress_percentage = (
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            )

            self.save_session()
            print(f"✅ Completed task: {task.name}")
            if task.duration_minutes:
                print(f"   Duration: {task.duration_minutes:.1f} minutes")

        else:
            print(f"❌ Task not found: {task_id}")

    def fail_task(self, task_id: str, reason: str) -> None:
        """Mark task as failed."""
        if task_id in self.session.tasks:
            task = self.session.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.notes = f"FAILED: {reason}"

            self.session.blockers.append(f"Task '{task.name}' failed: {reason}")
            self.save_session()
            print(f"❌ Failed task: {task.name} - {reason}")
        else:
            print(f"❌ Task not found: {task_id}")

    def add_learning(self, learning: str) -> None:
        """Add key learning from current work."""
        self.session.key_learnings.append(f"[{datetime.now().strftime('%H:%M')}] {learning}")
        self.save_session()
        print(f"🧠 Learning captured: {learning}")

    def add_next_action(self, action: str) -> None:
        """Add next action for session continuation."""
        self.session.next_actions.append(action)
        self.save_session()
        print(f"📋 Next action added: {action}")

    def update_phase(self, week: int, day: int, phase_name: str = None) -> None:
        """Update current phase/week/day."""
        self.session.current_week = week
        self.session.current_day = day
        if phase_name:
            self.session.current_phase = phase_name

        self.save_session()
        print(f"📅 Updated to Week {week}, Day {day}")

    def auto_save_progress(
        self, step_name: str, outputs: list[str] = None, learning: str = None
    ) -> None:
        """Automatically save progress after each significant step."""
        timestamp = datetime.now()

        # Create progress entry
        progress_entry = {
            "timestamp": timestamp.isoformat(),
            "step_name": step_name,
            "outputs": outputs or [],
            "learning": learning or "",
            "session_id": self.session.session_id,
        }

        # Add to progress log
        if not hasattr(self.session, "progress_log"):
            self.session.progress_log = []
        self.session.progress_log.append(progress_entry)

        # Save session state
        self.save_session()

        print(f"[SESSION] Auto-saved progress: {step_name}")

    def save_implementation_milestone(
        self, milestone_name: str, files_created: list[str], key_learnings: str
    ) -> None:
        """Save major implementation milestones."""
        self.auto_save_progress(
            step_name=f"MILESTONE: {milestone_name}", outputs=files_created, learning=key_learnings
        )

    def generate_status_report(self) -> str:
        """Generate comprehensive status report."""
        completed_tasks = [
            t for t in self.session.tasks.values() if t.status == TaskStatus.COMPLETED
        ]
        in_progress_tasks = [
            t for t in self.session.tasks.values() if t.status == TaskStatus.IN_PROGRESS
        ]
        pending_tasks = [t for t in self.session.tasks.values() if t.status == TaskStatus.PENDING]
        failed_tasks = [t for t in self.session.tasks.values() if t.status == TaskStatus.FAILED]

        report = f"""
# Session Status Report
**Session ID**: {self.session.session_id}
**Started**: {self.session.started_at.strftime('%Y-%m-%d %H:%M')}
**Last Updated**: {self.session.last_updated.strftime('%Y-%m-%d %H:%M')}
**Current Phase**: {self.session.current_phase}
**Week/Day**: Week {self.session.current_week}, Day {self.session.current_day}
**Progress**: {self.session.progress_percentage:.1f}%

## Task Summary
- ✅ **Completed**: {len(completed_tasks)} tasks
- ▶️ **In Progress**: {len(in_progress_tasks)} tasks
- 📋 **Pending**: {len(pending_tasks)} tasks
- ❌ **Failed**: {len(failed_tasks)} tasks

## Completed Files
{chr(10).join(f"- {file}" for file in self.session.completed_files)}

## Key Learnings
{chr(10).join(f"- {learning}" for learning in self.session.key_learnings[-5:])}

## Next Actions
{chr(10).join(f"- {action}" for action in self.session.next_actions)}

## Current Blockers
{chr(10).join(f"- {blocker}" for blocker in self.session.blockers)}
        """

        return report.strip()

    def auto_save_progress(
        self, step_name: str, outputs: list[str] = None, learning: str = None
    ) -> None:
        """Automatically save progress after each significant step."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if outputs:
            self.session.completed_files.extend(outputs)

        if learning:
            self.add_learning(learning)

        # Create auto-save summary
        summary_file = self.session_dir / f"step_{timestamp.replace(':', '')}_summary.md"
        with open(summary_file, "w") as f:
            f.write(f"# Step Completed: {step_name}\n")
            f.write(f"**Time**: {timestamp}\n")
            f.write(f"**Session**: {self.session.session_id}\n\n")

            if outputs:
                f.write("## Files Created/Modified\n")
                for output in outputs:
                    f.write(f"- {output}\n")
                f.write("\n")

            if learning:
                f.write(f"## Key Learning\n{learning}\n\n")

            f.write("## Current Status\n")
            f.write(self.generate_status_report())

        self.save_session()
        print(f"🔄 Auto-saved progress: {step_name}")


# Global session manager instance
_session_manager = None


def get_session_manager(project_root: Path = None) -> SessionManager:
    """Get or create global session manager."""
    global _session_manager

    if _session_manager is None:
        if project_root is None:
            project_root = Path.cwd()
        _session_manager = SessionManager(project_root)

    return _session_manager


def auto_save(step_name: str, outputs: list[str] = None, learning: str = None):
    """Decorator for automatic progress saving."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            sm = get_session_manager()

            try:
                result = func(*args, **kwargs)
                sm.auto_save_progress(step_name, outputs, learning)
                return result
            except Exception as e:
                sm.add_learning(f"Error in {step_name}: {str(e)}")
                sm.save_session()
                raise

        return wrapper

    return decorator


# Initialize session manager for this project
session_manager = get_session_manager(
    Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts")
)
