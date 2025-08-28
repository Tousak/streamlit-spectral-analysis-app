# src/PAC.py

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import signal
from scipy.stats import sem
from src import utils
import matplotlib.pyplot as plt

# --- 1. REVISED PLOTTING FUNCTIONS (Using Matplotlib) ---

def create_pac_detail_plots_matplotlib(metrics, channel_name, time_slice_info):
    """
    Creates the detailed 2x3 plots using Matplotlib for performance.
    """
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(f"PAC Details for {channel_name} | {time_slice_info}", fontsize=16)

    # --- PLV ---
    ax1 = fig.add_subplot(2, 3, 1, projection='polar')
    ax1.plot([0, np.angle(metrics['plv_vector'])], [0, metrics['plv_scalar']], marker='o')
    ax1.set_title("Phase-Locking Value")
    ax1.set_yticklabels([]) # Hide radial labels

    ax4 = fig.add_subplot(2, 3, 4, projection='polar')
    ax4.hist(np.angle(metrics['plv_e']), bins=18)
    ax4.set_yticklabels([])

    # --- MVL ---
    ax2 = fig.add_subplot(2, 3, 2, projection='polar')
    ax2.plot([0, np.angle(metrics['mvl_vector'])], [0, metrics['mvl_scalar']], marker='o', color='r')
    ax2.set_title("Mean Vector Length")
    ax2.set_yticklabels([])

    ax5 = fig.add_subplot(2, 3, 5, projection='polar')
    ax5.plot(np.angle(metrics['mvl_e']), np.abs(metrics['mvl_e']), 'r.', markersize=4)
    ax5.set_yticklabels([])

    # --- MI ---
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.bar(np.rad2deg(metrics['phase_bins']), metrics['mean_amp_dist'], width=360/len(metrics['phase_bins']))
    ax3.set_title("Phase-Amplitude Dist.")
    ax3.set_xlabel("Phase (deg)")
    ax3.set_ylabel("Normalized Amplitude")
    ax3.set_xlim([-180, 180])

    ax6 = fig.add_subplot(2, 3, 6, projection='polar')
    ax6.bar(metrics['phase_bins'], metrics['mean_amp_dist'], width=2*np.pi/len(metrics['phase_bins']))
    ax6.set_yticklabels([])

    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust for suptitle
    return fig

def create_pac_summary_barchart_matplotlib(results, channel_name):
    """
    Creates a summary bar chart using Matplotlib.
    """
    time_slices = list(results.keys())
    if len(time_slices) < 2:
        return None

    plvs = [results[ts]['PLV'] for ts in time_slices]
    mvls = [results[ts]['MVL'] for ts in time_slices]
    mis = [results[ts]['MI'] for ts in time_slices]
    
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f'PAC Metric Comparison for {channel_name}', fontsize=16)

    axs[0].bar(time_slices, plvs)
    axs[0].set_title("PLV Across Time")
    axs[0].tick_params(axis='x', rotation=45)
    
    axs[1].bar(time_slices, mvls)
    axs[1].set_title("MVL Across Time")
    axs[1].tick_params(axis='x', rotation=45)

    axs[2].bar(time_slices, mis)
    axs[2].set_title("MI Across Time")
    axs[2].tick_params(axis='x', rotation=45)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig

# ==============================================================================
# 2. CORE PAC CALCULATION (Modified to return plot data)
# ==============================================================================

def calculate_pac_metrics(phase_data, amp_data, fs, n_bins):
    """
    Calculates PAC metrics and returns both scalar values and the vectors needed for plotting.
    """
    min_len = min(len(phase_data), len(amp_data))
    phase_data = phase_data[:min_len]
    amp_data = amp_data[:min_len]
    
    phase_series = np.angle(signal.hilbert(phase_data))
    amplitude_series = np.abs(signal.hilbert(amp_data))

    # --- Modulation Index (MI) ---
    bin_edges = np.linspace(-np.pi, np.pi, n_bins + 1)
    phase_bins_for_plot = (bin_edges[:-1] + bin_edges[1:]) / 2
    binned_phase = np.digitize(phase_series, bin_edges)
    mean_amp_by_bin = np.array([np.mean(amplitude_series[binned_phase == i]) for i in range(1, n_bins + 1)])
    mean_amp_by_bin = np.nan_to_num(mean_amp_by_bin, nan=1e-15)
    p_norm = mean_amp_by_bin / np.sum(mean_amp_by_bin)
    H = -np.sum(p_norm * np.log(p_norm + 1e-15))
    MI = (np.log(n_bins) - H) / np.log(n_bins)

    # --- Mean Vector Length (MVL) ---
    mvl_e = amplitude_series * np.exp(1j * phase_series) # Complex vector for plotting
    mvl_vector = np.mean(mvl_e)
    MVL = np.abs(mvl_vector)

    # --- Phase-Locking Value (PLV) ---
    amp_phase = np.angle(signal.hilbert(amplitude_series))
    phase_diff = phase_series - amp_phase
    plv_e = np.exp(1j * phase_diff) # Complex vector for plotting
    plv_vector = np.mean(plv_e)
    PLV = np.abs(plv_vector)
    
    # Package everything for return
    scalar_results = {'MI': MI, 'MVL': MVL, 'PLV': PLV}
    plotting_data = {
        'plv_scalar': PLV, 'plv_vector': plv_vector, 'plv_e': plv_e,
        'mvl_scalar': MVL, 'mvl_vector': mvl_vector, 'mvl_e': mvl_e,
        'phase_bins': phase_bins_for_plot, 'mean_amp_dist': p_norm
    }
    
    return scalar_results, plotting_data
def generate_sliding_windows(data, fs, window_duration_s, overlap_ratio):
    """
    A generator that yields slices of data for sliding window analysis.
    """
    window_size = int(window_duration_s * fs)
    overlap_samples = int(window_size * overlap_ratio)
    step_size = window_size - overlap_samples
    
    num_windows = (len(data) - overlap_samples) // step_size
    
    for i in range(num_windows):
        start_idx = i * step_size
        end_idx = start_idx + window_size
        yield data[start_idx:end_idx]

def create_sliding_pac_plot(results, channel_name, time_range, pac_params):
    """
    Creates a 3-subplot figure with the x-axis visible on all plots.
    """
    if not results or not all(k in results for k in ['MI', 'MVL', 'PLV']):
        return None
    
    num_windows = len(results['MI'])
    window_duration_s = pac_params['sliding_window_duration_s']
    overlap_ratio = pac_params['overlap_sliding']
    
    # Calculate the correct time axis
    step_size_s = window_duration_s * (1 - overlap_ratio)
    start_time = time_range[0] + (window_duration_s / 2)
    end_time = start_time + (num_windows - 1) * step_size_s
    time_axis = np.linspace(start_time, end_time, num_windows)
    
    # --- PLOTTING (MODIFIED) ---
    # Remove sharex=True from the subplots call
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    time_slice_info = f"{time_range[0]}-{time_range[1]}s"
    fig.suptitle(f'Sliding Window PAC for {channel_name} | {time_slice_info}', fontsize=16)

    # Plot MI
    axs[0].plot(time_axis, results['MI'])
    axs[0].set_title("Modulation Index (MI)")
    axs[0].set_ylabel("MI")
    axs[0].grid(True)

    # Plot MVL
    axs[1].plot(time_axis, results['MVL'])
    axs[1].set_title("Mean Vector Length (MVL)")
    axs[1].set_ylabel("MVL")
    axs[1].grid(True)

    # Plot PLV
    axs[2].plot(time_axis, results['PLV'])
    axs[2].set_title("Phase-Locking Value (PLV)")
    axs[2].set_ylabel("PLV")
    axs[2].set_xlabel("Time [s]")
    axs[2].grid(True)

    # --- ADD THIS LOOP TO ENABLE ALL X-AXES ---
    # Explicitly turn on the tick labels for all subplots
    for ax in axs:
        ax.tick_params(axis='x', labelbottom=True)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig
# ==============================================================================
# 3. MAIN ORCHESTRATOR FUNCTION (Modified to create plots)
# ==============================================================================

def run_pac_analysis(selections, pac_params, file_map, load_mat_file_func):
    """
    Main function with corrected figure dictionary handling.
    """
    results = {}
    figures = {}

    fs_to_use = pac_params.get('fs', 2000) # Use fs from params, default to 2000
    F_h = pac_params.get('F_h', 200)
    # --- A. WITHIN-CHANNEL PAC ---
    if not pac_params['use_cross_channel']:
        for file_name, file_selections in selections.items():
            if file_name == 'pac_config': continue
            
            mat_contents = load_mat_file_func(file_map[file_name])
            if not mat_contents: continue
            
            results[file_name], figures[file_name] = {}, {}
            
            for channel_name, time_ranges in file_selections.items():
                if channel_name == 'pac_config' or not time_ranges: continue
                
                # --- CHANGE HERE: Initialize as a dictionary ---
                figures[file_name][channel_name] = {}
                
                signal_data_full = mat_contents[channel_name]['values'].flatten()
                signal_data_full = utils.notch_filter_50hz(signal_data_full, fs_to_use, F_h)
                results_per_slice = {}
                
                for time_range in time_ranges:
                    slice_info = f"{time_range[0]}-{time_range[1]}s"
                    id_st = int(time_range[0] * fs_to_use)
                    id_end = int(time_range[1] * fs_to_use)
                    signal_slice = signal_data_full[id_st:id_end]
                    
                    for phase_band in pac_params['phase_freq_bands']:
                        for amp_band in pac_params['amp_freq_bands']:
                            band_info = f"Phase_{phase_band[0]}-{phase_band[1]}_Amp_{amp_band[0]}-{amp_band[1]}"
                            
                            b_phase, a_phase = signal.butter(4, phase_band, btype='bandpass', fs=fs_to_use)
                            phase_filtered = signal.filtfilt(b_phase, a_phase, signal_slice)
                            
                            b_amp, a_amp = signal.butter(4, amp_band, btype='bandpass', fs=fs_to_use)
                            amp_filtered = signal.filtfilt(b_amp, a_amp, signal_slice)

                            scalar_results, plot_data = calculate_pac_metrics(phase_filtered, amp_filtered, fs_to_use, pac_params['n_bins'])
                            
                            results[file_name].setdefault(channel_name, {}).setdefault(band_info, {})[slice_info] = scalar_results
                            results_per_slice[slice_info] = scalar_results

                            # --- CHANGE HERE: Store in dictionary with a descriptive key ---
                            fig_key = f"Detail Plot | {slice_info} | {band_info}"
                            detail_fig = create_pac_detail_plots_matplotlib(plot_data, channel_name, f"{slice_info} | {band_info}")
                            figures[file_name][channel_name][fig_key] = detail_fig
                            
                            # --- SLIDING WINDOW PAC CALCULATION ---
                            if pac_params['slide_state']:
                                sliding_results = {'MI': [], 'MVL': [], 'PLV': []}
                                
                                phase_windows = generate_sliding_windows(phase_filtered, fs_to_use, pac_params['sliding_window_duration_s'], pac_params['overlap_sliding'])
                                amp_windows = generate_sliding_windows(amp_filtered, fs_to_use, pac_params['sliding_window_duration_s'], pac_params['overlap_sliding'])
                                
                                for phase_win, amp_win in zip(phase_windows, amp_windows):
                                    s_res, _ = calculate_pac_metrics(phase_win, amp_win, fs_to_use, pac_params['n_bins'])
                                    sliding_results['MI'].append(s_res['MI'])
                                    sliding_results['MVL'].append(s_res['MVL'])
                                    sliding_results['PLV'].append(s_res['PLV'])
                                
                                results[file_name][channel_name][band_info][f"{slice_info}_sliding"] = sliding_results
                                
                                # --- CHANGE HERE: Store in dictionary with a descriptive key ---
                                sliding_fig_key = f"Sliding PAC | {slice_info} | {band_info}"
                                sliding_fig = create_sliding_pac_plot(
                                    sliding_results, 
                                    channel_name, 
                                    time_range, # Pass the current time_range
                                    pac_params  # Pass the pac_params
                                )
                                if sliding_fig:
                                    figures[file_name][channel_name][sliding_fig_key] = sliding_fig

                # Create the summary bar chart
                if len(time_ranges) > 1:
                    summary_fig_key = f"Summary Chart | {channel_name}"
                    summary_fig = create_pac_summary_barchart_matplotlib(results_per_slice, channel_name)
                    if summary_fig:
                        figures[file_name][channel_name][summary_fig_key] = summary_fig
    # --- B. BETWEEN-CHANNELS PAC (CORRECTED LOGIC) ---
    else:
        for file_name, pairs in pac_params['channel_pairs'].items():
            if file_name not in selections: continue
            
            mat_contents = load_mat_file_func(file_map[file_name])
            if not mat_contents: continue

            results[file_name], figures[file_name] = {}, {}

            for phase_ch, amp_ch in pairs.items():
                time_ranges = selections[file_name].get(phase_ch, [])
                if not time_ranges: continue

                phase_data_full = mat_contents[phase_ch]['values'].flatten()
                amp_data_full = mat_contents[amp_ch]['values'].flatten()
                
                # --- ADD THIS BLOCK TO DETERMINE fs_to_use for the pair ---
                # We use the phase channel as the reference for fs
                phase_channel_data = mat_contents[phase_ch]
                available_fields = phase_channel_data.dtype.names if hasattr(phase_channel_data, 'dtype') else phase_channel_data.keys()
                
                if 'times' in available_fields:
                    time_vector = phase_channel_data['times'].flatten()
                    duration = time_vector[-1] - time_vector[0]
                    fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else pac_params.get('fs', 2000)
                else:
                    fs_to_use = pac_params.get('fs', 2000)
                # --- END OF ADDED BLOCK ---

                results_per_slice = {}
                for time_range in time_ranges:
                    id_st = int(time_range[0] * fs_to_use) # Now uses the correct fs
                    id_end = int(time_range[1] * fs_to_use) # Now uses the correct fs
                    
                    phase_slice = phase_data_full[id_st:id_end]
                    amp_slice = amp_data_full[id_st:id_end]

                    for phase_band in pac_params['phase_freq_bands']:
                        for amp_band in pac_params['amp_freq_bands']:
                            b_phase, a_phase = signal.butter(4, phase_band, btype='bandpass', fs=fs_to_use)
                            phase_filtered = signal.filtfilt(b_phase, a_phase, phase_slice)
                            
                            b_amp, a_amp = signal.butter(4, amp_band, btype='bandpass', fs=fs_to_use)
                            amp_filtered = signal.filtfilt(b_amp, a_amp, amp_slice)

                            scalar_results, plot_data = calculate_pac_metrics(phase_filtered, amp_filtered, fs_to_use, pac_params['n_bins'])
                            
                            slice_info = f"{time_range[0]}-{time_range[1]}s"
                            pair_name = f"Phase({utils.extract_short_name(phase_ch)})_Amp({utils.extract_short_name(amp_ch)})"
                            band_info = f"Bands_{phase_band[0]}-{phase_band[1]}_{amp_band[0]}-{amp_band[1]}"
                            
                            results[file_name].setdefault(pair_name, {}).setdefault(band_info, {})[slice_info] = scalar_results
                            results_per_slice[slice_info] = scalar_results
                            # --- CHANGE HERE: Store in dictionary with a descriptive key ---
                            fig_key = f"Detail Plot | {pair_name} | {slice_info} | {band_info}"
                            detail_fig = create_pac_detail_plots_matplotlib(plot_data, pair_name, f"{slice_info} | {band_info}")
                            figures[file_name].setdefault(pair_name, {})[fig_key] = detail_fig

                if len(time_ranges) > 1:
                    summary_fig_key = f"Summary Chart | {pair_name}"
                    summary_fig = create_pac_summary_barchart_matplotlib(results_per_slice, pair_name)
                    if summary_fig:
                        figures[file_name][pair_name][summary_fig_key] = summary_fig

    return results, figures