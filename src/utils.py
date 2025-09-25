import re
import streamlit as st
from functools import partial
from scipy import signal
from src import export_utils

def set_calculated_values_in_session_state():
    """Set the comod_figures state flag to False."""
    # st.session_state.selections = False

    st.session_state.psd_results = False
    st.session_state.psd_figures = False
    
    st.session_state.pac_figures= False
    st.session_state.pac_results= False

    st.session_state.coh_figures = False
    st.session_state.coh_results = False
    
    st.session_state.comod_figures = False
    st.session_state.results_with_means = False

    st.session_state.results = False
    export_utils.create_figures_zip_fast.clear()
    st.session_state.png_zip_bytes = None
    st.session_state.svg_zip_bytes = None
    st.session_state.button_png = False
    st.session_state.button_svg = False

# Pre-make the partial so it can be used directly in widgets
reset_values = partial(set_calculated_values_in_session_state)



def rest_after_upload_change():
    st.session_state.selections = False
    set_calculated_values_in_session_state()

reset_upload = partial(rest_after_upload_change)


# --- Replicating MATLAB's setResolution function ---
def calculate_spectrogram_params(fs, desired_freq_res, desired_time_res):
    """
    Calculates window size and overlap for a spectrogram based on desired resolutions.
    - Frequency resolution (Δf) is determined by window size (N): Δf ≈ fs / N
    - Time resolution (Δt) is determined by the hop size (H): Δt = H / fs
    """
    # Calculate window size from desired frequency resolution
    win_size = int(round(fs / desired_freq_res))
    
    # Calculate hop size from desired time resolution
    hop_size = int(round(fs * desired_time_res))
    
    # Calculate overlap
    noverlap = win_size - hop_size
    
    # Ensure overlap is valid
    if noverlap < 0:
        st.warning(f"Warning: Incompatible resolutions. Time resolution may be too coarse for the given frequency resolution.")
        noverlap = 0 # Prevent negative overlap

    overlap_percent = (noverlap / win_size) * 100 if win_size > 0 else 0
    
    return win_size, noverlap, overlap_percent

def parse_time_ranges(text_input):
    """
    Parses a string like "10 20; 30 40" into a list of lists [[10, 20], [30, 40]].
    Returns the list on success or None on failure.
    """
    ranges = []
    # Split by semicolon to get individual pairs
    pairs = text_input.strip().split(';')
    for pair in pairs:
        if not pair.strip():
            continue # Skip empty entries
        
        # Split by space and convert to floats
        parts = pair.strip().split()
        if len(parts) != 2:
            return None # Invalid pair
        
        try:
            start = float(parts[0])
            end = float(parts[1])
            if start >= end: # Start must be less than end
                return None
            ranges.append([start, end])
        except ValueError:
            return None # Not valid numbers
            
    return ranges    

# Function to extract the short name
def extract_short_name(full_name):
    match = re.search(r"Ch\d+$", full_name)
    return match.group() if match else full_name

def notch_filter_50hz(data, fs, F_h):
    max_harmonic = int((F_h - 1) / 50)
    filtered_data = data
    for i in range(1, max_harmonic + 1):
        f0 = 50.0 * i
        Q = f0 / 2.0
        b, a = signal.iirnotch(f0, Q, fs)
        filtered_data = signal.filtfilt(b, a, filtered_data)
    return filtered_data

def remove_invalid_chars(text):
    return text.replace('_', ' ')

def merge_results_from_session():
    merged_results = {}

    for key, value in st.session_state.items():
        if key.endswith("_results") and isinstance(value, dict):
            # Store under the same key to preserve origin
            merged_results[key] = value

    return merged_results