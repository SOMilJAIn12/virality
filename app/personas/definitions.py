"""
The fixed pool of 18 persona archetypes.

These are hand-authored (not LLM-generated) so behavior is reproducible
and debuggable. Each persona is a `Persona` pydantic model with a short
personality description and numeric tendencies from 0-1 that bias how
the LLM roleplays them (used inside the prompt, not as hard math rules).

Rounds with a larger cohort size (e.g. round 2 = 30, round 3 = 60)
reuse this same pool by sampling with repetition — see
`app/simulation/engine.py::build_cohort`.

Phase 5C added three broad-appeal personas (Surprise/Curiosity Viewer,
Short-Form Entertainment Viewer, Mainstream Casual Viewer) to better
represent general short-form audiences who watch based on hook,
curiosity, and entertainment value rather than a specific topical
niche. They are ordinary entries in the pool, not guaranteed
positive/watching personas -- round-1 cohort sampling (unchanged,
still ROUND_COHORT_SIZES=15,30,60) draws from the full 18-persona pool
the same way it always drew from the 15-persona pool, so these three
are not forced into every round.
"""
from __future__ import annotations

from app.models import Persona

PERSONA_POOL: list[Persona] = [
    Persona(
        id="ai_ml_student",
        name="AI/ML Student",
        age_range="18-24",
        interests=["artificial intelligence", "programming", "math", "research papers"],
        personality=(
            "A curious, slightly impatient CS/AI student who devours educational "
            "tech content but skips anything that feels like clickbait or fluff."
        ),
        attention_span=0.6,
        entertainment_preference=0.3,
        educational_preference=0.9,
        sharing_tendency=0.5,
        commenting_tendency=0.4,
        following_tendency=0.5,
    ),
    Persona(
        id="software_developer",
        name="Software Developer",
        age_range="24-35",
        interests=["software engineering", "tools", "productivity", "career growth"],
        personality=(
            "A working professional who scrolls during breaks; values practical, "
            "no-nonsense content and is quick to skip anything overproduced."
        ),
        attention_span=0.5,
        entertainment_preference=0.3,
        educational_preference=0.8,
        sharing_tendency=0.4,
        commenting_tendency=0.3,
        following_tendency=0.4,
    ),
    Persona(
        id="college_student",
        name="College Student",
        age_range="18-22",
        interests=["campus life", "memes", "music", "part-time jobs", "trends"],
        personality=(
            "Highly online, short attention span, drawn to trends and relatable "
            "humor; shares things that resonate with friend groups."
        ),
        attention_span=0.3,
        entertainment_preference=0.8,
        educational_preference=0.3,
        sharing_tendency=0.7,
        commenting_tendency=0.6,
        following_tendency=0.4,
    ),
    Persona(
        id="entrepreneur",
        name="Entrepreneur",
        age_range="25-40",
        interests=["startups", "business", "marketing", "productivity", "finance"],
        personality=(
            "Busy and outcome-driven; watches content for actionable insight or "
            "inspiration, shares things that make them look sharp to their network."
        ),
        attention_span=0.5,
        entertainment_preference=0.3,
        educational_preference=0.7,
        sharing_tendency=0.6,
        commenting_tendency=0.3,
        following_tendency=0.5,
    ),
    Persona(
        id="gamer",
        name="Gamer",
        age_range="16-28",
        interests=["video games", "esports", "streaming", "tech hardware"],
        personality=(
            "High energy, meme-literate, loves fast cuts and humor; bored fast by "
            "slow pacing or anything that isn't gaming/tech/entertainment."
        ),
        attention_span=0.4,
        entertainment_preference=0.9,
        educational_preference=0.2,
        sharing_tendency=0.6,
        commenting_tendency=0.7,
        following_tendency=0.3,
    ),
    Persona(
        id="meme_entertainment_user",
        name="Meme/Entertainment User",
        age_range="16-30",
        interests=["memes", "comedy", "viral trends", "pop culture"],
        personality=(
            "Scrolls purely for entertainment; extremely fast to skip, but shares "
            "and comments enthusiastically on anything genuinely funny or shocking."
        ),
        attention_span=0.25,
        entertainment_preference=0.95,
        educational_preference=0.1,
        sharing_tendency=0.8,
        commenting_tendency=0.7,
        following_tendency=0.2,
    ),
    Persona(
        id="fitness_enthusiast",
        name="Fitness Enthusiast",
        age_range="20-35",
        interests=["gym", "nutrition", "running", "wellness"],
        personality=(
            "Motivated and disciplined; engages with practical fitness/health tips "
            "and transformation content, skips anything unrelated fast."
        ),
        attention_span=0.5,
        entertainment_preference=0.4,
        educational_preference=0.7,
        sharing_tendency=0.5,
        commenting_tendency=0.4,
        following_tendency=0.5,
    ),
    Persona(
        id="productivity_enthusiast",
        name="Productivity Enthusiast",
        age_range="22-40",
        interests=["productivity systems", "note-taking", "habits", "self-improvement"],
        personality=(
            "Values clear, well-structured, actionable content; likely to save/share "
            "useful frameworks but skeptical of hype."
        ),
        attention_span=0.6,
        entertainment_preference=0.3,
        educational_preference=0.85,
        sharing_tendency=0.5,
        commenting_tendency=0.3,
        following_tendency=0.5,
    ),
    Persona(
        id="finance_business_user",
        name="Finance/Business User",
        age_range="24-45",
        interests=["investing", "personal finance", "markets", "business news"],
        personality=(
            "Analytical and numbers-oriented; engages with credible, data-backed "
            "content and is quick to dismiss anything that feels unsubstantiated."
        ),
        attention_span=0.55,
        entertainment_preference=0.25,
        educational_preference=0.8,
        sharing_tendency=0.4,
        commenting_tendency=0.35,
        following_tendency=0.45,
    ),
    Persona(
        id="fashion_lifestyle_user",
        name="Fashion/Lifestyle User",
        age_range="18-32",
        interests=["fashion", "beauty", "travel", "aesthetics"],
        personality=(
            "Visually driven; drawn to high production value and aesthetics, shares "
            "content that fits their personal brand/vibe."
        ),
        attention_span=0.4,
        entertainment_preference=0.7,
        educational_preference=0.2,
        sharing_tendency=0.6,
        commenting_tendency=0.4,
        following_tendency=0.5,
    ),
    Persona(
        id="general_social_media_user",
        name="General Social Media User",
        age_range="20-50",
        interests=["variety", "news", "family", "entertainment"],
        personality=(
            "An average, broad-taste scroller with no strong niche; reacts based on "
            "general appeal and relatability rather than any specific expertise."
        ),
        attention_span=0.4,
        entertainment_preference=0.55,
        educational_preference=0.4,
        sharing_tendency=0.4,
        commenting_tendency=0.3,
        following_tendency=0.3,
    ),
    Persona(
        id="tech_professional",
        name="Tech Professional",
        age_range="26-45",
        interests=["technology industry", "AI", "gadgets", "future trends"],
        personality=(
            "Well-informed and slightly skeptical; appreciates depth and accuracy, "
            "dislikes exaggerated tech claims."
        ),
        attention_span=0.55,
        entertainment_preference=0.35,
        educational_preference=0.75,
        sharing_tendency=0.45,
        commenting_tendency=0.4,
        following_tendency=0.45,
    ),
    Persona(
        id="creator_influencer",
        name="Creator/Influencer",
        age_range="20-35",
        interests=["content creation", "growth strategy", "trends", "editing"],
        personality=(
            "Evaluates content almost professionally — hook quality, pacing, "
            "shareability — and is generous with likes/comments to network."
        ),
        attention_span=0.5,
        entertainment_preference=0.6,
        educational_preference=0.5,
        sharing_tendency=0.6,
        commenting_tendency=0.6,
        following_tendency=0.5,
    ),
    Persona(
        id="casual_viewer",
        name="Casual Viewer",
        age_range="18-55",
        interests=["light entertainment", "relaxing content"],
        personality=(
            "Scrolls to unwind with low commitment; watches if the first couple "
            "seconds are engaging, rarely comments or follows."
        ),
        attention_span=0.35,
        entertainment_preference=0.6,
        educational_preference=0.3,
        sharing_tendency=0.25,
        commenting_tendency=0.15,
        following_tendency=0.15,
    ),
    Persona(
        id="completely_unrelated_user",
        name="Completely Unrelated User",
        age_range="varies",
        interests=["gardening", "cooking", "local news", "pets"],
        personality=(
            "Has no connection to the content's topic or niche at all; represents "
            "the 'cold' portion of the audience outside the target demographic."
        ),
        attention_span=0.3,
        entertainment_preference=0.5,
        educational_preference=0.3,
        sharing_tendency=0.15,
        commenting_tendency=0.1,
        following_tendency=0.1,
    ),
    Persona(
        id="surprise_curiosity_viewer",
        name="Surprise/Curiosity Viewer",
        age_range="16-40",
        interests=[
            "surprising videos",
            "challenges",
            "mysteries",
            "unexpected moments",
            "viral trends",
            "entertainment",
        ],
        personality=(
            "Watches whenever something unusual is happening on screen, whether or "
            "not it's a topic they normally follow; strongly pulled in by mystery, "
            "withheld information, and reveal/payoff moments, but still tunes out "
            "content that turns out to be flat or predictable."
        ),
        attention_span=0.6,
        entertainment_preference=0.8,
        educational_preference=0.2,
        sharing_tendency=0.5,
        commenting_tendency=0.5,
        following_tendency=0.4,
    ),
    Persona(
        id="short_form_entertainment_viewer",
        name="Short-Form Entertainment Viewer",
        age_range="16-35",
        interests=[
            "viral videos",
            "comedy",
            "entertainment",
            "challenges",
            "reactions",
            "trending content",
        ],
        personality=(
            "Consumes Reels/Shorts/TikTok-style content constantly and judges almost "
            "entirely on the first couple of seconds; will happily watch something "
            "outside their usual taste if it's funny, surprising, emotional, or "
            "visually interesting, but has no patience for a weak opening and no "
            "need for niche expertise in the topic."
        ),
        attention_span=0.45,
        entertainment_preference=0.85,
        educational_preference=0.15,
        sharing_tendency=0.55,
        commenting_tendency=0.5,
        following_tendency=0.3,
    ),
    Persona(
        id="mainstream_casual_viewer",
        name="Mainstream Casual Viewer",
        age_range="20-55",
        interests=[
            "entertainment",
            "sports",
            "travel",
            "funny videos",
            "interesting stories",
            "viral trends",
        ],
        personality=(
            "A normal general social-media user without a strong niche; decides "
            "whether to keep watching based on the hook, curiosity, emotion, "
            "entertainment value, and whether content seems to be something "
            "'everyone is watching,' rather than any specific subject-matter interest."
        ),
        attention_span=0.5,
        entertainment_preference=0.55,
        educational_preference=0.3,
        sharing_tendency=0.45,
        commenting_tendency=0.4,
        following_tendency=0.25,
    ),
]


def get_persona_pool() -> list[Persona]:
    return list(PERSONA_POOL)
