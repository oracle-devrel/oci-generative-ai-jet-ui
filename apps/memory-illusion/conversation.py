"""The scripted conversation — identical for BOTH demos.

12 turns of trip planning. Personal facts land early (vegetarian, window seat,
peanut allergy); the last two turns deliberately test whether the assistant
still "remembers" them. Same script in, so any token difference between the
two demos comes purely from HOW conversation state is carried."""

SCRIPT = [
    # -- facts get planted -------------------------------------------------
    "Hi! I'm planning a 5-day Tokyo trip in November. I'm vegetarian, and I "
    "always prefer window seats on flights. Budget is around $2,000.",
    "Which neighborhoods should I consider staying in?",
    "I love photography — where can I catch great sunrise shots in the city?",
    "Are there any day trips from Tokyo that are really worth it?",
    "One update: my partner Ankita is joining me. Ankita is allergic to "
    "peanuts, so please keep that in mind for restaurants.",
    # -- questions that silently depend on earlier facts -------------------
    "Given our food restrictions, which street-food areas can we actually enjoy?",
    "What's the best way to get from Narita airport into the city?",
    "What should we book in advance vs. figure out on the spot?",
    "How cold is Tokyo in November — what should we pack?",
    "Can you plan our day 1 in detail, morning to night?",
    # -- the memory tests ---------------------------------------------------
    "Quick check — remind me, what food restrictions do Ankita and I have?",
    "Perfect. And when you book my flight home, which seat should you pick for me?",
]
