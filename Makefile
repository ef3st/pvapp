# Code formatting with black
format:
	poetry run black .

# Run tests with pytest
test:
	poetry run pytest

# Run the main script
run:
	poetry run python src/main.py

# Command to format + test
check: format test
