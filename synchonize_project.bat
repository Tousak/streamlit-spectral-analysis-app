@echo off
ECHO "Activating virtual environment..."

REM Activate the virtual environment
call .\.venv\Scripts\activate.bat

ECHO "Pulling latest changes from Git..."
git pull

ECHO "Installing requirements..."
pip install -r requirements.txt

ECHO "Starting Streamlit app..."
streamlit run app.py

ECHO "Streamlit server has been stopped."
pause
