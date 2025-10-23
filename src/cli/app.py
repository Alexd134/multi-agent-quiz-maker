"""Typer CLI application for quiz generation."""

import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.export.docx_generator import export_quiz_with_separate_answers, export_to_docx
from src.graph.state import create_initial_state
from src.graph.workflow import compile_workflow
from src.models.quiz import QuestionDifficulty, UserInput

app = typer.Typer(
    name="quiz-agent",
    help="AI-powered quiz generator using multi-agent system",
    add_completion=False,
)

console = Console()


@app.command()
def generate(
    topics: List[str] = typer.Option(
        ...,
        "--topic",
        "-t",
        help="Quiz topics (can specify multiple times: -t History -t Science)",
    ),
    questions_per_round: int = typer.Option(
        10,
        "--questions",
        "-q",
        help="Number of questions per round/topic",
        min=1,
        max=50,
    ),
    difficulty: QuestionDifficulty = typer.Option(
        QuestionDifficulty.MEDIUM,
        "--difficulty",
        "-d",
        help="Overall difficulty level",
        case_sensitive=False,
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        help="Custom quiz title",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        help="Custom quiz description",
    ),
    output: str = typer.Option(
        "quiz",
        "--output",
        "-o",
        help="Output file path (without extension)",
    ),
    separate_answers: bool = typer.Option(
        True,
        "--separate-answers/--include-answers",
        help="Generate separate answer key file vs include answers in quiz",
    ),
    include_answers: bool = typer.Option(
        False,
        "--with-answers/--no-answers",
        help="Include answers in the main quiz document",
    ),
    quality_threshold: float = typer.Option(
        0.7,
        "--quality-threshold",
        help="Minimum quality score for questions (0.0-1.0)",
        min=0.0,
        max=1.0,
    ),
    max_regenerations: int = typer.Option(
        3,
        "--max-regenerations",
        help="Maximum number of regeneration attempts for low-quality questions",
        min=0,
        max=10,
    ),
) -> None:
    """
    Generate a quiz using AI agents.

    Example:
        quiz-agent generate -t "World History" -t "Science" -q 15 -d medium -o my_quiz
    """
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.",
            style="bold",
        )
        console.print(
            "\nPlease set your API key:\n  export ANTHROPIC_API_KEY='your-key-here'"
        )
        raise typer.Exit(code=1)

    # Display configuration
    display_config(
        topics, questions_per_round, difficulty, title, description, output
    )

    # Create user input
    user_input = UserInput(
        topics=topics,
        questions_per_round=questions_per_round,
        difficulty=difficulty,
        quiz_title=title,
        quiz_description=description,
    )

    # Create initial state
    state = create_initial_state(user_input)
    state["quality_threshold"] = quality_threshold
    state["max_regeneration_attempts"] = max_regenerations

    # Compile workflow
    console.print("\n[cyan]Initializing multi-agent workflow...[/cyan]")
    workflow = compile_workflow()

    # Run workflow with progress indicator
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Generating quiz with AI agents...", total=None
            )

            # Execute the workflow
            final_state = workflow.invoke(state)

            progress.update(task, description="[green]Quiz generation complete!")

    except Exception as e:
        console.print(f"\n[red]Error during quiz generation:[/red] {e}", style="bold")
        raise typer.Exit(code=1)

    # Get the final quiz
    quiz = final_state.get("final_quiz")

    if not quiz:
        console.print(
            "[red]Error:[/red] Quiz generation failed - no quiz produced.",
            style="bold",
        )
        raise typer.Exit(code=1)

    # Display results
    display_quiz_summary(quiz, final_state)

    # Export to DOCX
    console.print("\n[cyan]Exporting to DOCX...[/cyan]")

    try:
        if separate_answers:
            questions_file, answers_file = export_quiz_with_separate_answers(
                quiz, output
            )
            console.print(f"\n[green]✓[/green] Quiz exported successfully!")
            console.print(f"  Questions: {questions_file}")
            console.print(f"  Answers:   {answers_file}")
        else:
            output_file = export_to_docx(quiz, f"{output}.docx", include_answers)
            console.print(f"\n[green]✓[/green] Quiz exported to: {output_file}")

    except Exception as e:
        console.print(f"\n[red]Error during export:[/red] {e}", style="bold")
        raise typer.Exit(code=1)

    console.print("\n[green bold]Quiz generation complete![/green bold]")


@app.command()
def info() -> None:
    """Display information about the quiz generator."""
    info_text = """
[bold cyan]AI Quiz Generator[/bold cyan]
Version: 0.1.0

[bold]Multi-Agent System:[/bold]
  • Planner Agent - Creates quiz structure
  • Generator Agent - Generates questions using Claude
  • Reviewer Agent - Reviews question quality
  • Validator Agent - Validates answer correctness
  • Coordinator Agent - Formats final output

[bold]Features:[/bold]
  • AI-powered question generation
  • Multi-layer quality assurance
  • Automatic feedback loops
  • Professional DOCX output
  • Customizable difficulty levels

[bold]Model:[/bold] Claude 3.5 Sonnet (Anthropic)
    """
    console.print(Panel(info_text, title="Quiz Agent Info", border_style="cyan"))


def display_config(
    topics: List[str],
    questions_per_round: int,
    difficulty: QuestionDifficulty,
    title: Optional[str],
    description: Optional[str],
    output: str,
) -> None:
    """Display the configuration before generation."""
    table = Table(title="Quiz Configuration", show_header=False, border_style="cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Topics", ", ".join(topics))
    table.add_row("Questions per round", str(questions_per_round))
    table.add_row("Difficulty", difficulty.value.capitalize())
    if title:
        table.add_row("Title", title)
    if description:
        table.add_row("Description", description)
    table.add_row("Output", output)

    console.print()
    console.print(table)


def display_quiz_summary(quiz, state) -> None:
    """Display a summary of the generated quiz."""
    console.print("\n[bold green]Quiz Generated Successfully![/bold green]")

    # Main stats
    table = Table(title="Quiz Summary", border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Title", quiz.title)
    table.add_row("Total Rounds", str(quiz.total_rounds))
    table.add_row("Total Questions", str(quiz.total_questions))

    if quiz.metadata.average_quality_score:
        score = quiz.metadata.average_quality_score
        score_str = f"{score:.2f}"
        if score >= 0.8:
            score_str = f"[green]{score_str}[/green]"
        elif score >= 0.7:
            score_str = f"[yellow]{score_str}[/yellow]"
        else:
            score_str = f"[red]{score_str}[/red]"
        table.add_row("Avg Quality Score", score_str)

    if quiz.metadata.regeneration_count > 0:
        table.add_row("Regenerations", str(quiz.metadata.regeneration_count))

    console.print()
    console.print(table)

    # Rounds breakdown
    rounds_table = Table(title="Rounds Breakdown", border_style="cyan")
    rounds_table.add_column("Round", style="cyan")
    rounds_table.add_column("Topic", style="white")
    rounds_table.add_column("Questions", style="white")

    for round_data in quiz.rounds:
        rounds_table.add_row(
            str(round_data.round_number),
            round_data.topic,
            str(round_data.question_count),
        )

    console.print()
    console.print(rounds_table)


@app.callback()
def callback() -> None:
    """
    AI Quiz Generator - Create quizzes using multi-agent AI system.
    """
    pass


if __name__ == "__main__":
    app()