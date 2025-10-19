# src/coherence.py

import numpy as np
import plotly.graph_objects as go
from scipy import signal
from scipy.ndimage import uniform_filter1d # Import the filter
# Import helper functions
from src.utils import extract_short_name, notch_filter_50hz
from src.PSD import calculate_band_power

# ==============================================================================
# 1. CORE CALCULATION AND PLOTTING ENGINES
# ==============================================================================

def _calculate_and_plot_coherence(signal1_slice, signal2_slice, fs, plot_title, F_h):
    f, Cxy = signal.coherence(signal1_slice, signal2_slice, fs=fs, nperseg=fs*2)
    fig = go.Figure(data=go.Scatter(x=f, y=Cxy, mode='lines'))
    fig.update_layout(title=plot_title, xaxis_title="Frequency (Hz)", yaxis_title="Coherence", yaxis_range=[0, 1], xaxis_range=[0, F_h])
    return fig, f, Cxy
import streamlit as st

def _calculate_and_plot_coheregram(signal1_slice, signal2_slice, fs, plot_title, F_h, time_res, freq_res):
    """
    Calculates and plots a time-resolved coheregram (heatmap) with spectral smoothing.
    """
    # st.write(f'F_h: {F_h} || time_res: {time_res} || freq_res: {freq_res}')
    
    # --- NEW: Detrend signals to remove DC offset before analysis ---
    # This is the key step to prevent artificially high coherence at low frequencies.
    signal1_slice = signal.detrend(signal1_slice, type='constant')
    signal2_slice = signal.detrend(signal2_slice, type='constant')
    # --- END NEW ---

    nperseg = int(fs / freq_res)
    noverlap = nperseg - int(fs * time_res)
    if noverlap >= nperseg:
        noverlap = nperseg - 1

    # --- 1. Get the time-resolved spectra using STFT with a Hann window ---
    f, t, Sxx = signal.stft(signal1_slice, fs=fs, nperseg=nperseg, noverlap=noverlap, window='hann')
    _, _, Syy = signal.stft(signal2_slice, fs=fs, nperseg=nperseg, noverlap=noverlap, window='hann')

    # --- 2. Calculate Power and Cross-Power Spectral Density ---
    Pxx = np.abs(Sxx)**2
    Pyy = np.abs(Syy)**2
    Pxy = Sxx * np.conj(Syy)

    # --- 3. FIX: Smooth the spectral estimates over the time axis ---
    # This averaging is essential for a meaningful coherence calculation.
    # The window size determines how much smoothing is applied.
    # A size of 3-5 is often a good starting point.
    smoothing_window_size = 5 
    
    Pxx_smoothed = uniform_filter1d(Pxx, size=smoothing_window_size, axis=1)
    Pyy_smoothed = uniform_filter1d(Pyy, size=smoothing_window_size, axis=1)
    Pxy_smoothed = uniform_filter1d(Pxy, size=smoothing_window_size, axis=1)
    # --- END FIX ---

    # --- 4. Calculate Coherence using the smoothed estimates ---
    epsilon = 1e-15
    coheregram = (np.abs(Pxy_smoothed)**2) / (Pxx_smoothed * Pyy_smoothed + epsilon)
    
    coheregram_real = coheregram.astype(np.float64)

    # Dynamic Color Range Logic
    freq_indices = np.where(f <= F_h)[0]
    filtered_data = coheregram_real[freq_indices, :]
    z_min, z_max = (np.min(filtered_data), np.max(filtered_data)) if filtered_data.size > 0 else (0, 1)
    
    # --- 5. Create the Smooth Contour Plot ---
    fig = go.Figure(data=go.Contour(
        z=coheregram_real,
        x=t + float(plot_title.split('(')[1].split('-')[0]),
        y=f,
        colorscale='Jet',
        zmin=0,
        zmax=1,
        colorbar={'title': 'Coherence'},
        contours_coloring='fill',
        line_smoothing=0.85
    ))
    fig.update_layout(
        title=plot_title,
        xaxis_title="Time (s)",
        yaxis_title="Frequency (Hz)"
    )
    fig.update_yaxes(range=[0, F_h])
    
    return fig, f, t, coheregram_real

# --- NEW FUNCTION TO PLOT BAND COHERENCE ---
def _create_band_coherence_barchart(band_means, band_errors, plot_title):
    """Creates a bar chart for the mean coherence in frequency bands."""
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    fig = go.Figure(data=go.Bar(
        x=band_labels,
        y=band_means,
        error_y=dict(type='data', array=band_errors, visible=True)
    ))
    fig.update_layout(
        title=plot_title,
        yaxis_title='Mean Coherence',
        xaxis_title='Frequency Band'
    )
    return fig
# ==============================================================================
# 2. MAIN ORCHESTRATOR FUNCTION
# ==============================================================================

def run_coherence_analysis(selections, params, pac_params, file_map, load_mat_file_func):
    """
    Main orchestrator that now also creates a barchart for band coherence.
    """
    results, figures = {}, {}

    F_h = params.get('F_h', 100)
    
    for file_name, pairs in pac_params.get('channel_pairs', {}).items():
        if file_name not in selections: continue
        mat_contents = load_mat_file_func(file_map[file_name])
        if not mat_contents: continue

        for phase_ch, amp_ch in pairs.items():
            time_ranges = selections[file_name].get(phase_ch, [])
            if not time_ranges: continue

            signal1_full = mat_contents[phase_ch]['values'].flatten()
            signal2_full = mat_contents[amp_ch]['values'].flatten()
            fs_to_use = params.get('fs', 2000)
            
            signal1_full = notch_filter_50hz(signal1_full, fs_to_use, F_h)
            signal2_full = notch_filter_50hz(signal2_full, fs_to_use, F_h)
            
            pair_name_short = f"{extract_short_name(phase_ch)} vs {extract_short_name(amp_ch)}"
            
            for time_range in time_ranges:
                time_range_str = f"{time_range[0]}-{time_range[1]}s"
                id_st, id_end = int(time_range[0] * fs_to_use), int(time_range[1] * fs_to_use)
                signal1_slice, signal2_slice = signal1_full[id_st:id_end], signal2_full[id_st:id_end]
                
                if len(signal1_slice) < fs_to_use * 2: continue

                coh_plot_name = f"Coherence | {file_name} | {pair_name_short} ({time_range_str})"
                
                fig_coh, freqs, coh_values = _calculate_and_plot_coherence(
                    signal1_slice, signal2_slice, fs_to_use, coh_plot_name, F_h
                )
                
                band_means, band_errors = calculate_band_power(coh_values, freqs, params['F_c'])
                
                # --- CREATE AND STORE THE NEW BARCHART ---
                bar_plot_name = f"Band Coherence | {file_name} | {pair_name_short} ({time_range_str})"
                fig_bar = _create_band_coherence_barchart(band_means, band_errors, bar_plot_name)

                # Store all results and figures
                results.setdefault(file_name, {}).setdefault(pair_name_short, {})[time_range_str] = {
                    'full_coherence': {'frequencies': freqs.tolist(), 'coherence': coh_values.tolist()},
                    'band_coherence': {'means': band_means.tolist(), 'errors': band_errors.tolist()}
                }
                figures.setdefault(file_name, {}).setdefault(pair_name_short, {})[coh_plot_name] = fig_coh
                figures.setdefault(file_name, {}).setdefault(pair_name_short, {})[bar_plot_name] = fig_bar # Add the new figure
                # --- Calculate and Plot Coheregram if enabled ---
                if pac_params.get('calculate_coheregram'):
                    coheregram_plot_name = f"Coheregram | {file_name} | {pair_name_short} ({time_range_str})"
                    fig_coheregram, _, _, _ = _calculate_and_plot_coheregram(
                        signal1_slice, signal2_slice, fs_to_use, 
                        coheregram_plot_name, pac_params["max_F_coherergam"], 
                        pac_params['coheregram_time_res'], pac_params['coheregram_freq_res']
                    )
                    # Storing the figure
                    figures.setdefault(file_name, {}).setdefault(pair_name_short, {})[coheregram_plot_name] = fig_coheregram
                
                # --- Store Results and Figures ---
                band_means, band_errors = calculate_band_power(coh_values, freqs, params['F_c'])
                results.setdefault(file_name, {}).setdefault(pair_name_short, {})[time_range_str] = {
                    'full_coherence': {'frequencies': freqs.tolist(), 'coherence': coh_values.tolist()},
                    'band_coherence': {'means': band_means.tolist(), 'errors': band_errors.tolist()}
                }
                figures.setdefault(file_name, {}).setdefault(pair_name_short, {})[coh_plot_name] = fig_coh

    return results, figures