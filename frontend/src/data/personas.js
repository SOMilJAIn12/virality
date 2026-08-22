// Mirrors app/personas/definitions.py (the real, authoritative persona
// pool used by the Python simulation engine). This is presentation-layer
// metadata only — the actual reactions/decisions always come from the
// backend; this file just lets the UI show a human-readable name,
// interests, and personality blurb for whichever persona_id a reaction
// references.

export const PERSONA_POOL = {
  ai_ml_student: {
    name: "AI/ML Student",
    ageRange: "18-24",
    interests: ["artificial intelligence", "programming", "math", "research papers"],
    personality:
      "A curious, slightly impatient CS/AI student who devours educational tech content but skips anything that feels like clickbait or fluff.",
    sharingTendency: 0.5,
    commentingTendency: 0.4,
  },
  software_developer: {
    name: "Software Developer",
    ageRange: "24-35",
    interests: ["software engineering", "tools", "productivity", "career growth"],
    personality:
      "A working professional who scrolls during breaks; values practical, no-nonsense content and is quick to skip anything overproduced.",
    sharingTendency: 0.4,
    commentingTendency: 0.3,
  },
  college_student: {
    name: "College Student",
    ageRange: "18-22",
    interests: ["campus life", "memes", "music", "part-time jobs", "trends"],
    personality:
      "Highly online, short attention span, drawn to trends and relatable humor; shares things that resonate with friend groups.",
    sharingTendency: 0.7,
    commentingTendency: 0.6,
  },
  entrepreneur: {
    name: "Entrepreneur",
    ageRange: "25-40",
    interests: ["startups", "business", "marketing", "productivity", "finance"],
    personality:
      "Busy and outcome-driven; watches content for actionable insight or inspiration, shares things that make them look sharp to their network.",
    sharingTendency: 0.6,
    commentingTendency: 0.3,
  },
  gamer: {
    name: "Gamer",
    ageRange: "16-28",
    interests: ["video games", "esports", "streaming", "tech hardware"],
    personality:
      "High energy, meme-literate, loves fast cuts and humor; bored fast by slow pacing or anything that isn't gaming/tech/entertainment.",
    sharingTendency: 0.6,
    commentingTendency: 0.7,
  },
  meme_entertainment_user: {
    name: "Meme/Entertainment User",
    ageRange: "16-30",
    interests: ["memes", "comedy", "viral trends", "pop culture"],
    personality:
      "Scrolls purely for entertainment; extremely fast to skip, but shares and comments enthusiastically on anything genuinely funny or shocking.",
    sharingTendency: 0.8,
    commentingTendency: 0.7,
  },
  fitness_enthusiast: {
    name: "Fitness Enthusiast",
    ageRange: "20-35",
    interests: ["gym", "nutrition", "running", "wellness"],
    personality:
      "Motivated and disciplined; engages with practical fitness/health tips and transformation content, skips anything unrelated fast.",
    sharingTendency: 0.5,
    commentingTendency: 0.4,
  },
  productivity_enthusiast: {
    name: "Productivity Enthusiast",
    ageRange: "22-40",
    interests: ["productivity systems", "note-taking", "habits", "self-improvement"],
    personality:
      "Values clear, well-structured, actionable content; likely to save/share useful frameworks but skeptical of hype.",
    sharingTendency: 0.5,
    commentingTendency: 0.3,
  },
  finance_business_user: {
    name: "Finance/Business User",
    ageRange: "24-45",
    interests: ["investing", "personal finance", "markets", "business news"],
    personality:
      "Analytical and numbers-oriented; engages with credible, data-backed content and is quick to dismiss anything that feels unsubstantiated.",
    sharingTendency: 0.4,
    commentingTendency: 0.35,
  },
  fashion_lifestyle_user: {
    name: "Fashion/Lifestyle User",
    ageRange: "18-32",
    interests: ["fashion", "beauty", "travel", "aesthetics"],
    personality:
      "Visually driven; drawn to high production value and aesthetics, shares content that fits their personal brand/vibe.",
    sharingTendency: 0.6,
    commentingTendency: 0.4,
  },
  general_social_media_user: {
    name: "General Social Media User",
    ageRange: "20-50",
    interests: ["variety", "news", "family", "entertainment"],
    personality:
      "An average, broad-taste scroller with no strong niche; reacts based on general appeal and relatability rather than any specific expertise.",
    sharingTendency: 0.4,
    commentingTendency: 0.3,
  },
  tech_professional: {
    name: "Tech Professional",
    ageRange: "26-45",
    interests: ["technology industry", "AI", "gadgets", "future trends"],
    personality:
      "Well-informed and slightly skeptical; appreciates depth and accuracy, dislikes exaggerated tech claims.",
    sharingTendency: 0.45,
    commentingTendency: 0.4,
  },
  creator_influencer: {
    name: "Creator/Influencer",
    ageRange: "20-35",
    interests: ["content creation", "growth strategy", "trends", "editing"],
    personality:
      "Evaluates content almost professionally — hook quality, pacing, shareability — and is generous with likes/comments to network.",
    sharingTendency: 0.6,
    commentingTendency: 0.6,
  },
  casual_viewer: {
    name: "Casual Viewer",
    ageRange: "18-55",
    interests: ["light entertainment", "relaxing content"],
    personality:
      "Scrolls to unwind with low commitment; watches if the first couple seconds are engaging, rarely comments or follows.",
    sharingTendency: 0.25,
    commentingTendency: 0.15,
  },
  completely_unrelated_user: {
    name: "Completely Unrelated User",
    ageRange: "varies",
    interests: ["gardening", "cooking", "local news", "pets"],
    personality:
      "Has no connection to the content's topic or niche at all; represents the 'cold' portion of the audience outside the target demographic.",
    sharingTendency: 0.15,
    commentingTendency: 0.1,
  },
  surprise_curiosity_viewer: {
    name: "Surprise/Curiosity Viewer",
    ageRange: "16-40",
    interests: ["surprising videos", "challenges", "mysteries", "unexpected moments", "viral trends"],
    personality:
      "Watches whenever something unusual is happening on screen, whether or not it's a topic they normally follow; pulled in by mystery and reveal moments, but tunes out anything flat or predictable.",
    sharingTendency: 0.5,
    commentingTendency: 0.5,
  },
  short_form_entertainment_viewer: {
    name: "Short-Form Entertainment Viewer",
    ageRange: "16-35",
    interests: ["viral videos", "comedy", "entertainment", "challenges", "reactions", "trending content"],
    personality:
      "Consumes Reels/Shorts/TikTok-style content constantly and judges almost entirely on the first couple of seconds; no patience for a weak opening.",
    sharingTendency: 0.55,
    commentingTendency: 0.5,
  },
  mainstream_casual_viewer: {
    name: "Mainstream Casual Viewer",
    ageRange: "20-55",
    interests: ["entertainment", "sports", "travel", "funny videos", "interesting stories", "viral trends"],
    personality:
      "A normal general social-media user without a strong niche; decides whether to keep watching based on the hook, curiosity, emotion, and entertainment value.",
    sharingTendency: 0.45,
    commentingTendency: 0.4,
  },
};

export function getPersonaMeta(personaId) {
  return (
    PERSONA_POOL[personaId] || {
      name: (personaId || "unknown").replace(/_/g, " "),
      ageRange: "—",
      interests: [],
      personality: "",
      sharingTendency: 0.3,
      commentingTendency: 0.3,
    }
  );
}
