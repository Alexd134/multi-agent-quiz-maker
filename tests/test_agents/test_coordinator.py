"""Tests for the Coordinator Agent."""

from src.agents.coordinator import format_quiz, organize_questions_by_topic
from src.models.quiz import Quiz


class TestOrganizeQuestionsByTopic:
    """Test organizing questions by topic."""

    def test_groups_questions_by_topic(self, mock_quiz_state: dict):
        """Test that questions are grouped by topic."""
        topic_map = organize_questions_by_topic(mock_quiz_state)

        assert "Mathematics" in topic_map
        assert "Physics" in topic_map
        assert "Literature" in topic_map

    def test_each_topic_has_correct_questions(self, mock_quiz_state: dict):
        """Test that each topic contains the correct questions."""
        topic_map = organize_questions_by_topic(mock_quiz_state)

        # Check Mathematics questions
        math_questions = topic_map["Mathematics"]
        assert len(math_questions) == 1
        assert math_questions[0].question_text == "What is 2 + 2?"

        # Check Physics questions
        physics_questions = topic_map["Physics"]
        assert len(physics_questions) == 1
        assert physics_questions[0].question_text == "What is the speed of light?"


class TestFormatQuiz:
    """Test quiz formatting."""

    def test_creates_quiz_with_correct_structure(self, mock_quiz_state: dict):
        """Test that format_quiz creates a Quiz object."""
        result = format_quiz(mock_quiz_state)

        assert "final_quiz" in result
        assert isinstance(result["final_quiz"], Quiz)

    def test_quiz_has_correct_title(self, mock_quiz_state: dict):
        """Test that quiz has correct title."""
        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        assert quiz.title == "Test Quiz"

    def test_quiz_has_correct_description(self, mock_quiz_state: dict):
        """Test that quiz has correct description."""
        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        assert quiz.description == "A test quiz"

    def test_quiz_has_correct_number_of_rounds(self, mock_quiz_state: dict):
        """Test that quiz has correct number of rounds."""
        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        # Should have 2 rounds (History and Science)
        assert len(quiz.rounds) == 2

    def test_quiz_metadata_includes_regeneration_count(self, mock_quiz_state: dict):
        """Test that metadata includes regeneration count."""
        mock_quiz_state["feedback_loop_count"] = 2

        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        assert quiz.metadata.regeneration_count == 2

    def test_quiz_metadata_calculates_average_quality(self, mock_quiz_state: dict):
        """Test that metadata calculates average quality score."""
        # Set quality scores on questions
        for i, question in enumerate(mock_quiz_state["validated_questions"]):
            question.quality_score = 0.8 + (i * 0.05)

        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        assert quiz.metadata.average_quality_score is not None
        assert 0.8 <= quiz.metadata.average_quality_score <= 0.95

    def test_handles_empty_questions_gracefully(self, mock_quiz_state: dict):
        """Test that empty questions list is handled."""
        mock_quiz_state["validated_questions"] = []

        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        assert quiz.title is not None
        assert len(quiz.rounds) == 0

    def test_rounds_have_correct_structure(self, mock_quiz_state: dict):
        """Test that rounds have all required fields."""
        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        for round_obj in quiz.rounds:
            assert round_obj.round_number > 0
            assert round_obj.round_name is not None
            assert round_obj.topic is not None
            assert len(round_obj.questions) > 0

    def test_questions_grouped_by_topic_in_rounds(self, mock_quiz_state: dict):
        """Test that questions are correctly grouped by topic in rounds."""
        result = format_quiz(mock_quiz_state)
        quiz = result["final_quiz"]

        # Find History round
        history_round = next(r for r in quiz.rounds if r.topic == "History")
        # All questions in this round should have History topic
        for question in history_round.questions:
            assert question.topic == "History"

        # Find Science round
        science_round = next(r for r in quiz.rounds if r.topic == "Science")
        # All questions in this round should have Science topic
        for question in science_round.questions:
            assert question.topic == "Science"