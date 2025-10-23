"""Question Generator Agent - Generates quiz questions using AI."""

from typing import Any, Dict, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import get_settings
from src.graph.state import QuizState
from src.models.quiz import Question, QuestionDifficulty, QuestionList


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
    settings = get_settings()

    # Initialize Claude with structured output
    llm = ChatAnthropic(
        model=settings.model_name,
        temperature=settings.default_temperature,
    )

    # Use structured output to automatically generate and validate the schema
    llm_with_structure = llm.with_structured_output(QuestionList)

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

        # Create the generation prompt (simpler now - no JSON format specification needed)
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
                - hard: Challenging, requires specific knowledge or deep thinking"""

        user_prompt = f"""Generate {question_count} multiple-choice questions on the topic: {topic}

                Difficulty level: {difficulty}
                Round: {round_number}

                {regeneration_context}

                Generate exactly {question_count} high-quality questions."""

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
            # Batch generation failed, try one question at a time
            print(f"Batch generation failed for {topic}: {e}")
            print(f"Attempting to generate questions individually...")

            for i in range(question_count):
                try:
                    question = generate_single_question(topic, difficulty, llm)
                    all_questions.append(question)
                except Exception as single_error:
                    # Skip this question and log the failure
                    error_msg = f"Failed to generate question {i+1}/{question_count} for {topic}: {single_error}"
                    state.get("errors", []).append(error_msg)
                    print(f"Skipping question: {error_msg}")
                    # Don't add a fallback - just continue with fewer questions

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

    Raises:
        Exception: If question generation fails
    """
    
    llm_with_structure = llm.with_structured_output(Question)

    system_prompt = """You are an expert quiz question writer. Create ONE high-quality multiple-choice question.

Requirements:
- Exactly 4 options (A, B, C, D)
- Only ONE correct answer
- Clear, unambiguous wording
- Plausible but clearly incorrect distractors"""

    user_prompt = f"""Generate ONE multiple-choice question on: {topic}
Difficulty: {difficulty}

Create a high-quality question."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Returns Question object directly
    question = llm_with_structure.invoke(messages)
    # Set topic and difficulty
    question.topic = topic
    question.difficulty = QuestionDifficulty(difficulty)
    return question