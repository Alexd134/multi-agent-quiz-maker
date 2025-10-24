"""Shared test fixtures and configuration for pytest."""

from datetime import datetime
from typing import Any

import pytest

from src.models.quiz import (
    Question,
    QuestionDifficulty,
    Quiz,
    QuizMetadata,
    QuizRound,
    UserInput,
)


@pytest.fixture
def sample_user_input() -> UserInput:
    """Create a sample UserInput for testing."""
    return UserInput(
        topics=["History", "Science"],
        questions_per_round=5,
        difficulty=QuestionDifficulty.MEDIUM,
        quiz_title="Test Quiz",
        quiz_description="A test quiz",
    )


@pytest.fixture
def sample_question() -> Question:
    """Create a sample Question for testing."""
    return Question(
        question_text="What is the capital of France?",
        options={
            "A": "London",
            "B": "Paris",
            "C": "Berlin",
            "D": "Madrid",
        },
        correct_answer="B",
        topic="Geography",
        difficulty=QuestionDifficulty.EASY,
        explanation="Paris is the capital and largest city of France.",
    )


@pytest.fixture
def sample_questions() -> list[Question]:
    """Create a list of sample questions for testing."""
    return [
        Question(
            question_text="What is 2 + 2?",
            options={"A": "3", "B": "4", "C": "5", "D": "6"},
            correct_answer="B",
            topic="Mathematics",
            difficulty=QuestionDifficulty.EASY,
            explanation="Basic addition: 2 + 2 = 4",
        ),
        Question(
            question_text="What is the speed of light?",
            options={
                "A": "299,792,458 m/s",
                "B": "300,000,000 m/s",
                "C": "150,000,000 m/s",
                "D": "500,000,000 m/s",
            },
            correct_answer="A",
            topic="Physics",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="The speed of light in vacuum is exactly 299,792,458 m/s.",
        ),
        Question(
            question_text="Who wrote '1984'?",
            options={
                "A": "Aldous Huxley",
                "B": "George Orwell",
                "C": "Ray Bradbury",
                "D": "Philip K. Dick",
            },
            correct_answer="B",
            topic="Literature",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="George Orwell wrote the dystopian novel '1984' in 1949.",
        ),
    ]


@pytest.fixture
def sample_quiz_round(sample_questions: list[Question]) -> QuizRound:
    """Create a sample QuizRound for testing."""
    return QuizRound(
        round_name="Round 1: General Knowledge",
        round_number=1,
        topic="General Knowledge",
        questions=sample_questions,
    )


@pytest.fixture
def sample_quiz(sample_quiz_round: QuizRound) -> Quiz:
    """Create a sample Quiz for testing."""
    metadata = QuizMetadata(
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        model_used="claude-3-7-sonnet-20250219-v1:0",
        regeneration_count=0,
        average_quality_score=0.85,
    )

    return Quiz(
        title="Test Quiz",
        description="A comprehensive test quiz",
        rounds=[sample_quiz_round],
        metadata=metadata,
    )


@pytest.fixture
def sample_quiz_plan() -> dict[str, Any]:
    """Create a sample quiz plan for testing."""
    return {
        "title": "Test Quiz",
        "description": "A test quiz",
        "rounds": [
            {
                "round_number": 1,
                "round_name": "Round 1: History",
                "topic": "History",
                "question_count": 5,
                "difficulty": "medium",
            },
            {
                "round_number": 2,
                "round_name": "Round 2: Science",
                "topic": "Science",
                "question_count": 5,
                "difficulty": "medium",
            },
        ],
    }


@pytest.fixture
def mock_quiz_state(
    sample_user_input: UserInput,
    sample_quiz_plan: dict[str, Any],
) -> dict[str, Any]:
    """Create a mock QuizState for testing."""
    # Create questions with matching topics from quiz plan
    questions = [
        Question(
            question_text="What happened in 1066?",
            options={"A": "Norman Conquest", "B": "Magna Carta", "C": "Black Death", "D": "War of the Roses"},
            correct_answer="A",
            topic="History",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="The Norman Conquest occurred in 1066.",
        ),
        Question(
            question_text="What is photosynthesis?",
            options={"A": "Plant growth", "B": "Energy from light", "C": "Cell division", "D": "Water absorption"},
            correct_answer="B",
            topic="Science",
            difficulty=QuestionDifficulty.MEDIUM,
            explanation="Photosynthesis converts light energy into chemical energy.",
        ),
    ]

    return {
        "user_input": sample_user_input,
        "quiz_plan": sample_quiz_plan,
        "raw_questions": questions,
        "reviewed_questions": questions,
        "validated_questions": questions,
        "feedback_loop_count": 0,
        "max_regeneration_attempts": 3,
        "quality_threshold": 0.7,
        "needs_regeneration": False,
        "review_feedback": None,
        "validation_issues": None,
    }