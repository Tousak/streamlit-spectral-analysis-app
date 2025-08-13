# Description

## Electrophysiology Signal Analysis Suite
This is a comprehensive Streamlit web application designed for the analysis of electrophysiological data (such as EEG or LFP signals) stored in .mat files. It provides a user-friendly interface to perform a variety of advanced signal processing tasks, visualize the results, and export the data for further analysis.

The application is a Python-based replication and extension of a MATLAB analysis pipeline, offering interactive plots and flexible parameter configuration.

## Features
This application supports a wide range of standard electrophysiological analyses:

### Interactive Data Handling:
Upload .mat files directly through the browser.
For local use, load all files from a specified folder path, bypassing browser upload limits.
Dynamically select channels and define multiple time ranges for analysis.

### Power Spectral Density (PSD)
Calculates and plots the power spectrum of a signal, including summary statistics (mean and SEM) for standard frequency bands (Delta, Theta, Alpha, Beta, Gamma).

### Spectrogram
Generates time-frequency plots to visualize how the spectral content of a signal changes over time for specific intervals.

### Phase-Amplitude Coupling (PAC)
Calculates PAC metrics (Modulation Index, Mean Vector Length, Phase-Locking Value) for user-defined phase and amplitude frequency bands.
Supports both within-channel and between-channel (cross-channel) PAC analysis.
Includes an optional sliding-window analysis to view PAC changes over time.

### Comodulogram
Creates a heatmap (or smooth contour plot) of Modulation Index values across a grid of phase and amplitude frequencies to identify coupling relationships.

### Coherence
Calculates the magnitude-squared coherence between two paired channels to measure their linear correlation at different frequencies.
Provides summary statistics for coherence within standard frequency bands.

### Coheregram
Generates a time-frequency heatmap of coherence, showing how the correlation between two signals evolves over time.

### Data Export
Export all numerical results (including summary statistics) to a multi-sheet Excel file.

The Excel export can be configured to create detailed "dashboards" with plots embedded alongside the data tables.

# Installation
🚀 Getting Started
Follow these instructions to set up and run the application on a local computer. This guide assumes you have Git and Python installed.

## 1. Clone the Repository
First, you need to get the project files from the Git repository.

Create a Folder: Create a new, empty folder on your computer where you want to store the project (e.g., C:\Projects\AnalysisApp).

Open Terminal: Right-click on the folder you just created and select "Open in Terminal" (or a similar option like "Open PowerShell window here").

Clone the Code: In the terminal, run the following command. Replace <your-git-repository-ssh-link> with the actual SSH or HTTPS link from your Git provider.

git clone <your-git-repository-ssh-link> .

(Note: The . at the end clones the files directly into your current folder.)

## 2. Set Up the Python Environment
It is highly recommended to use a virtual environment to keep the project's dependencies isolated.

Create the Environment: In the same terminal, run this command to create a virtual environment folder named .venv.

python -m venv .venv

Activate the Environment: To start using the environment, run the following command. You will need to do this every time you open a new terminal to work on the project.

For Windows PowerShell
.\.venv\Scripts\Activate.ps1

You should see (.venv) appear at the beginning of your terminal prompt.

## 3. Install Dependencies
Install all the required Python libraries using the requirements.txt file.

Install Libraries: With your virtual environment active, run this single command:

pip install -r requirements.txt

## 4. Run the Application
You are now ready to start the app.

Launch Streamlit: In the terminal (with the environment still active), run:

streamlit run app.py

View in Browser: A new tab should automatically open in your web browser with the application running, typically at http://localhost:8501.


# How to Use the App
## Load Data
Use either "Option A: Upload Files" to select .mat files from your computer or, if running locally, use "Option B: Load from Folder" to load all files from a specific directory path.

#### 1. Configure Files
For each loaded file, an expander will appear.

#### 2. Select Channels
Use the multiselect box to choose which channels you want to analyze.

#### 3. Define Time Ranges
For each selected channel, a text box will appear. Enter the start and end times (in seconds) for the analysis intervals (e.g., 10 20; 30 45).

## Set Analysis Parameters
Use the global settings sections to configure the parameters for PSD, PAC, Coherence, and Comodulogram calculations.

#### Run Analysis
Click the "Start Calculation" button for the desired analysis. The app will process the data according to your configuration.

## View and Export

#### Plots
After the calculation is complete, a multiselect box will appear, allowing you to choose which of the generated plots to display.

#### Results
The numerical results are stored and can be viewed in an expander.

#### Export
Click the "Download Results as Excel" button to save all numerical data to a structured .xlsx file.


# File Structure
**app.py:** The main script that runs the Streamlit application and organizes the UI.

**requirements.txt:** A list of all Python libraries required to run the project.

**src/:** A folder containing the core logic for the application.

**PSD.py:** Functions for PSD and spectrogram analysis.

**PAC.py:** Functions for Phase-Amplitude Coupling analysis.

**Coherence.py:** Functions for coherence and coheregram analysis.

**Comodulogram.py:** Functions for comodulogram analysis.

**analysis_utils.py:** Functions for calculating summary statistics (means, SEMs).

**export_utils.py:** Functions for exporting results to Excel.

**file_loader.py:** UI and logic for file handling and channel configuration.

**utils.py:** General helper functions used across the application.