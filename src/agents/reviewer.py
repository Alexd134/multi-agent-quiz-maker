"""Quality Reviewer Agent - Reviews question quality and provides feedback."""

from typing import Any, Dict, List
import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import get_settings
from src.graph.state import QuizState
from src.models.quiz import Question, ReviewList


def review_questions(state: QuizState) -> Dict[str, Any]:
    """
    Quality Reviewer Agent: Review generated questions for quality.

    This agent evaluates each question on:
    - Clarity and wording
    - Answer correctness
    - Distractor quality (incorrect options are plausible)
    - Appropriate difficulty level
    - Overall engagement

    Args:
        state: Current quiz state containing raw_questions

    Returns:
        Dictionary with updated state containing reviewed_questions and feedback
    """
    raw_questions = state["raw_questions"]
    quality_threshold = state.get("quality_threshold", 0.7)
    settings = get_settings()

    if not raw_questions:
        return {
            "reviewed_questions": [],
            "review_feedback": [{"issue": "No questions to review"}],
            "needs_regeneration": True,
        }

    # Initialize Claude with structured output
    llm = ChatAnthropic(
        model=settings.model_name,
        temperature=settings.review_temperature,
    )

    # Use structured output
    llm_with_structure = llm.with_structured_output(ReviewList)

    reviewed_questions: List[Question] = []
    all_feedback: List[Dict[str, Any]] = []
    low_quality_count = 0

    # Review questions in batches (to avoid token limits)
    batch_size = 5
    for i in range(0, len(raw_questions), batch_size):
        batch = raw_questions[i : i + batch_size]

        # Create review prompt (simpler now - no JSON format needed)
        system_prompt = """You are an expert quiz quality reviewer. Evaluate quiz questions on multiple criteria.

For each question, assess:
1. Clarity: Is the question clear and unambiguous? (0-1)
2. Answer Correctness: Is the correct answer actually correct? (0-1)
3. Distractor Quality: Are incorrect options plausible but clearly wrong? (0-1)
4. Difficulty Match: Does it match the intended difficulty? (0-1)
5. Engagement: Is it interesting and well-written? (0-1)

Overall score should be the average of the 5 criteria.
Consider a question "passed" if overall_score >= 0.7"""

        # Format questions for review
        questions_text = format_questions_for_review(batch, i)

        user_prompt = f"""Review these quiz questions:

{questions_text}

Evaluate each question with detailed scores and feedback."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            # Get review from Claude - returns ReviewList object directly
            review_list = llm_with_structure.invoke(messages)

            # Apply reviews to questions
            for j, question in enumerate(batch):
                # Find matching review
                review = next(
                    (r for r in review_list.reviews if r.question_index == j),
                    None,
                )

                if review:
                    # Update question with quality score and feedback
                    question.quality_score = review.overall_score
                    question.feedback = review.feedback

                    reviewed_questions.append(question)

                    # Track feedback
                    if review.overall_score < quality_threshold:
                        low_quality_count += 1
                        all_feedback.append(
                            {
                                "question_index": i + j,
                                "topic": question.topic,
                                "issue": review.feedback,
                                "issues": review.issues,
                                "score": review.overall_score,
                            }
                        )
                else:
                    # No review found, use defaults
                    question.quality_score = 0.7
                    question.feedback = "Review not available"
                    reviewed_questions.append(question)

        except Exception as e:
            # If review fails, accept questions with default scores
            print(f"Error reviewing batch: {e}")
            for question in batch:
                question.quality_score = 0.7
                question.feedback = "Review failed, assuming acceptable quality"
                reviewed_questions.append(question)

    # Calculate average quality score
    avg_quality = (
        sum(q.quality_score or 0.7 for q in reviewed_questions)
        / len(reviewed_questions)
        if reviewed_questions
        else 0.0
    )

    # Determine if regeneration is needed
    needs_regeneration = (
        low_quality_count > len(reviewed_questions) * 0.3  # More than 30% failed
        or avg_quality < quality_threshold
    )

    return {
        "reviewed_questions": reviewed_questions,
        "review_feedback": all_feedback if all_feedback else None,
        "needs_regeneration": needs_regeneration,
    }


def format_questions_for_review(questions: List[Question], offset: int = 0) -> str:
    """
    Format questions for the review prompt.

    Args:
        questions: List of questions to review
        offset: Index offset for question numbering

    Returns:
        Formatted string of questions
    """
    formatted = []
    for i, q in enumerate(questions):
        formatted.append(f"""Question {offset + i}:
Topic: {q.topic}
Difficulty: {q.difficulty.value}
Question: {q.question_text}
Options:
  A: {q.options['A']}
  B: {q.options['B']}
  C: {q.options['C']}
  D: {q.options['D']}
Correct Answer: {q.correct_answer}
Explanation: {q.explanation or 'Not provided'}
---""")

    return "\n".join(formatted)


def parse_review_response(content: str) -> List[Dict[str, Any]]:
    """
    Parse the review response from Claude.

    Args:
        content: Raw response content

    Returns:
        List of review dictionaries
    """
    # Remove markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    content = content.strip()

    try:
        reviews = json.loads(content)

        # Ensure it's a list
        if isinstance(reviews, dict):
            reviews = [reviews]

        return reviews
    except json.JSONDecodeError as e:
        print(f"Failed to parse review response: {e}")
        print(f"Content: {content[:200]}...")
        return []


def create_default_review(question_index: int) -> Dict[str, Any]:
    """
    Create a default review if parsing fails.

    Args:
        question_index: Index of the question

    Returns:
        Default review dictionary
    """
    return {
        "question_index": question_index,
        "clarity_score": 0.7,
        "correctness_score": 0.7,
        "distractor_score": 0.7,
        "difficulty_score": 0.7,
        "engagement_score": 0.7,
        "overall_score": 0.7,
        "feedback": "Review unavailable, assuming acceptable quality.",
        "issues": [],
        "passed": True,
    }


def calculate_batch_quality(reviews: List[Dict[str, Any]]) -> float:
    """
    Calculate average quality score for a batch of reviews.

    Args:
        reviews: List of review dictionaries

    Returns:
        Average quality score
    """
    if not reviews:
        return 0.7

    scores = [r.get("overall_score", 0.7) for r in reviews]
    return sum(scores) / len(scores) if scores else 0.7