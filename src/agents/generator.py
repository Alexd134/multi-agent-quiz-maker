"""Question Generator Agent - Generates quiz questions using AI."""

from typing import Any

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import get_settings
from src.graph.state import QuizState
from src.models.quiz import Question, QuestionDifficulty, QuestionList


def generate_questions(state: QuizState) -> dict[str, Any]:
    """
    Question Generator Agent: Generate quiz questions based on the quiz plan.

    This agent generates questions for each round in the quiz plan.
    On regeneration, it only regenerates questions that failed review.

    Args:
        state: Current quiz state containing quiz_plan

    Returns:
        Dictionary with updated state containing raw_questions
    """
    quiz_plan = state["quiz_plan"]
    feedback_loop_count = state.get("feedback_loop_count", 0)
    review_feedback = state.get("review_feedback", None)
    raw_questions = state.get("raw_questions", [])
    settings = get_settings()

    llm = ChatBedrock(
        model=settings.model_name,
        temperature=settings.default_temperature,
    )

    # Use structured output to automatically generate and validate the schema
    llm_with_structure = llm.with_structured_output(QuestionList)

    # Check if this is a regeneration
    is_regeneration = feedback_loop_count > 0 and review_feedback is not None

    if is_regeneration:
        # Extract IDs of questions that need regeneration
        failed_question_ids = {fb["question_id"] for fb in review_feedback}
        # Keep questions that passed review
        all_questions = [q for q in raw_questions if q.id not in failed_question_ids]

        # Group failed questions by topic to know how many to regenerate per round
        failed_by_topic: dict[str, int] = {}
        for fb in review_feedback:
            topic = fb["topic"]
            failed_by_topic[topic] = failed_by_topic.get(topic, 0) + 1
    else:
        # First generation - start fresh
        all_questions: list[Question] = []
        failed_by_topic = {}

    # Generate questions for each round
    for round_data in quiz_plan["rounds"]:
        topic = round_data["topic"]
        question_count = round_data["question_count"]
        difficulty = round_data["difficulty"]
        round_number = round_data["round_number"]

        # On regeneration, only generate the number of failed questions for this topic
        if is_regeneration:
            questions_to_generate = failed_by_topic.get(topic, 0)
            if questions_to_generate == 0:
                # No failed questions for this topic, skip
                continue
        else:
            # First generation, generate all questions
            questions_to_generate = question_count

        # If we're regenerating, include feedback
        regeneration_context = ""
        if is_regeneration:
            regeneration_context = f"""
IMPORTANT: This is regeneration attempt {feedback_loop_count}.
Previous questions on this topic had quality issues. Please improve based on this feedback:
{format_feedback_for_topic(review_feedback, topic)}

Focus on:
- More interesting and engaging questions
- Clear, unambiguous wording
- Plausible but clearly incorrect distractors
- Proper difficulty level
"""

        # Create the generation prompt
        system_prompt = """You are an expert quiz question writer. Create high-quality, engaging multiple-choice questions.

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
                - hard: Challenging, requires specific knowledge or deep thinking"""

        user_prompt = f"""Generate {questions_to_generate} multiple-choice questions on the topic: {topic}

                Difficulty level: {difficulty}
                Round: {round_number}

                {regeneration_context}

                Generate exactly {questions_to_generate} high-quality questions."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            # Get questions from LLM - returns QuestionList object directly
            question_list = llm_with_structure.invoke(messages)

            # Add topic and difficulty to each question
            for question in question_list.questions:
                question.topic = topic
                question.difficulty = QuestionDifficulty(difficulty)
                all_questions.append(question)

        except Exception as e:
            # Log error and skip this entire round
            error_msg = f"Failed to generate questions for round {round_number} ({topic}): {str(e)}"
            state.get("errors", []).append(error_msg)
            print(f"Skipping round: {error_msg}")
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


def format_feedback_for_topic(feedback: list[dict[str, Any]], topic: str) -> str:
    """
    Format quality feedback for a specific topic.

    Args:
        feedback: List of feedback items
        topic: Topic to filter feedback for

    Returns:
        Formatted feedback string
    """
    if not feedback:
        return "No specific feedback available."

    # Filter feedback for this topic
    relevant_feedback = [f for f in feedback if f.get("topic") == topic]

    if not relevant_feedback:
        return "General: Improve question quality, clarity, and difficulty appropriateness."

    feedback_text = []
    for item in relevant_feedback:
        if "issue" in item:
            feedback_text.append(f"- {item['issue']}")
        if "issues" in item and item["issues"]:
            for issue in item["issues"]:
                feedback_text.append(f"  • {issue}")

    return "\n".join(feedback_text) if feedback_text else "Improve overall quality."
