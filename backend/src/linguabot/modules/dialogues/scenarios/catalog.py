"""Trusted English role-play definitions shared by every LLM provider."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioDefinition:
    title: str
    bot_role: str
    learner_goal: str
    steps: tuple[str, ...]


SCENARIOS: dict[str, ScenarioDefinition] = {
    "introductions": ScenarioDefinition(
        title="Знакомство",
        bot_role="A new acquaintance at a language club.",
        learner_goal=(
            "Greet someone, introduce yourself, and ask about their name, "
            "country and occupation."
        ),
        steps=(
            "Greet the learner and exchange names.",
            "Ask where they are from, using their name if already known.",
            "Discuss what they do: work, studies or occupation.",
            "Ask why they are learning English and respond to their reason.",
            "Suggest practising together and exchange goodbyes.",
        ),
    ),
    "cafe": ScenarioDefinition(
        title="В кафе",
        bot_role="A barista at a cafe.",
        learner_goal=(
            "Politely order food and drinks, ask about ingredients, "
            "and request the bill."
        ),
        steps=(
            "Welcome the customer and take their drink order.",
            "Clarify the drink size and any ingredient questions.",
            "Offer something to eat and accept a polite refusal.",
            "State a role-play price and ask about cash or card.",
            "Serve the order, respond to a request for the bill and close.",
        ),
    ),
    "shop": ScenarioDefinition(
        title="В магазине",
        bot_role="A shop assistant in a clothing shop.",
        learner_goal=(
            "Ask about products, sizes and prices, try something on, "
            "make a purchase or return an item."
        ),
        steps=(
            "Offer help and find out which item the customer needs.",
            "Ask which size they need.",
            "Offer the item and show the fitting room; discuss colours.",
            "Ask how it fits and offer an alternative or a larger size.",
            "Answer price questions and help with payment or a return.",
        ),
    ),
    "travel": ScenarioDefinition(
        title="Поездка",
        bot_role=(
            "An airline check-in desk employee. Start in this role; only "
            "become a fellow passenger after check-in is finished and "
            "the conversation naturally moves to that encounter."
        ),
        learner_goal=(
            "Check in, discuss luggage and seats, ask about a connecting "
            "flight, and find the departure gate."
        ),
        steps=(
            "Welcome the passenger and ask for their booking details.",
            "Ask whether they are checking bags or have only hand luggage.",
            "Offer a window or aisle seat and respond to their preference.",
            "Give a role-play gate and boarding time; answer directions.",
            "Explain the way past security and discuss delays or connections.",
        ),
    ),
    "business_meeting": ScenarioDefinition(
        title="Деловая встреча",
        bot_role="A business partner or client in a project meeting.",
        learner_goal=(
            "Present a proposal, agree or disagree politely, "
            "and negotiate deadlines."
        ),
        steps=(
            "Welcome the learner and ask them to present their proposal.",
            "Ask about the project timeline and launch deadline.",
            "Raise a budget concern and discuss the proposed compromise.",
            "Suggest scheduling a follow-up meeting.",
            "Agree on next steps and an agenda, then close politely.",
        ),
    ),
    "doctor_visit": ScenarioDefinition(
        title="Визит к врачу",
        bot_role="A general practitioner in a simulated English lesson.",
        learner_goal=(
            "Describe symptoms, understand recommendations "
            "and ask clarifying questions."
        ),
        steps=(
            "Ask what the problem is and how long symptoms have lasted.",
            "Ask about a fever, cough or related symptoms.",
            "Ask about allergies to medication.",
            "Practise clarifying fictional care instructions in English; "
            "do not diagnose or prescribe real medication or doses.",
            "Discuss when a follow-up would be needed and close the visit.",
        ),
    ),
    "renting_a_flat": ScenarioDefinition(
        title="Аренда жилья",
        bot_role="A landlord or letting agent showing a flat.",
        learner_goal=(
            "Ask about rental conditions and bills, and negotiate the rent."
        ),
        steps=(
            "Confirm which flat the learner is interested in.",
            "Discuss the monthly rent and whether bills are included.",
            "Explain the deposit and answer questions about furniture.",
            "Discuss furnishings and the minimum contract length.",
            "Respond to a request to negotiate and agree on next steps.",
        ),
    ),
    "customer_support": ScenarioDefinition(
        title="Звонок в службу поддержки",
        bot_role="A customer support agent on a simulated phone call.",
        learner_goal=(
            "Describe a problem, follow instructions and request "
            "compensation or escalation when needed."
        ),
        steps=(
            "Greet the caller and ask what problem they need help with.",
            "Ask for a fictional order number to discuss the missing order.",
            "Explain a role-play delay and offer a refund or another option.",
            "Discuss compensation or escalation and how to send the outcome.",
            "Check whether they need anything else and close politely.",
        ),
    ),
    "job_interview": ScenarioDefinition(
        title="Собеседование",
        bot_role="An HR interviewer conducting a job interview.",
        learner_goal=(
            "Describe work experience, answer behavioural questions "
            "and ask the employer questions."
        ),
        steps=(
            "Invite the candidate to introduce themselves and describe "
            "their experience.",
            "Ask about a strength and a supporting example.",
            "Ask them to describe a difficult situation they handled.",
            "Discuss why they want to work for this employer.",
            "Invite their questions, such as onboarding or the role itself.",
        ),
    ),
    "weekend_small_talk": ScenarioDefinition(
        title="Планы на выходные",
        bot_role="A friendly acquaintance chatting about the weekend.",
        learner_goal=(
            "Keep a casual conversation going, make an invitation "
            "and accept or decline politely."
        ),
        steps=(
            "Ask about the learner's plans for the weekend.",
            "Discuss a museum exhibition and whether it is worth visiting.",
            "Suggest going together and respond to acceptance or refusal.",
            "Arrange a suitable time and meeting place if they accept.",
            "Continue with a related topic, such as coffee afterwards.",
        ),
    ),
}
