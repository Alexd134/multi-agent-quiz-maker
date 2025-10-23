# Quiz Agent Usage Guide

## Setup

1. **Set your Anthropic API key:**
   ```bash
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

   Or create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

2. **Install the package** (if not already done):
   ```bash
   pip install -e .
   ```

## Basic Usage

### Generate a quiz

```bash
python main.py generate \
  --topic "World History" \
  --topic "Science" \
  --questions 10 \
  --difficulty medium \
  --output my_quiz
```

### Short form

```bash
python main.py generate -t "History" -t "Geography" -q 15 -d hard -o pub_quiz
```

## Command Options

### Required
- `-t, --topic`: Quiz topic (can specify multiple times)

### Optional
- `-q, --questions`: Questions per round (default: 10, range: 1-50)
- `-d, --difficulty`: Difficulty level - easy/medium/hard (default: medium)
- `--title`: Custom quiz title
- `--description`: Custom quiz description
- `-o, --output`: Output file path without extension (default: quiz)
- `--separate-answers/--include-answers`: Generate separate answer key (default: separate)
- `--with-answers/--no-answers`: Include answers in main quiz (default: no-answers)
- `--quality-threshold`: Minimum quality score 0.0-1.0 (default: 0.7)
- `--max-regenerations`: Max regeneration attempts (default: 3)

## Examples

### Simple quiz
```bash
python main.py generate -t "General Knowledge" -q 10
```

### Multi-topic quiz with custom settings
```bash
python main.py generate \
  -t "European History" \
  -t "World Geography" \
  -t "Basic Science" \
  -q 15 \
  -d medium \
  --title "Pub Quiz Night" \
  --description "A fun quiz for Friday night" \
  -o friday_quiz
```

### High-quality, difficult quiz
```bash
python main.py generate \
  -t "Quantum Physics" \
  -t "Ancient Philosophy" \
  -q 20 \
  -d hard \
  --quality-threshold 0.85 \
  --max-regenerations 5 \
  -o expert_quiz
```

### Quiz with answers included
```bash
python main.py generate \
  -t "Movies" \
  -t "Music" \
  -q 10 \
  --with-answers \
  --include-answers \
  -o trivia_with_answers
```

## Output Files

### Separate answers (default)
- `{output}_questions.docx` - Quiz questions only
- `{output}_answers.docx` - Answer key with explanations

### Combined (with --include-answers)
- `{output}.docx` - Single file with questions and answers

## Info Command

Get information about the quiz generator:
```bash
python main.py info
```

## Help

View all available commands and options:
```bash
python main.py --help
python main.py generate --help
```

## Environment Variables

You can configure defaults using environment variables (see `.env.example`):

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `MODEL_NAME` - Claude model to use (default: claude-3-5-sonnet-20241022)
- `DEFAULT_TEMPERATURE` - Generation temperature (default: 0.8)
- `REVIEW_TEMPERATURE` - Review temperature (default: 0.3)
- `VALIDATION_TEMPERATURE` - Validation temperature (default: 0.1)
- `QUALITY_THRESHOLD` - Default quality threshold (default: 0.7)
- `MAX_REGENERATIONS` - Default max regenerations (default: 3)

## Tips

1. **Start simple**: Begin with 1-2 topics and 10 questions to test
2. **Quality threshold**: Higher values (0.8-0.9) produce better questions but may take longer
3. **Difficulty levels**:
   - `easy`: Common knowledge, straightforward
   - `medium`: General knowledge, some thinking required
   - `hard`: Challenging, specific knowledge needed
4. **Topics**: Be specific for better results (e.g., "Ancient Roman History" vs "History")
5. **Regenerations**: More attempts = better quality but higher API costs

## Troubleshooting

### API Key Not Set
```
Error: ANTHROPIC_API_KEY environment variable not set.
```
**Solution**: Set your API key as shown in Setup section

### Generation Fails
- Check your internet connection
- Verify API key is valid
- Try reducing questions per round
- Lower quality threshold temporarily

### Low Quality Scores
- Increase `--max-regenerations`
- Try different topics (more specific is better)
- Adjust `--quality-threshold` if needed