import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import signal
from scipy.stats import sem
from src import utils


# ==============================================================================
# 1. HELPER FUNCTIONS (No changes needed here)
# ==============================================================================


def time_slicer_and_spectrogram(data, times, time_intervals, fs, spec_win, spec_nover, spec_stat, chann_name, spec_F_range, k_cax):
    s_sliced, t_sliced = np.array([]), np.array([])
    spectrogram_figs = []
    for i, interval in enumerate(time_intervals):
        start_time, end_time = interval[0], interval[1]
        id_st, id_end = int(start_time * fs), int(end_time * fs)
        if id_st < 0 or id_end <= id_st: continue
        id_st, id_end = max(0, id_st), min(len(data), id_end)
        s1_slice, t1_slice = data[id_st:id_end], times[id_st:id_end]
        s_sliced = np.concatenate((s_sliced, s1_slice)) if s_sliced.size else s1_slice
        t_sliced = np.concatenate((t_sliced, t1_slice)) if t_sliced.size else t1_slice
        
        if spec_stat:
            nfft = len(spec_win)
            f_spec, t_spec, Sxx = signal.spectrogram(s1_slice, fs, window=spec_win, noverlap=spec_nover, nfft=nfft)
            idx_range = np.where((f_spec >= spec_F_range[0]) & (f_spec <= spec_F_range[1]))[0]
            fig = go.Figure(data=go.Heatmap(z=10 * np.log10(Sxx[idx_range, :]), x=t_spec + start_time, y=f_spec[idx_range], colorscale='Jet', zmin=k_cax[0], zmax=k_cax[1], colorbar=dict(title='Power [dB/Hz]')))
            fig.update_layout(title=f'Spectrogram: {chann_name} | Slice: {start_time}-{end_time}s', yaxis_title='Frequency [Hz]', xaxis_title='Time [s]')
            spectrogram_figs.append(fig)
    return s_sliced, t_sliced, spectrogram_figs

def psd_welch(data, fs, window, noverlap, nfft):
    if len(data) < len(window):
        nfft, window, noverlap = 1024, signal.windows.hann(1024), 512
    f, Pxx = signal.welch(data, fs=fs, window=window, noverlap=noverlap, nfft=nfft)
    return Pxx, f

def calculate_band_power(psd, freqs, bands):
    band_means, band_errors = [], []
    for band in bands:
        idx_band = np.where((freqs >= band[0]) & (freqs <= band[1]))[0]
        mean_power = np.mean(psd[idx_band]) if idx_band.size > 0 else 0
        error = sem(psd[idx_band]) if idx_band.size > 1 else 0.0
        band_means.append(mean_power)
        band_errors.append(error)
    return np.array(band_means), np.array(band_errors)

# ==============================================================================
# 2. CORE CALCULATION ENGINE (Your original function)
# ==============================================================================
def psd_calc_python(data, norm_type, F_c, T1, F_h, spec_win_size, spec_noverlap, spec_F_range, k_cax, chann_name, fs, welch_params, spec_stat, filter_50hz=True):
    chann_name = utils.remove_invalid_chars(chann_name)
    signal_raw, times_raw = data['values'], data['times']
    
    if filter_50hz:
        signal_notched = utils.notch_filter_50hz(signal_raw, fs, F_h)
    else:
        signal_notched = signal_raw
        
    signal_normalized = (signal_notched - np.mean(signal_notched)) / np.std(signal_notched) if norm_type else signal_notched
    
    spec_win = signal.windows.hamming(spec_win_size)
    signal_sliced, times_sliced, spectrogram_figs = time_slicer_and_spectrogram(
        signal_normalized, times_raw, T1, fs, spec_win, spec_noverlap, spec_stat, chann_name, spec_F_range, k_cax
    )
    
    psd_values, freqs = psd_welch(signal_sliced, fs, welch_params['window'], welch_params['noverlap'], welch_params['nfft'])
    band_means, band_errors = calculate_band_power(psd_values, freqs, F_c)
    # --- Step 7: Plotting (MODIFIED TO CREATE 3 SEPARATE FIGURES) ---
        
    # Figure 1: Signal Plot
    fig_signal = go.Figure()
    fig_signal.add_trace(go.Scatter(x=times_sliced, y=signal_sliced, mode='lines'))
    fig_signal.update_layout(
        title=f'Signal: {chann_name}',
        xaxis_title='Time [s]',
        yaxis_title='Amplitude [mV]',
        height=350,
        margin=dict(t=50, b=10) # Adjust margin for a compact look
    )

    # Figure 2: PSD Plot
    fig_psd = go.Figure()
    fig_psd.add_trace(go.Scatter(x=freqs, y=psd_values, mode='lines'))
    fig_psd.update_layout(
        title=f'Power Spectrum: {chann_name}',
        xaxis_title='Frequency [Hz]',
        yaxis_title='Power [V^2/Hz]',
        height=350,
        margin=dict(t=50, b=10)
    )
    fig_psd.update_xaxes(range=[0, F_h])
    fig_psd.update_yaxes(type="log")

    # Figure 3: Bar Chart (No change to its creation)
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    fig_barchart = go.Figure(data=go.Bar(
        x=band_labels,
        y=band_means,
        error_y=dict(type='data', array=band_errors, visible=True)
    ))
    fig_barchart.update_layout(
        title=f'Band Power: {chann_name}',
        yaxis_title='Energy [mV^2/Hz]',
        xaxis_title='Frequency Band'
    )

    # --- Return Results AND 3 Separate Plotly Figures ---
    F_BP_PSD = {'means': band_means.tolist(), 'errors': band_errors.tolist()}

    # Update the return statement to include all three figures
    return F_BP_PSD, {'power': psd_values.tolist(), 'frequencies': freqs.tolist()}, spectrogram_figs, fig_signal, fig_psd, fig_barchart

# ==============================================================================
# 3. NEW MAIN ORCHESTRATOR FUNCTION
# ==============================================================================
import streamlit as st
def run_psd_analysis(selections, params, file_map, load_mat_file_func):
    """
    Main orchestrator that runs a separate PSD analysis for EACH configured time range.
    (Version with corrected parameter handling)
    """
    results = {}
    figures = {}

    # --- CREATE A CLEAN COPY OF PARAMS FOR THE FUNCTION CALL ---
    # This is the block you correctly identified as missing.
    params_for_function = params.copy()
    keys_to_remove = ['fs', 'desired_resolution', 'desired_freq_res', 'desired_time_res', 'SEM_state']
    for key in keys_to_remove:
        params_for_function.pop(key, None)
    # --- END OF CLEANING BLOCK ---

    for file_name, channels in selections.items():
        if not channels or 'pac_config' in file_name: continue
        
        results[file_name], figures[file_name] = {}, {}
        file_item = file_map.get(file_name)
        if not file_item: continue
        
        mat_contents = load_mat_file_func(file_item)
        
        if mat_contents is None: continue

        for channel_name, time_ranges in channels.items():
            if channel_name == 'pac_config' or not time_ranges: continue
            
            results[file_name][channel_name] = {}
            figures[file_name][channel_name] = {}

            # Loop for each individual time range
            for time_range in time_ranges:
                time_range_str = f"{time_range[0]}-{time_range[1]}s"
                channel_data = mat_contents[channel_name]
                
                signal_values = channel_data['values'].flatten()
                available_fields = channel_data.dtype.names if hasattr(channel_data, 'dtype') else channel_data.keys()
                
                if 'times' in available_fields:
                    time_vector = channel_data['times'].flatten()
                    duration = time_vector[-1] - time_vector[0]
                    fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
                else:
                    fs_to_use = params['fs']
                    time_vector = np.arange(len(signal_values)) / fs_to_use
                
                data_for_function = {'values': signal_values, 'times': time_vector}
                
                # Call the analysis function for this single time range
                band_power, full_psd, spec_figs, fig_sig, fig_psd, fig_bar = psd_calc_python(
                    data=data_for_function,
                    fs=fs_to_use,
                    T1=np.array([time_range]), # Pass only the current time range
                    chann_name=channel_name,
                    **params_for_function # Unpack the cleaned dictionary
                )
                
                # Store results and figures, organized by time range
                # Store the results and the newly separated figures
                results[file_name][channel_name][time_range_str] = {'band_power': band_power, 'full_psd': full_psd}
                
                psd_plot_name = f"Signal & PSD | {channel_name} ({time_range_str})"
                bar_plot_name = f"Band Power | {channel_name} ({time_range_str})"
                
                # Use descriptive names for all three main plots
                figures[file_name][channel_name][f"Signal | {channel_name} ({time_range_str})"] = fig_sig
                figures[file_name][channel_name][f"PSD | {channel_name} ({time_range_str})"] = fig_psd
                figures[file_name][channel_name][f"Band Power | {channel_name} ({time_range_str})"] = fig_bar
                
                for i, spec_fig in enumerate(spec_figs):
                    spec_plot_name = spec_fig.layout.title.text
                    figures[file_name][channel_name][spec_plot_name] = spec_fig

    return results, figures

# def run_psd_analysis(selections, params, file_map, load_mat_file_func):
#     """
#     Main orchestrator for running PSD analysis on all configured files and channels.
#     This function manages the loops and data prep, then calls psd_calc_python for each channel.
#     """
#     results = {}
#     figures = {}

#     for file_name, channels in selections.items():
#         if not channels or 'pac_config' in channels:
#             # If the entry is just for pac_config, create an empty dict and skip
#             if 'pac_config' in channels and len(channels) == 1:
#                 results[file_name], figures[file_name] = {}, {}
#                 continue
        
#         results[file_name], figures[file_name] = {}, {}
#         file_item = file_map.get(file_name)
#         if not file_item: continue
        
#         mat_contents = load_mat_file_func(file_item)
#         if mat_contents is None: continue

#         for channel_name, time_ranges in channels.items():
#             if channel_name == 'pac_config' or not time_ranges: continue
            
#             channel_data = mat_contents[channel_name]
#             signal_values = channel_data['values'].flatten()
#             available_fields = channel_data.dtype.names if hasattr(channel_data, 'dtype') else channel_data.keys()

#             if 'times' in available_fields:
#                 time_vector = channel_data['times'].flatten()
#                 duration = time_vector[-1] - time_vector[0]
#                 fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
#             else:
#                 fs_to_use = params['fs']
#                 time_vector = np.arange(len(signal_values)) / fs_to_use
            
#             data_for_function = {'values': signal_values, 'times': time_vector}
            
#             # Create a copy of the params to modify
#             params_for_function = params.copy()
            
#             # List of keys that are in 'params' but NOT arguments of psd_calc_python
#             keys_to_remove = ['fs', 'desired_resolution', 'desired_freq_res', 'desired_time_res','SEM_state']
            
#             # Remove the unnecessary keys before unpacking
#             for key in keys_to_remove:
#                 params_for_function.pop(key, None)

#             # Call the calculation engine with the cleaned dictionary
#             band_power, full_psd, spec_figs, fig_psd, fig_bar = psd_calc_python(
#                 data=data_for_function,
#                 fs=fs_to_use,
#                 T1=np.array(time_ranges),
#                 chann_name=channel_name,
#                 **params_for_function  # Unpack the cleaned dictionary
#             )
            
#             results[file_name][channel_name] = {'band_power': band_power, 'full_psd': full_psd}
#             figures[file_name][channel_name] = [fig_psd, fig_bar] + spec_figs

#     return results, figures

