@echo off
ECHO "Activating virtual environment..."

REM The 'call' command executes the activate script and then returns control to this file
call .\.venv\Scripts\activate.bat

ECHO "Starting Streamlit app..."
streamlit run app.py

ECHO "Streamlit server has been stopped."
pause
