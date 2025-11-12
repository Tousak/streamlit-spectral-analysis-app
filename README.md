# Electrophysiology Signal Analysis Suite

## Overview

This is a comprehensive Streamlit web application for the analysis of electrophysiological data (e.g., EEG, LFP) from `.mat` files. It provides a user-friendly interface to perform advanced signal processing, visualize results, and export data for publication or further analysis.

The application is designed around a clear, powerful workflow:
1.  **Configure**: Interactively load `.mat` files and select analysis channels and time ranges, either individually or for all files at once using a global settings feature.
2.  **Calculate**: Execute a suite of signal processing tasks (PSD, PAC, Coherence, Comodulogram) with a single click.
3.  **Aggregate**: Automatically calculate hierarchical summary statistics, including means and standard error (SEM) across time segments, channels, and entire files.
4.  **Export**: Download all numerical results to a multi-sheet, publication-ready Excel file, and export all generated figures as high-quality images (`.svg`, `.png`) bundled into a single `.zip` archive.

## Quickstart

This project includes simple scripts for easy setup and execution on Windows.

### 1. Clone the Repository
First, get the project files. Open a terminal (like PowerShell or Command Prompt) and run:
```bash
git clone https://gitlab.com/Tousak/streamlit-spectral-analysis-app.git
```
This will create a `streamlit-spectral-analysis-app` folder with all the project files.

### 2. Run the Application
Navigate into the project folder. To start the application for the first time, simply double-click the **`run_app.bat`** file.

This script will automatically:
- Activate the Python virtual environment.
- Launch the Streamlit application in your default web browser.

### 3. Update the Application
To update the application with the latest changes from the repository, double-click the **`synchonize_project.bat`** file.

This script will:
- Pull the latest code using `git pull`.
- Install or update any required Python libraries from `requirements.txt`.

## Application Capabilities

*   **Flexible Data Input**: Load `.mat` files via the browser uploader or by providing a local folder path to handle large collections of files.
*   **Power Spectral Density (PSD)**: Calculate and plot the power spectrum for selected channels, including summary statistics for standard frequency bands.
*   **Phase-Amplitude Coupling (PAC)**: Compute PAC metrics (MI, MVL, PLV) to measure cross-frequency coupling.
*   **Comodulogram**: Generate heatmaps of PAC values across a grid of phase and amplitude frequencies to identify coupling relationships.
*   **Coherence**: Analyze the linear correlation between channel pairs across different frequencies.
*   **Automated Statistical Aggregation**: The application automatically calculates and organizes hierarchical means (across time, channels, and files), providing a comprehensive statistical overview.
*   **Advanced Exporting**:
    *   **Excel**: All numerical results, from raw values to grand means, are exported to a clean, multi-sheet `.xlsx` file.
    *   **Figures**: All generated plots can be exported as a `.zip` archive containing high-quality vector (`.svg`) or image (`.png`) files, ready for use in presentations or publications. The figure export process is parallelized for speed.

## File Structure
- **`app.py`**: The main script that runs the Streamlit application and organizes the UI.
- **`run_app.bat`**: A script to automatically start the application on Windows.
- **`synchonize_project.bat`**: A script to update the application from Git and install dependencies.
- **`requirements.txt`**: A list of all Python libraries required to run the project.
- **`src/`**: A folder containing the core logic for the application.
    - **`PSD.py`, `PAC.py`, `coherence.py`, `Comudologram.py`**: Modules for the core signal processing calculations.
    - **`analysis_utils.py`**: Functions for calculating hierarchical summary statistics (means, SEMs).
    - **`export_utils.py`**: Functions for flattening data structures and exporting results to Excel and zipped figures.
    - **`file_loader.py`**: UI and logic for file handling and analysis configuration.
    - **`utils.py`**: General helper functions used across the application.
    - **`plotting/`**: Modules dedicated to visualizing the results of each analysis type.

## Minimum System Requirements

These are estimates for running the application effectively. Requirements may increase with larger datasets or more complex analyses.

- **Operating System**: Windows (for `.bat` script compatibility). The Python code is cross-platform but the provided scripts are for Windows.
- **CPU**: Modern multi-core processor (e.g., Intel Core i5 / AMD Ryzen 5, 4 cores or more recommended).
- **RAM**: 
    - **8 GB** (Minimum) for smaller datasets and basic analyses.
    - **16 GB or more** (Recommended) for handling large data files, multiple analyses at once, or computationally intensive tasks like comodulograms.
- **Storage**: Sufficient free space to store your `.mat` data files.
