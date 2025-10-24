"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.models.quiz import (
    Question,
    QuestionDifficulty,
    Quiz,
    QuizMetadata,
    QuizRound,
    UserInput,
)


class TestQuestion:
    """Test Question model."""

    def test_create_valid_question(self, sample_question: Question):
        """Test creating a valid question."""
        assert sample_question.question_text == "What is the capital of France?"
        assert sample_question.correct_answer == "B"
        assert sample_question.options["B"] == "Paris"
        assert sample_question.difficulty == QuestionDifficulty.EASY

    def test_question_requires_all_options(self):
        """Test that question requires all four options."""
        with pytest.raises(ValidationError):
            Question(
                question_text="Test?",
                options={"A": "Answer A", "B": "Answer B"},  # Missing C and D
                correct_answer="A",
                topic="Test",
                difficulty=QuestionDifficulty.EASY,
            )

    def test_question_correct_answer_must_be_valid(self):
        """Test that correct_answer must be A, B, C, or D."""
        with pytest.raises(ValidationError):
            Question(
                question_text="Test?",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="E",  # Invalid
                topic="Test",
                difficulty=QuestionDifficulty.EASY,
            )

    def test_question_quality_score_optional(self, sample_question: Question):
        """Test that quality_score is optional."""
        assert sample_question.quality_score is None
        sample_question.quality_score = 0.85
        assert sample_question.quality_score == 0.85


class TestQuizRound:
    """Test QuizRound model."""

    def test_create_valid_round(self, sample_quiz_round: QuizRound):
        """Test creating a valid quiz round."""
        assert sample_quiz_round.round_number == 1
        assert sample_quiz_round.round_name == "Round 1: General Knowledge"
        assert sample_quiz_round.topic == "General Knowledge"
        assert len(sample_quiz_round.questions) == 3

    def test_round_question_count_property(self, sample_quiz_round: QuizRound):
        """Test the question_count property."""
        assert sample_quiz_round.question_count == 3


class TestQuiz:
    """Test Quiz model."""

    def test_create_valid_quiz(self, sample_quiz: Quiz):
        """Test creating a valid quiz."""
        assert sample_quiz.title == "Test Quiz"
        assert sample_quiz.description == "A comprehensive test quiz"
        assert len(sample_quiz.rounds) == 1

    def test_quiz_total_rounds_property(self, sample_quiz: Quiz):
        """Test the total_rounds property."""
        assert sample_quiz.total_rounds == 1

    def test_quiz_total_questions_property(self, sample_quiz: Quiz):
        """Test the total_questions property."""
        assert sample_quiz.total_questions == 3

    def test_quiz_metadata(self, sample_quiz: Quiz):
        """Test quiz metadata."""
        assert sample_quiz.metadata.model_used == "claude-3-7-sonnet-20250219-v1:0"
        assert sample_quiz.metadata.regeneration_count == 0
        assert sample_quiz.metadata.average_quality_score == 0.85


class TestUserInput:
    """Test UserInput model."""

    def test_create_valid_user_input(self, sample_user_input: UserInput):
        """Test creating valid user input."""
        assert sample_user_input.topics == ["History", "Science"]
        assert sample_user_input.questions_per_round == 5
        assert sample_user_input.difficulty == QuestionDifficulty.MEDIUM

    def test_user_input_requires_topics(self):
        """Test that at least one topic is required."""
        with pytest.raises(ValidationError):
            UserInput(
                topics=[],  # Empty topics
                questions_per_round=10,
                difficulty=QuestionDifficulty.EASY,
            )

    def test_user_input_validates_questions_per_round(self):
        """Test that questions_per_round is validated."""
        with pytest.raises(ValidationError):
            UserInput(
                topics=["Test"],
                questions_per_round=0,  # Must be at least 1
                difficulty=QuestionDifficulty.EASY,
            )

        with pytest.raises(ValidationError):
            UserInput(
                topics=["Test"],
                questions_per_round=51,  # Max is 50
                difficulty=QuestionDifficulty.EASY,
            )

    def test_user_input_optional_fields(self):
        """Test that title and description are optional."""
        user_input = UserInput(
            topics=["Test"],
            questions_per_round=10,
            difficulty=QuestionDifficulty.EASY,
        )
        assert user_input.quiz_title is None
        assert user_input.quiz_description is None


class TestQuestionDifficulty:
    """Test QuestionDifficulty enum."""

    def test_difficulty_values(self):
        """Test difficulty enum values."""
        assert QuestionDifficulty.EASY.value == "easy"
        assert QuestionDifficulty.MEDIUM.value == "medium"
        assert QuestionDifficulty.HARD.value == "hard"

    def test_difficulty_from_string(self):
        """Test creating difficulty from string."""
        assert QuestionDifficulty("easy") == QuestionDifficulty.EASY
        assert QuestionDifficulty("medium") == QuestionDifficulty.MEDIUM
        assert QuestionDifficulty("hard") == QuestionDifficulty.HARD