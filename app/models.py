"""
Pydantic data models shared across the whole application.

Keeping all schemas in one file makes it easy to see the full "shape"
of data flowing through the pipeline:

    Video -> ContentProfile -> (Persona + ContentProfile) -> PersonaReaction
          -> EngagementStats -> RoundResult -> SimulationReport
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

class ContentProfile(BaseModel):
    """A structured summary of the video, produced once and reused by
    every persona so we don't re-analyze the raw video 15+ times."""

    title: str = Field(description="Short topic/title for the content")
    summary: str = Field(description="1-3 sentence summary of what happens")
    duration_seconds: float = Field(ge=0)

    hook_strength: float = Field(ge=0, le=1, description="How strong the first 1-3s hook is")
    educational_value: float = Field(ge=0, le=1)
    entertainment_value: float = Field(ge=0, le=1)
    emotional_intensity: float = Field(ge=0, le=1)
    shareability: float = Field(ge=0, le=1)
    curiosity_surprise_strength: float = Field(
        ge=0,
        le=1,
        description="Strength of curiosity, mystery, anticipation, surprise, or reveal payoff",
    )

    call_to_action: Optional[str] = None
    target_audience: str = Field(description="Who this content is most likely to resonate with")


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

class Persona(BaseModel):
    """A simulated social-media user with a fixed personality profile."""

    id: str
    name: str
    age_range: str
    interests: list[str]
    personality: str

    # 0-1 scores describing behavioral tendencies for this archetype
    attention_span: float = Field(ge=0, le=1)
    entertainment_preference: float = Field(ge=0, le=1)
    educational_preference: float = Field(ge=0, le=1)
    sharing_tendency: float = Field(ge=0, le=1)
    commenting_tendency: float = Field(ge=0, le=1)
    following_tendency: float = Field(ge=0, le=1)


class PersonaReaction(BaseModel):
    """The structured decision one persona makes after 'watching' the content."""

    persona_id: str
    watch: bool
    completion_rate: float = Field(ge=0, le=1)
    rewatch: bool
    like: bool
    comment: bool
    share: bool
    follow: bool
    comment_text: Optional[str] = None
    reasoning: str

    @field_validator("completion_rate")
    @classmethod
    def clamp_completion(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @model_validator(mode="after")
    def enforce_watch_consistency(self) -> "PersonaReaction":
        """A persona that didn't watch can't have engaged with the content.

        If watch=False, force every downstream engagement field into its
        "didn't happen" state, regardless of what the LLM returned. If
        watch=True, all engagement fields remain exactly as the persona
        (independently) decided them.
        """
        if not self.watch:
            self.completion_rate = 0.0
            self.rewatch = False
            self.like = False
            self.comment = False
            self.share = False
            self.follow = False
            self.comment_text = None
        return self


# ---------------------------------------------------------------------------
# Aggregation / scoring
# ---------------------------------------------------------------------------

class EngagementStats(BaseModel):
    """Deterministic, purely-Python-computed engagement metrics for one round."""

    total_personas: int
    successful_personas: int
    failed_personas: int

    watch_rate: float
    skip_rate: float
    average_completion_rate: float
    rewatch_rate: float
    like_rate: float
    comment_rate: float
    share_rate: float
    follow_rate: float


class RoundResult(BaseModel):
    round_number: int
    cohort_size: int
    stats: EngagementStats
    distribution_score: float
    decision: str  # "PUSH" or "STOP"
    reactions: list[PersonaReaction]


class SimulationReport(BaseModel):
    video_path: str
    content_profile: ContentProfile
    rounds: list[RoundResult]
    virality_score: float = Field(ge=0, le=100)
    potential: str  # LOW / MEDIUM / HIGH / VERY HIGH
    main_drivers: list[str]
    weaknesses: list[str]
    ai_summary: str = ""
