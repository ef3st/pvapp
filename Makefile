# Code formatting with black
format:
	poetry run black .

# Run tests with pytest
test:
	poetry run pytest

# Run the main script
run:
	poetry run python src/solartracker/main.py

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


# Run Jupyter Notebook with Poetry
notebook:
	poetry run jupyter notebook

# Register the environment as a Jupyter kernel (one-time)
register-kernel:
	poetry run python -m ipykernel install --user --name=solartracker --display-name "Python (solartracker)"

# Run Jupyter Lab (optional, if you use it)
lab:
	poetry run jupyter lab

streamlit:
	poetry run streamlit run src/solartracker/main.py --logger.level=debug gui

downloader-doc: 
	poetry run streamlit run src/documentation/docbuilder.py

developer:
	poetry run python src/solartracker/main.py dev

count_lines:
	cloc . --include-ext=py