"""Planner Agent - Creates quiz structure and distributes topics."""

from typing import Any, Dict

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import get_settings
from src.graph.state import QuizState
from src.models.quiz import QuestionDifficulty, QuizPlan


def create_quiz_plan(state: QuizState) -> Dict[str, Any]:
    """
    Planner Agent: Create a structured quiz plan from user input.

    This agent takes the user's requirements and creates a detailed plan
    for the quiz, including:
    - Quiz title and description
    - Round structure
    - Topic distribution
    - Question allocation per round

    Args:
        state: Current quiz state containing user_input

    Returns:
        Dictionary with updated state containing quiz_plan
    """
    user_input = state["user_input"]
    settings = get_settings()

    # Initialize Claude with structured output
    llm = ChatBedrock(
        model=settings.model_name,
        temperature=settings.default_temperature,
    )

    # Use structured output to automatically generate and validate the schema
    llm_with_structure = llm.with_structured_output(QuizPlan)

    # Create the planning prompt
    system_prompt = """You are a quiz planning expert. Your job is to create a well-structured quiz plan.

Given the user's requirements, create a detailed quiz plan with:
1. An engaging quiz title (if not provided)
2. A brief description
3. Rounds organized by topics

IMPORTANT RULES:
- Create EXACTLY ONE round for EACH topic provided by the user
- Do NOT break down topics into sub-topics
- Do NOT create additional rounds beyond the topics specified
- Each round should have exactly the number of questions requested
- Round names should be engaging and descriptive"""

    topic_count = len(user_input.topics)
    user_prompt = f"""Create a quiz plan with the following requirements:

Topics: {', '.join(user_input.topics)}
Number of topics: {topic_count}
Questions per round: {user_input.questions_per_round}
Difficulty: {user_input.difficulty.value}
{f"Custom title: {user_input.quiz_title}" if user_input.quiz_title else ""}
{f"Custom description: {user_input.quiz_description}" if user_input.quiz_description else ""}

IMPORTANT: Create EXACTLY {topic_count} round(s) - one for each topic listed above.
Do NOT create additional rounds or break topics into sub-topics."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        # Get the plan from Claude - returns QuizPlan object directly
        quiz_plan_obj = llm_with_structure.invoke(messages)

        # Convert to dict for state
        quiz_plan = {
            "title": quiz_plan_obj.title,
            "description": quiz_plan_obj.description,
            "rounds": quiz_plan_obj.rounds,
        }

        # Validate and ensure all required fields
        quiz_plan = validate_quiz_plan(quiz_plan, user_input)

    except Exception as e:
        # Fallback: create a basic plan
        quiz_plan = create_fallback_plan(user_input)

    return {"quiz_plan": quiz_plan}


def create_fallback_plan(user_input) -> Dict[str, Any]:
    """
    Create a basic fallback plan if AI generation fails.

    Args:
        user_input: User input object

    Returns:
        Basic quiz plan dictionary
    """
    return {
        "title": user_input.quiz_title or "General Knowledge Quiz",
        "description": user_input.quiz_description
        or "A challenging quiz covering various topics",
        "rounds": [
            {
                "round_number": i + 1,
                "round_name": f"Round {i + 1}: {topic}",
                "topic": topic,
                "question_count": user_input.questions_per_round,
                "difficulty": user_input.difficulty.value,
            }
            for i, topic in enumerate(user_input.topics)
        ],
    }


def validate_quiz_plan(plan: Dict[str, Any], user_input) -> Dict[str, Any]:
    """
    Validate and fix the quiz plan to ensure it has all required fields.

    Args:
        plan: Quiz plan dictionary
        user_input: User input object

    Returns:
        Validated quiz plan
    """
    # Ensure title
    if "title" not in plan or not plan["title"]:
        plan["title"] = user_input.quiz_title or "General Knowledge Quiz"

    # Ensure description
    if "description" not in plan or not plan["description"]:
        plan["description"] = (
            user_input.quiz_description or "A challenging quiz covering various topics"
        )

    # Ensure rounds exist
    if "rounds" not in plan or not plan["rounds"]:
        plan["rounds"] = [
            {
                "round_number": i + 1,
                "round_name": f"Round {i + 1}: {topic}",
                "topic": topic,
                "question_count": user_input.questions_per_round,
                "difficulty": user_input.difficulty.value,
            }
            for i, topic in enumerate(user_input.topics)
        ]
    else:
        # CRITICAL: Ensure we have exactly one round per topic
        expected_rounds = len(user_input.topics)
        actual_rounds = len(plan["rounds"])

        if actual_rounds != expected_rounds:
            print(f"Warning: LLM created {actual_rounds} rounds but expected {expected_rounds}. Using fallback.")
            # Use fallback plan to ensure correct number of rounds
            plan["rounds"] = [
                {
                    "round_number": i + 1,
                    "round_name": f"Round {i + 1}: {topic}",
                    "topic": topic,
                    "question_count": user_input.questions_per_round,
                    "difficulty": user_input.difficulty.value,
                }
                for i, topic in enumerate(user_input.topics)
            ]
        else:
            # Validate each round
            for i, round_data in enumerate(plan["rounds"]):
                if "round_number" not in round_data:
                    round_data["round_number"] = i + 1
                if "round_name" not in round_data:
                    topic = round_data.get("topic", f"Topic {i + 1}")
                    round_data["round_name"] = f"Round {i + 1}: {topic}"
                if "question_count" not in round_data:
                    round_data["question_count"] = user_input.questions_per_round
                if "difficulty" not in round_data:
                    round_data["difficulty"] = user_input.difficulty.value
                # Ensure difficulty is valid
                if round_data["difficulty"] not in [d.value for d in QuestionDifficulty]:
                    round_data["difficulty"] = user_input.difficulty.value

    return plan