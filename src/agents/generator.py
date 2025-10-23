"""Question Generator Agent - Generates quiz questions using AI."""

import json
from typing import Any, Dict, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import QuizState
from src.models.quiz import Question, QuestionDifficulty


def generate_questions(state: QuizState) -> Dict[str, Any]:
    """
    Question Generator Agent: Generate quiz questions based on the quiz plan.

    This agent generates questions for each round in the quiz plan.
    It can regenerate questions if quality review fails.

    Args:
        state: Current quiz state containing quiz_plan

    Returns:
        Dictionary with updated state containing raw_questions
    """
    quiz_plan = state["quiz_plan"]
    feedback_loop_count = state.get("feedback_loop_count", 0)
    review_feedback = state.get("review_feedback", None)

    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.8,  # Higher temperature for more creative questions
    )

    all_questions: List[Question] = []

    # Generate questions for each round
    for round_data in quiz_plan["rounds"]:
        topic = round_data["topic"]
        question_count = round_data["question_count"]
        difficulty = round_data["difficulty"]
        round_number = round_data["round_number"]

        # If we're regenerating, include feedback
        regeneration_context = ""
        if feedback_loop_count > 0 and review_feedback:
            regeneration_context = f"""
IMPORTANT: This is regeneration attempt {feedback_loop_count}.
Previous questions had quality issues. Please improve based on this feedback:
{format_feedback_for_round(review_feedback, round_number)}

Focus on:
- More interesting and engaging questions
- Clear, unambiguous wording
- Plausible but clearly incorrect distractors
- Proper difficulty level
"""

        # Create the generation prompt
        system_prompt = f"""You are an expert quiz question writer. Create high-quality, engaging multiple-choice questions.

Requirements:
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE option should be correct
- Incorrect options (distractors) should be plausible but clearly wrong
- Questions should be clear and unambiguous
- Avoid trivial or overly obscure questions
- Match the requested difficulty level

Difficulty levels:
- easy: Common knowledge, straightforward questions
- medium: Requires general knowledge or logical thinking
- hard: Challenging, requires specific knowledge or deep thinking

Return ONLY a JSON array of questions in this exact format:
[
    {{
        "question_text": "What is the capital of France?",
        "options": {{
            "A": "London",
            "B": "Paris",
            "C": "Berlin",
            "D": "Madrid"
        }},
        "correct_answer": "B",
        "explanation": "Paris has been the capital of France since 987 AD."
    }}
]

IMPORTANT: Return ONLY the JSON array, no additional text or markdown.
"""

        user_prompt = f"""Generate {question_count} multiple-choice questions on the topic: {topic}

Difficulty level: {difficulty}
Round: {round_number}

{regeneration_context}

Generate exactly {question_count} high-quality questions following the JSON format specified.
Remember: Return ONLY the JSON array, no markdown code blocks or additional text."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Get questions from Claude
        response = llm.invoke(messages)
        content = response.content

        # Parse the response
        questions_data = parse_questions_response(content)

        # Convert to Question objects
        for q_data in questions_data:
            try:
                question = Question(
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    topic=topic,
                    difficulty=QuestionDifficulty(difficulty),
                    explanation=q_data.get("explanation"),
                )
                all_questions.append(question)
            except Exception as e:
                # Log error but continue with other questions
                error_msg = f"Failed to create question from data: {e}"
                state.get("errors", []).append(error_msg)
                continue

    # Increment feedback loop count if this is a regeneration
    new_feedback_count = feedback_loop_count
    if state.get("needs_regeneration", False):
        new_feedback_count = feedback_loop_count + 1

    return {
        "raw_questions": all_questions,
        "feedback_loop_count": new_feedback_count,
        "needs_regeneration": False,  # Reset the flag
    }


def parse_questions_response(content: str) -> List[Dict[str, Any]]:
    """
    Parse the AI response to extract questions.

    Handles various response formats including markdown code blocks.

    Args:
        content: Raw response from Claude

    Returns:
        List of question dictionaries
    """
    # Remove markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    # Remove any leading/trailing whitespace
    content = content.strip()

    try:
        questions_data = json.loads(content)

        # Ensure it's a list
        if isinstance(questions_data, dict):
            questions_data = [questions_data]

        return questions_data
    except json.JSONDecodeError as e:
        # Try to extract JSON from the content
        import re

        json_pattern = r"\[[\s\S]*\]"
        match = re.search(json_pattern, content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # If all parsing fails, return empty list
        print(f"Failed to parse questions: {e}")
        print(f"Content: {content[:200]}...")
        return []


def format_feedback_for_round(
    feedback: List[Dict[str, Any]], round_number: int
) -> str:
    """
    Format quality feedback for a specific round.

    Args:
        feedback: List of feedback items
        round_number: Round number to filter feedback for

    Returns:
        Formatted feedback string
    """
    if not feedback:
        return "No specific feedback available."

    relevant_feedback = [
        f
        for f in feedback
        if f.get("round_number") == round_number or "round_number" not in f
    ]

    if not relevant_feedback:
        return "General: Improve question quality, clarity, and difficulty appropriateness."

    feedback_text = []
    for item in relevant_feedback:
        if "issue" in item:
            feedback_text.append(f"- {item['issue']}")
        if "suggestion" in item:
            feedback_text.append(f"  Suggestion: {item['suggestion']}")

    return "\n".join(feedback_text) if feedback_text else "Improve overall quality."


def generate_single_question(
    topic: str, difficulty: str, llm: ChatAnthropic
) -> Question:
    """
    Generate a single question (useful for targeted regeneration).

    Args:
        topic: Question topic
        difficulty: Difficulty level
        llm: Language model instance

    Returns:
        Generated Question object
    """
    system_prompt = """You are an expert quiz question writer. Create ONE high-quality multiple-choice question.

Return ONLY a JSON object in this format:
{
    "question_text": "What is the capital of France?",
    "options": {
        "A": "London",
        "B": "Paris",
        "C": "Berlin",
        "D": "Madrid"
    },
    "correct_answer": "B",
    "explanation": "Paris has been the capital of France since 987 AD."
}"""

    user_prompt = f"""Generate ONE multiple-choice question on: {topic}
Difficulty: {difficulty}

Return ONLY the JSON object, no markdown or additional text."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    content = response.content

    # Parse response
    questions_data = parse_questions_response(content)

    if questions_data and len(questions_data) > 0:
        q_data = questions_data[0]
        return Question(
            question_text=q_data["question_text"],
            options=q_data["options"],
            correct_answer=q_data["correct_answer"],
            topic=topic,
            difficulty=QuestionDifficulty(difficulty),
            explanation=q_data.get("explanation"),
        )

    # Fallback question if generation fails
    return create_fallback_question(topic, difficulty)


def create_fallback_question(topic: str, difficulty: str) -> Question:
    """
    Create a fallback question if generation fails.

    Args:
        topic: Question topic
        difficulty: Difficulty level

    Returns:
        Basic Question object
    """
    return Question(
        question_text=f"Sample question about {topic}?",
        options={
            "A": "Option A",
            "B": "Option B",
            "C": "Option C",
            "D": "Option D",
        },
        correct_answer="A",
        topic=topic,
        difficulty=QuestionDifficulty(difficulty),
        explanation="This is a fallback question.",
    )