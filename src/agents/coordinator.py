"""Format Coordinator Agent - Organizes questions into final quiz structure."""

from datetime import datetime
from typing import Any

from src.graph.state import QuizState
from src.models.quiz import Quiz, QuizMetadata, QuizRound


def format_quiz(state: QuizState) -> dict[str, Any]:
    """
    Format Coordinator Agent: Organize validated questions into final quiz structure.

    This agent takes all validated questions and organizes them into:
    - Properly structured rounds
    - Complete Quiz object with metadata
    - Ready for export

    Args:
        state: Current quiz state containing validated_questions and quiz_plan

    Returns:
        Dictionary with updated state containing final_quiz
    """
    validated_questions = state["validated_questions"]
    quiz_plan = state["quiz_plan"]
    user_input = state["user_input"]

    if not validated_questions:
        # Create empty quiz if no questions
        quiz = Quiz(
            title=quiz_plan.get("title", "Empty Quiz"),
            description=quiz_plan.get("description", ""),
            rounds=[],
            metadata=QuizMetadata(
                created_at=datetime.now(),
                regeneration_count=state.get("feedback_loop_count", 0),
            ),
        )
        return {"final_quiz": quiz}

    # Group questions by topic/round
    rounds_data = quiz_plan.get("rounds", [])
    quiz_rounds = []

    for round_info in rounds_data:
        round_number = round_info["round_number"]
        round_name = round_info["round_name"]
        topic = round_info["topic"]

        # Find questions for this round/topic
        round_questions = [q for q in validated_questions if q.topic == topic]

        if round_questions:
            quiz_round = QuizRound(
                round_name=round_name,
                round_number=round_number,
                topic=topic,
                questions=round_questions,
            )
            quiz_rounds.append(quiz_round)

    # Calculate metadata
    avg_quality_score = None
    if validated_questions:
        quality_scores = [
            q.quality_score for q in validated_questions if q.quality_score is not None
        ]
        if quality_scores:
            avg_quality_score = sum(quality_scores) / len(quality_scores)

    # Create quiz metadata
    metadata = QuizMetadata(
        created_at=datetime.now(),
        model_used="claude-3-5-sonnet-20241022",
        regeneration_count=state.get("feedback_loop_count", 0),
        average_quality_score=avg_quality_score,
    )

    # Create final quiz
    quiz = Quiz(
        title=quiz_plan.get("title", user_input.quiz_title or "Quiz"),
        description=quiz_plan.get(
            "description", user_input.quiz_description or "Generated quiz"
        ),
        rounds=quiz_rounds,
        metadata=metadata,
    )

    return {"final_quiz": quiz, "quiz_rounds": quiz_rounds}


def organize_questions_by_topic(state: QuizState) -> dict[str, Any]:
    """
    Helper function to organize questions by topic.

    Args:
        state: Current quiz state

    Returns:
        Dictionary mapping topics to questions
    """
    validated_questions = state["validated_questions"]

    topic_map: dict[str, list] = {}
    for question in validated_questions:
        topic = question.topic
        if topic not in topic_map:
            topic_map[topic] = []
        topic_map[topic].append(question)

    return topic_map


def create_round_from_questions(
    round_number: int, round_name: str, topic: str, questions: list
) -> QuizRound:
    """
    Create a QuizRound from a list of questions.

    Args:
        round_number: Round sequence number
        round_name: Display name for the round
        topic: Round topic
        questions: List of Question objects

    Returns:
        QuizRound object
    """
    return QuizRound(
        round_name=round_name,
        round_number=round_number,
        topic=topic,
        questions=questions,
    )
