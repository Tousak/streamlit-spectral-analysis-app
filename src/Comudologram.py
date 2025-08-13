# src/Comodulogram.py

import numpy as np
import plotly.graph_objects as go
from scipy import signal
# Import the notch filter from your existing PSD module
from src import utils

# ==============================================================================
# 1. HELPER FUNCTION (Equivalent to ModIndex_v2)
# ==============================================================================

def _calculate_mi(phase_series, amp_series, n_bins):
    """Calculates the Modulation Index (MI) using the KL-divergence method."""
    bin_edges = np.linspace(-np.pi, np.pi, n_bins + 1)
    binned_phase = np.digitize(phase_series, bin_edges)
    
    mean_amp_by_bin = np.array([
        np.mean(amp_series[binned_phase == i]) for i in range(1, n_bins + 1)
    ])
    mean_amp_by_bin = np.nan_to_num(mean_amp_by_bin, nan=1e-15) # Avoid NaNs
    
    p_norm = mean_amp_by_bin / np.sum(mean_amp_by_bin)
    
    # Calculate entropy and MI
    H = -np.sum(p_norm * np.log(p_norm + 1e-15))
    MI = (np.log(n_bins) - H) / np.log(n_bins)
    return MI

# ==============================================================================
# 2. CORE CALCULATION ENGINE (Equivalent to cmd_try)
# ==============================================================================

def _calculate_and_plot_comodulogram(data_slice, fs, chann_name, time_range_str, params):
    """
    Core function with improved filter logic for near-zero frequencies.
    """
    chann_name = utils.remove_invalid_chars(chann_name)
    
    # You can now set start to a small positive number, e.g., 0.1
    phase_start = params['phase_vec_start']
    amp_start = params['amp_vec_start']
    
    # Ensure start values are not exactly zero
    if phase_start <= 0: phase_start = 0.1
    if amp_start <= 0: amp_start = 0.1
    
    phase_vec = np.arange(phase_start, params['phase_vec_end'], params['phase_vec_dt'])
    amp_vec = np.arange(amp_start, params['amp_vec_end'], params['amp_vec_dt'])
    
    phase_bw = params['phase_vec_dt'] / 2.0
    amp_bw = params['amp_vec_dt'] / 4.0
    
    lfp = utils.notch_filter_50hz(data_slice, fs, params['F_h'])

    # --- Filtering and Hilbert transform (MODIFIED LOGIC) ---
    amp_envelopes = []
    for i, amp_f in enumerate(amp_vec):
        f_high = amp_f + amp_bw
        # Use a lowpass filter for the first bin if it's near zero
        if i == 0 and amp_f < 1.0:
            b, a = signal.butter(4, f_high, btype='lowpass', fs=fs)
        else:
            b, a = signal.butter(4, [amp_f, f_high], btype='bandpass', fs=fs)
        filtered_amp = signal.filtfilt(b, a, lfp)
        amp_envelopes.append(np.abs(signal.hilbert(filtered_amp)))

    phase_series_list = []
    for i, phase_f in enumerate(phase_vec):
        f_high = phase_f + phase_bw
        # Use a lowpass filter for the first bin if it's near zero
        if i == 0 and phase_f < 1.0:
            b, a = signal.butter(4, f_high, btype='lowpass', fs=fs)
        else:
            b, a = signal.butter(4, [phase_f, f_high], btype='bandpass', fs=fs)
        filtered_phase = signal.filtfilt(b, a, lfp)
        phase_series_list.append(np.angle(signal.hilbert(filtered_phase)))
        
    # --- Compute MI and comodulogram matrix ---
    comodulogram = np.zeros((len(amp_vec), len(phase_vec)))
    for i, phase_series in enumerate(phase_series_list):
        for j, amp_envelope in enumerate(amp_envelopes):
            MI = _calculate_mi(phase_series, amp_envelope, params['n_bins'])
            comodulogram[j, i] = MI
    
    # --- Plot comodulogram using Plotly Contour (MODIFIED) ---
    fig = go.Figure(data=go.Contour(
        z=comodulogram,
        x=phase_vec + phase_bw / 2,
        y=amp_vec + amp_bw / 2,
        colorscale='Jet',
        contours_coloring='fill', # This creates the filled effect like contourf
        line_smoothing=0.85,      # This makes the contours smooth
        zmin=params['cax_cmd_vals'][0],
        zmax=params['cax_cmd_vals'][1],
        colorbar={'title': 'Modulation Index'}
    ))
    fig.update_layout(
        title=f'Comodulogram: {chann_name} ({time_range_str})',
        xaxis_title='Phase Frequency (Hz)',
        yaxis_title='Amplitude Frequency (Hz)'
    )
    
    return fig, comodulogram

# ==============================================================================
# 3. MAIN ORCHESTRATOR FUNCTION
# ==============================================================================

def run_comodulogram_analysis(selections, params, file_map, load_mat_file_func):
    """
    Main orchestrator for running Comodulogram analysis on all configured time ranges.
    """
    results = {}
    figures = {}

    for file_name, channels in selections.items():
        if not channels or 'pac_config' in file_name: continue
        
        file_item = file_map.get(file_name)
        if not file_item: continue
        
        mat_contents = load_mat_file_func(file_item)
        if mat_contents is None: continue

        for channel_name, time_ranges in channels.items():
            if channel_name == 'pac_config' or not time_ranges: continue
            
            # Extract the full signal and time vector once
            channel_data = mat_contents[channel_name]
            signal_values = channel_data['values'].flatten()
            available_fields = channel_data.dtype.names if hasattr(channel_data, 'dtype') else channel_data.keys()

            if 'times' in available_fields:
                time_vector = channel_data['times'].flatten()
                duration = time_vector[-1] - time_vector[0]
                fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
            else:
                fs_to_use = params['fs']
            
            # Loop to run analysis on each individual time range
            for time_range in time_ranges:
                time_range_str = f"{time_range[0]}-{time_range[1]}s"
                
                # Extract the specific slice of the signal
                id_st = int(time_range[0] * fs_to_use)
                id_end = int(time_range[1] * fs_to_use)
                signal_slice = signal_values[id_st:id_end]
                
                # Call the core function to get the plot and data
                fig, comod_data = _calculate_and_plot_comodulogram(
                    signal_slice, fs_to_use, channel_name, time_range_str, params
                )
                
                # Store results and figures
                results.setdefault(file_name, {}).setdefault(channel_name, {})[time_range_str] = comod_data.tolist()
                figures.setdefault(file_name, {}).setdefault(channel_name, {})[fig.layout.title.text] = fig

    return results, figures