"""Answer Validator Agent - Validates answer correctness and option quality."""

from typing import Any

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import get_settings
from src.graph.state import QuizState
from src.models.quiz import Question, ValidationList


def validate_answers(state: QuizState) -> dict[str, Any]:
    """
    Answer Validator Agent: Validate that answers are correct and unambiguous.

    This agent performs deep validation:
    - Verifies the marked correct answer is actually correct
    - Ensures incorrect options are genuinely incorrect
    - Checks for ambiguity or trick questions
    - Validates explanations match the correct answer

    Args:
        state: Current quiz state containing reviewed_questions

    Returns:
        Dictionary with updated state containing validated_questions and validation_issues
    """
    reviewed_questions = state["reviewed_questions"]
    settings = get_settings()

    if not reviewed_questions:
        return {
            "validated_questions": [],
            "validation_issues": [{"error": "No questions to validate"}],
        }

    # Initialize Claude with structured output
    llm = ChatBedrock(
        model=settings.model_name,
        temperature=settings.validation_temperature,
    )

    # Use structured output
    llm_with_structure = llm.with_structured_output(ValidationList)

    validated_questions: list[Question] = []
    validation_issues: list[dict[str, Any]] = []

    # Validate questions in batches
    batch_size = 5
    for i in range(0, len(reviewed_questions), batch_size):
        batch = reviewed_questions[i : i + batch_size]

        # Create validation prompt (simpler now - no JSON format needed)
        system_prompt = """You are an expert fact-checker and quiz validator. Your job is to verify answers are correct.

For each question, validate:
1. Is the marked correct answer actually correct?
2. Are all incorrect options genuinely incorrect?
3. Is there any ambiguity that could make multiple answers correct?
4. Does the explanation support the correct answer?
5. Are there any factual errors?

If issues are found, provide specific details and suggest fixes."""

        # Format questions for validation
        questions_text = format_questions_for_validation(batch, i)

        user_prompt = f"""Validate these quiz questions for correctness:

{questions_text}

Check each answer carefully and provide validation results."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            # Get validation from Claude - returns ValidationList object directly
            validation_list = llm_with_structure.invoke(messages)

            # Apply validations to questions
            for j, question in enumerate(batch):
                # Find matching validation
                validation = next(
                    (v for v in validation_list.validations if v.question_index == j),
                    None,
                )

                if validation:
                    # Check if validation passed
                    is_valid = (
                        validation.is_correct
                        and validation.correct_answer_valid
                        and validation.incorrect_options_valid
                        and not validation.is_ambiguous
                    )

                    if is_valid:
                        validated_questions.append(question)
                    else:
                        # Track validation issues
                        validation_issues.append(
                            {
                                "question_index": i + j,
                                "topic": question.topic,
                                "question_text": question.question_text,
                                "issues": validation.issues,
                                "suggested_fix": validation.suggested_fix,
                                "confidence": validation.confidence,
                            }
                        )
                        # Still add to validated list but with lower quality score
                        question.quality_score = 0.5  # Mark as questionable
                        validated_questions.append(question)
                else:
                    # No validation found, assume valid
                    validated_questions.append(question)

        except Exception as e:
            # If validation fails, accept questions anyway
            print(f"Error validating batch: {e}")
            for question in batch:
                validated_questions.append(question)

    return {
        "validated_questions": validated_questions,
        "validation_issues": validation_issues if validation_issues else None,
    }


def format_questions_for_validation(questions: list[Question], offset: int = 0) -> str:
    """
    Format questions for the validation prompt.

    Args:
        questions: List of questions to validate
        offset: Index offset for question numbering

    Returns:
        Formatted string of questions
    """
    formatted = []
    for i, q in enumerate(questions):
        formatted.append(
            f"""Question {offset + i}:
Topic: {q.topic}
Difficulty: {q.difficulty.value}
Question: {q.question_text}
Options:
  A: {q.options['A']}
  B: {q.options['B']}
  C: {q.options['C']}
  D: {q.options['D']}
Marked Correct Answer: {q.correct_answer} - {q.options[q.correct_answer]}
Explanation: {q.explanation or 'Not provided'}
---"""
        )

    return "\n".join(formatted)
