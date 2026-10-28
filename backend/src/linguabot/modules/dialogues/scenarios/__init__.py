"""Server-owned topics; stored scenario text is never an instruction."""

_TOPICS = {
    "introductions": "Help the learner introduce themselves, greet a new acquaintance and ask simple follow-up questions.",
    "cafe": "Role-play a cafe server. Practice ordering food and drinks, polite requests and paying the bill.",
    "shop": "Role-play a shop assistant. Practice asking about products, sizes, prices and making a purchase.",
}
_FREE_CHAT = "Have a friendly everyday English conversation about a safe topic chosen by the learner."


def scenario_instructions(scenario: str) -> str:
    return _TOPICS.get(scenario.strip().lower(), _FREE_CHAT)
