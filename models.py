from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Feature:
    key: str
    summary: str
    status: str
    art: Optional[str]
    pi: Optional[str]
    business_benefit: Optional[str]
    created: datetime
    updated: datetime

@dataclass
class Story:
    key: str
    summary: str
    status: str
    story_points: int
    workstream: str
    sprint: Optional[str]
    feature_link: str
    assignee: str
    created: datetime
    updated: datetime

@dataclass
class PIMetrics:
    pi_label: str
    art: Optional[str]
    workstream: Optional[str]
    total_features: int
    completed_features: int
    total_stories: int
    completed_stories: int
    total_story_points: int
    completed_story_points: int
    feature_completion_rate: float
    story_completion_rate: float
    story_points_completion_rate: float

@dataclass
class ScrumMetrics:
    workstream: str
    sprint_name: Optional[str]
    velocity: int
    planned_points: int
    completed_points: int
    stories_planned: int
    stories_completed: int
    sprint_goal_achievement: float

@dataclass
class ARTMetrics:
    art_name: str
    pi: str
    total_workstreams: int
    features_committed: int
    features_delivered: int
    story_points_committed: int
    story_points_delivered: int
    predictability_measure: float