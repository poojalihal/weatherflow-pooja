# Week 1 Reflection — WeatherFlow

## What I built

- Created my WeatherFlow project repository on GitHub and configured the project structure, virtual environment, `.gitignore`, and dependency files.
- Studied the reference WeatherFlow project and documented its architecture and limitations.
- Developed `extract.py` to retrieve weather data from the Open-Meteo API for five UK cities.
- Created a Jupyter notebook to explore weather data and understand its structure.
- Developed `etl_v1.py` to extract, transform, and load weather records into an SQLite database.
- Successfully processed 240 hourly weather records across five UK cities.
- Created SQL queries to analyse the stored weather data.
- Improved dependency management by replacing the original frozen `requirements.txt` with a smaller, cross-platform dependency list and creating `requirements-dev.txt`.

## What went well

- Successfully configured Python, Git, GitHub, VS Code, and the project environment.
- Connected to the Open-Meteo API and retrieved weather data for all five cities.
- Built and executed an end-to-end ETL pipeline.
- Successfully loaded 240 weather records into SQLite.
- Verified that the ETL pipeline could be rerun without creating duplicate records.
- Learned how to use Git commands to track changes, commit updates, and push them to GitHub.

## What was hard, and how I solved it

1. **Understanding Git and project structure.** As a beginner in data engineering, I initially found repository organisation, Git commands, and file paths challenging. I worked through the instructions step by step and verified the results in Git Bash.

2. **Managing Python dependencies.** My original `requirements.txt` contained unnecessary packages and Windows-specific dependencies. I replaced it with a smaller list of project dependencies, created a separate development requirements file, and tested package installation in a fresh virtual environment.

3. **Understanding the ETL process.** Initially, I found it challenging to understand how extraction, transformation, and loading work together. Building and running the pipeline helped me understand how API responses become structured records in an SQLite database.

4. **Troubleshooting installation problems.** During dependency testing, I encountered package installation and compatibility issues. I used `python -m pip`, installed a missing compatible dependency in the test environment, and verified the installation using `pip check` and Python import tests.

## What surprised me

- A single API extraction could generate 240 hourly records across five cities.
- Running an ETL pipeline more than once does not necessarily create duplicates when the database loading logic is designed correctly.
- A `requirements.txt` file generated automatically with `pip freeze` can contain unnecessary dependencies and cause compatibility problems on other operating systems.
- Git and GitHub are useful not only for storing code but also for tracking the development and improvement of a project.