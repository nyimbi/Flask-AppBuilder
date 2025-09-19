"""
Core collaborative functionality for Flask-AppBuilder.

Provides team management, workspace management, and collaboration engine.
"""

from .team_manager import TeamManager
from .collaboration_engine import CollaborationEngine
from .workspace_manager import WorkspaceManager

__all__ = [
    "TeamManager",
    "CollaborationEngine",
    "WorkspaceManager"
]