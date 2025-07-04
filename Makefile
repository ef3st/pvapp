# Code formatting with black
format:
	poetry run black .

# Run tests with pytest
test:
	poetry run pytest

# Run the main script
run:
	poetry run python src/main.py

# Run ruff -> check for errors
ruff:
	poetry run ruff check src/

# Fix ruff errors -> fix the errors
ruff-fix:
	poetry run ruff check src/ --fix

# Run mypy -> check for type errors
mypy:
	poetry run mypy src/

# Run pdoc -> generate documentation
docs:
	poetry run pdoc src/ --html --output-dir docs/

# Command to format + test
check: format test ruff mypy
