"""Pydantic models for quiz data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class QuestionDifficulty(str, Enum):
    """Question difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    """A single quiz question with multiple choice answers."""

    question_text: str = Field(..., min_length=10, description="The question text")
    options: Dict[str, str] = Field(
        ...,
        description="Multiple choice options (A, B, C, D)",
    )
    correct_answer: str = Field(
        ...,
        pattern="^[A-D]$",
        description="The correct answer key (A, B, C, or D)",
    )
    topic: str = Field(..., min_length=1, description="Question topic/category")
    difficulty: QuestionDifficulty = Field(
        default=QuestionDifficulty.MEDIUM,
        description="Question difficulty level",
    )
    explanation: Optional[str] = Field(
        None,
        description="Explanation of the correct answer",
    )
    quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Quality score from reviewer (0.0 to 1.0)",
    )
    feedback: Optional[str] = Field(
        None,
        description="Feedback from quality reviewer",
    )

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensure options contains exactly A, B, C, D."""
        required_keys = {"A", "B", "C", "D"}
        if set(v.keys()) != required_keys:
            raise ValueError("Options must contain exactly keys A, B, C, D")
        for key, value in v.items():
            if not value or not value.strip():
                raise ValueError(f"Option {key} cannot be empty")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, v: str) -> str:
        """Ensure correct answer is uppercase."""
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_text": "What is the capital of France?",
                "options": {
                    "A": "London",
                    "B": "Paris",
                    "C": "Berlin",
                    "D": "Madrid",
                },
                "correct_answer": "B",
                "topic": "Geography",
                "difficulty": "easy",
                "explanation": "Paris has been the capital of France since 987 AD.",
                "quality_score": 0.95,
            }
        }
    }


class QuizRound(BaseModel):
    """A round of quiz questions on a specific topic."""

    round_name: str = Field(..., min_length=1, description="Display name for the round")
    round_number: int = Field(..., ge=1, description="Round sequence number")
    topic: str = Field(..., min_length=1, description="Main topic for this round")
    questions: List[Question] = Field(
        default_factory=list,
        description="Questions in this round",
    )

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, v: List[Question]) -> List[Question]:
        """Ensure questions list is not empty if provided."""
        if v is not None and len(v) == 0:
            return v  # Allow empty list during construction
        return v

    @property
    def question_count(self) -> int:
        """Get the number of questions in this round."""
        return len(self.questions)

    model_config = {
        "json_schema_extra": {
            "example": {
                "round_name": "World Geography",
                "round_number": 1,
                "topic": "Geography",
                "questions": [],
            }
        }
    }


class QuizMetadata(BaseModel):
    """Metadata about the quiz generation process."""

    created_at: datetime = Field(default_factory=datetime.now)
    model_used: str = Field(default="claude-3-5-sonnet-20241022")
    total_tokens_used: Optional[int] = Field(None, ge=0)
    generation_time_seconds: Optional[float] = Field(None, ge=0.0)
    regeneration_count: int = Field(default=0, ge=0)
    average_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class Quiz(BaseModel):
    """A complete quiz with multiple rounds."""

    title: str = Field(..., min_length=1, description="Quiz title")
    description: Optional[str] = Field(
        None,
        description="Quiz description or instructions",
    )
    rounds: List[QuizRound] = Field(
        default_factory=list,
        description="Quiz rounds",
    )
    metadata: QuizMetadata = Field(
        default_factory=QuizMetadata,
        description="Quiz generation metadata",
    )

    @property
    def total_questions(self) -> int:
        """Calculate total number of questions across all rounds."""
        return sum(round.question_count for round in self.rounds)

    @property
    def total_rounds(self) -> int:
        """Get the total number of rounds."""
        return len(self.rounds)

    def get_questions_by_difficulty(
        self, difficulty: QuestionDifficulty
    ) -> List[Question]:
        """Get all questions of a specific difficulty level."""
        questions = []
        for round in self.rounds:
            questions.extend(
                [q for q in round.questions if q.difficulty == difficulty]
            )
        return questions

    def get_questions_by_topic(self, topic: str) -> List[Question]:
        """Get all questions for a specific topic."""
        questions = []
        for round in self.rounds:
            if round.topic.lower() == topic.lower():
                questions.extend(round.questions)
        return questions

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "General Knowledge Quiz",
                "description": "A fun quiz covering various topics",
                "rounds": [],
            }
        }
    }


class UserInput(BaseModel):
    """User input for quiz generation."""

    topics: List[str] = Field(..., min_items=1, description="Quiz topics")
    questions_per_round: int = Field(
        ...,
        ge=1,
        le=50,
        description="Number of questions per round/topic",
    )
    difficulty: QuestionDifficulty = Field(
        default=QuestionDifficulty.MEDIUM,
        description="Overall difficulty level",
    )
    quiz_title: Optional[str] = Field(None, description="Custom quiz title")
    quiz_description: Optional[str] = Field(None, description="Custom description")

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        """Clean and validate topics."""
        cleaned = [topic.strip() for topic in v if topic.strip()]
        if not cleaned:
            raise ValueError("At least one valid topic is required")
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "topics": ["History", "Science", "Geography"],
                "questions_per_round": 10,
                "difficulty": "medium",
                "quiz_title": "Pub Quiz Night",
            }
        }
    }


# Structured output models for LLM responses


class QuizPlan(BaseModel):
    """Quiz plan structure from Planner Agent."""

    title: str = Field(..., description="Quiz title")
    description: str = Field(..., description="Quiz description")
    rounds: List[Dict[str, Any]] = Field(
        ...,
        description="List of rounds with topic, question_count, etc.",
    )


class QuestionList(BaseModel):
    """List of questions from Generator Agent."""

    questions: List[Question] = Field(
        ...,
        description="List of generated questions",
    )


class QuestionReview(BaseModel):
    """Review result for a single question."""

    question_index: int
    clarity_score: float = Field(..., ge=0.0, le=1.0)
    correctness_score: float = Field(..., ge=0.0, le=1.0)
    distractor_score: float = Field(..., ge=0.0, le=1.0)
    difficulty_score: float = Field(..., ge=0.0, le=1.0)
    engagement_score: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    issues: List[str] = Field(default_factory=list)
    passed: bool


class ReviewList(BaseModel):
    """List of reviews from Reviewer Agent."""

    reviews: List[QuestionReview] = Field(
        ...,
        description="List of question reviews",
    )


class QuestionValidation(BaseModel):
    """Validation result for a single question."""

    question_index: int
    is_correct: bool
    correct_answer_valid: bool
    incorrect_options_valid: bool
    is_ambiguous: bool
    explanation_matches: bool
    issues: List[str] = Field(default_factory=list)
    suggested_fix: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class ValidationList(BaseModel):
    """List of validations from Validator Agent."""

    validations: List[QuestionValidation] = Field(
        ...,
        description="List of question validations",
    )
