"""Planner Agent - Creates quiz structure and distributes topics."""

from typing import Any, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import QuizState
from src.models.quiz import QuestionDifficulty


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

    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
    )

    # Create the planning prompt
    system_prompt = """You are a quiz planning expert. Your job is to create a well-structured quiz plan.

Given the user's requirements, create a detailed quiz plan with:
1. An engaging quiz title (if not provided)
2. A brief description
3. Rounds organized by topics
4. Balanced distribution of questions

Guidelines:
- Each round should focus on one topic
- Round names should be engaging and descriptive
- Ensure variety and good flow between rounds
- Consider the difficulty level requested

Return your plan as a structured JSON object with this format:
{
    "title": "Quiz Title",
    "description": "Brief description",
    "rounds": [
        {
            "round_number": 1,
            "round_name": "Descriptive Round Name",
            "topic": "Topic Name",
            "question_count": 10,
            "difficulty": "medium"
        }
    ]
}"""

    user_prompt = f"""Create a quiz plan with the following requirements:

Topics: {', '.join(user_input.topics)}
Questions per round: {user_input.questions_per_round}
Difficulty: {user_input.difficulty.value}
{f"Custom title: {user_input.quiz_title}" if user_input.quiz_title else ""}
{f"Custom description: {user_input.quiz_description}" if user_input.quiz_description else ""}

Create an engaging quiz plan following the JSON format specified."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Get the plan from Claude
    response = llm.invoke(messages)

    # Parse the response
    import json

    content = response.content

    # Extract JSON from the response (handle markdown code blocks)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        quiz_plan = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: create a basic plan
        quiz_plan = create_fallback_plan(user_input)

    # Validate and ensure all required fields
    quiz_plan = validate_quiz_plan(quiz_plan, user_input)

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
        # Validate each round
        for i, round_data in enumerate(plan["rounds"]):
            if "round_number" not in round_data:
                round_data["round_number"] = i + 1
            if "question_count" not in round_data:
                round_data["question_count"] = user_input.questions_per_round
            if "difficulty" not in round_data:
                round_data["difficulty"] = user_input.difficulty.value
            # Ensure difficulty is valid
            if round_data["difficulty"] not in [d.value for d in QuestionDifficulty]:
                round_data["difficulty"] = user_input.difficulty.value

    return plan