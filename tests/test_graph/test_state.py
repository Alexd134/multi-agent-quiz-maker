"""Tests for LangGraph state management."""

from src.graph.state import create_initial_state
from src.models.quiz import QuestionDifficulty, UserInput


class TestCreateInitialState:
    """Test initial state creation."""

    def test_creates_state_with_user_input(self, sample_user_input: UserInput):
        """Test that initial state contains user input."""
        state = create_initial_state(sample_user_input)

        assert "user_input" in state
        assert state["user_input"] == sample_user_input

    def test_initializes_empty_lists(self, sample_user_input: UserInput):
        """Test that lists are initialized as empty."""
        state = create_initial_state(sample_user_input)

        assert state["raw_questions"] == []
        assert state["reviewed_questions"] == []
        assert state["validated_questions"] == []

    def test_initializes_feedback_loop_count(self, sample_user_input: UserInput):
        """Test that feedback loop count is initialized to 0."""
        state = create_initial_state(sample_user_input)

        assert state["feedback_loop_count"] == 0

    def test_initializes_max_regeneration_attempts(self, sample_user_input: UserInput):
        """Test that max regeneration attempts is set."""
        state = create_initial_state(sample_user_input)

        assert state["max_regeneration_attempts"] == 3

    def test_initializes_needs_regeneration_flag(self, sample_user_input: UserInput):
        """Test that needs_regeneration is initialized to False."""
        state = create_initial_state(sample_user_input)

        assert state["needs_regeneration"] is False

    def test_quiz_plan_is_none_initially(self, sample_user_input: UserInput):
        """Test that quiz_plan starts as None."""
        state = create_initial_state(sample_user_input)

        assert state["quiz_plan"] is None

    def test_final_quiz_is_none_initially(self, sample_user_input: UserInput):
        """Test that final_quiz starts as None."""
        state = create_initial_state(sample_user_input)

        assert state["final_quiz"] is None

    def test_review_feedback_is_none_initially(self, sample_user_input: UserInput):
        """Test that review_feedback starts as None."""
        state = create_initial_state(sample_user_input)

        assert state["review_feedback"] is None

    def test_validation_issues_is_empty_initially(self, sample_user_input: UserInput):
        """Test that validation_issues starts as empty list."""
        state = create_initial_state(sample_user_input)

        assert state["validation_issues"] == []

    def test_state_is_mutable(self, sample_user_input: UserInput):
        """Test that state can be modified."""
        state = create_initial_state(sample_user_input)

        # Modify state
        state["feedback_loop_count"] = 1
        state["needs_regeneration"] = True

        assert state["feedback_loop_count"] == 1
        assert state["needs_regeneration"] is True

    def test_state_with_different_user_inputs(self):
        """Test that different user inputs create different states."""
        user_input_1 = UserInput(
            topics=["Topic A"],
            questions_per_round=5,
            difficulty=QuestionDifficulty.EASY,
        )

        user_input_2 = UserInput(
            topics=["Topic B", "Topic C"],
            questions_per_round=10,
            difficulty=QuestionDifficulty.HARD,
        )

        state_1 = create_initial_state(user_input_1)
        state_2 = create_initial_state(user_input_2)

        assert state_1["user_input"].topics == ["Topic A"]
        assert state_2["user_input"].topics == ["Topic B", "Topic C"]

        assert state_1["user_input"].questions_per_round == 5
        assert state_2["user_input"].questions_per_round == 10