"""Tests for the Planner Agent."""

import pytest

from src.agents.planner import create_fallback_plan, validate_quiz_plan
from src.models.quiz import QuestionDifficulty, UserInput


class TestCreateFallbackPlan:
    """Test the fallback plan creation."""

    def test_creates_plan_with_correct_structure(self, sample_user_input: UserInput):
        """Test that fallback plan has correct structure."""
        plan = create_fallback_plan(sample_user_input)

        assert "title" in plan
        assert "description" in plan
        assert "rounds" in plan

    def test_creates_one_round_per_topic(self, sample_user_input: UserInput):
        """Test that one round is created for each topic."""
        plan = create_fallback_plan(sample_user_input)

        assert len(plan["rounds"]) == len(sample_user_input.topics)

    def test_round_structure_is_correct(self, sample_user_input: UserInput):
        """Test that each round has correct structure."""
        plan = create_fallback_plan(sample_user_input)

        for i, round_data in enumerate(plan["rounds"]):
            assert round_data["round_number"] == i + 1
            assert "round_name" in round_data
            assert round_data["topic"] == sample_user_input.topics[i]
            assert round_data["question_count"] == sample_user_input.questions_per_round
            assert round_data["difficulty"] == sample_user_input.difficulty.value

    def test_uses_custom_title_if_provided(self):
        """Test that custom title is used."""
        user_input = UserInput(
            topics=["Test"],
            questions_per_round=10,
            difficulty=QuestionDifficulty.EASY,
            quiz_title="Custom Title",
        )
        plan = create_fallback_plan(user_input)

        assert plan["title"] == "Custom Title"

    def test_uses_default_title_if_not_provided(self):
        """Test that default title is used."""
        user_input = UserInput(
            topics=["Test"],
            questions_per_round=10,
            difficulty=QuestionDifficulty.EASY,
        )
        plan = create_fallback_plan(user_input)

        assert plan["title"] == "General Knowledge Quiz"


class TestValidateQuizPlan:
    """Test quiz plan validation."""

    def test_adds_title_if_missing(self, sample_user_input: UserInput):
        """Test that title is added if missing."""
        plan = {"description": "Test", "rounds": []}
        validated = validate_quiz_plan(plan, sample_user_input)

        assert "title" in validated
        assert validated["title"] is not None

    def test_adds_description_if_missing(self, sample_user_input: UserInput):
        """Test that description is added if missing."""
        plan = {"title": "Test", "rounds": []}
        validated = validate_quiz_plan(plan, sample_user_input)

        assert "description" in validated
        assert validated["description"] is not None

    def test_creates_rounds_if_missing(self, sample_user_input: UserInput):
        """Test that rounds are created if missing."""
        plan = {"title": "Test", "description": "Test"}
        validated = validate_quiz_plan(plan, sample_user_input)

        assert "rounds" in validated
        assert len(validated["rounds"]) == len(sample_user_input.topics)

    def test_validates_round_count_matches_topics(self, sample_user_input: UserInput):
        """Test that round count is corrected to match topic count."""
        # Plan with wrong number of rounds
        plan = {
            "title": "Test",
            "description": "Test",
            "rounds": [
                {
                    "round_number": 1,
                    "round_name": "Round 1",
                    "topic": "Wrong Topic",
                    "question_count": 10,
                    "difficulty": "easy",
                }
            ],
        }

        validated = validate_quiz_plan(plan, sample_user_input)

        # Should be corrected to match the number of topics
        assert len(validated["rounds"]) == len(sample_user_input.topics)

    def test_adds_missing_round_fields(self, sample_user_input: UserInput):
        """Test that missing round fields are added."""
        plan = {
            "title": "Test",
            "description": "Test",
            "rounds": [
                {"topic": "History"},
                {"topic": "Science"},
            ],
        }

        validated = validate_quiz_plan(plan, sample_user_input)

        for i, round_data in enumerate(validated["rounds"]):
            assert "round_number" in round_data
            assert "round_name" in round_data
            assert "question_count" in round_data
            assert "difficulty" in round_data

    def test_preserves_valid_difficulty(self, sample_user_input: UserInput):
        """Test that valid difficulty is preserved."""
        plan = {
            "title": "Test",
            "description": "Test",
            "rounds": [
                {
                    "round_number": 1,
                    "round_name": "Round 1: History",
                    "topic": "History",
                    "question_count": 5,
                    "difficulty": "hard",
                },
                {
                    "round_number": 2,
                    "round_name": "Round 2: Science",
                    "topic": "Science",
                    "question_count": 5,
                    "difficulty": "easy",
                },
            ],
        }

        validated = validate_quiz_plan(plan, sample_user_input)

        assert validated["rounds"][0]["difficulty"] == "hard"
        assert validated["rounds"][1]["difficulty"] == "easy"

    def test_replaces_invalid_difficulty(self, sample_user_input: UserInput):
        """Test that invalid difficulty is replaced."""
        plan = {
            "title": "Test",
            "description": "Test",
            "rounds": [
                {
                    "round_number": 1,
                    "round_name": "Round 1: History",
                    "topic": "History",
                    "question_count": 5,
                    "difficulty": "invalid",
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

        validated = validate_quiz_plan(plan, sample_user_input)

        # Invalid difficulty should be replaced with user input difficulty
        assert validated["rounds"][0]["difficulty"] == sample_user_input.difficulty.value
        # Valid difficulty should be preserved
        assert validated["rounds"][1]["difficulty"] == "medium"