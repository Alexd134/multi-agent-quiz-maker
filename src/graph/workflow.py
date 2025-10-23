"""LangGraph workflow definition for quiz generation."""

from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.coordinator import format_quiz
from src.agents.generator import generate_questions
from src.agents.planner import create_quiz_plan
from src.agents.reviewer import review_questions
from src.agents.validator import validate_answers
from src.graph.state import QuizState


def should_regenerate(state: QuizState) -> Literal["regenerate", "validate"]:
    """
    Determine if questions need regeneration based on quality scores.

    Args:
        state: Current quiz state

    Returns:
        "regenerate" if quality is below threshold, "validate" otherwise
    """
    if state.get("needs_regeneration", False):
        # Check if we've hit max attempts
        if state["feedback_loop_count"] >= state["max_regeneration_attempts"]:
            # Give up and proceed to validation
            return "validate"
        return "regenerate"
    return "validate"


def should_continue_after_validation(
    state: QuizState,
) -> Literal["coordinator", "regenerate", "end"]:
    """
    Determine next step after validation.

    Args:
        state: Current quiz state

    Returns:
        Next node to execute
    """
    validation_issues = state.get("validation_issues", [])

    if validation_issues and len(validation_issues) > 0:
        # Check if we've hit max attempts
        if state["feedback_loop_count"] >= state["max_regeneration_attempts"]:
            # Proceed anyway with warnings
            return "coordinator"
        # Try to fix the issues
        return "regenerate"

    return "coordinator"


def create_quiz_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for quiz generation.

    The workflow follows this structure:
    1. Planner - Creates quiz structure
    2. Generator - Generates questions (parallel per topic)
    3. Reviewer - Reviews quality
    4. [Conditional] Regenerate if quality is low
    5. Validator - Validates answers
    6. [Conditional] Regenerate if validation fails
    7. Coordinator - Formats final quiz

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(QuizState)

    # Add nodes for each agent
    workflow.add_node("planner", create_quiz_plan)
    workflow.add_node("generator", generate_questions)
    workflow.add_node("reviewer", review_questions)
    workflow.add_node("validator", validate_answers)
    workflow.add_node("coordinator", format_quiz)

    # Define the flow
    # Start -> Planner
    workflow.set_entry_point("planner")

    # Planner -> Generator
    workflow.add_edge("planner", "generator")

    # Generator -> Reviewer
    workflow.add_edge("generator", "reviewer")

    # Reviewer -> Conditional (regenerate or validate)
    workflow.add_conditional_edges(
        "reviewer",
        should_regenerate,
        {
            "regenerate": "generator",  # Loop back to regenerate
            "validate": "validator",  # Proceed to validation
        },
    )

    # Validator -> Conditional (regenerate, coordinator, or end)
    workflow.add_conditional_edges(
        "validator",
        should_continue_after_validation,
        {
            "regenerate": "generator",  # Loop back to fix issues
            "coordinator": "coordinator",  # Proceed to final formatting
            "end": END,  # Should not normally reach here
        },
    )

    # Coordinator -> End
    workflow.add_edge("coordinator", END)

    return workflow


def compile_workflow() -> StateGraph:
    """
    Compile the workflow and return it ready for execution.

    Returns:
        Compiled workflow
    """
    workflow = create_quiz_workflow()
    return workflow.compile()