# src/Comodulogram.py

import numpy as np
import matplotlib.pyplot as plt # Import Matplotlib
from scipy import signal
from src import utils
from pactools import Comodulogram # Import the Comodulogram class
import streamlit as st # Import Streamlit

# ==============================================================================
# 2. CORE CALCULATION ENGINE (Rewritten with pactools)
# ==============================================================================

def _calculate_and_plot_comodulogram(phase_signal, amp_signal, fs, plot_title, params):
    """
    Core function to calculate and plot a smooth comodulogram using pactools for 
    calculation and Matplotlib's contourf for plotting.
    Supports both within-channel (phase_signal == amp_signal) and cross-channel PAC.
    """
    # --- Ensure start frequencies are always positive ---
    phase_start = params.get('phase_vec_start', 0.1)
    if phase_start <= 0:
        phase_start = 0.1 
        
    amp_start = params.get('amp_vec_start', 0.1)
    if amp_start <= 0:
        amp_start = 0.1
    # --- END FIX ---

    # --- 1. Define frequency ranges for the analysis ---
    # Fix: Include the end frequency in the range
    low_fq_range = np.arange(
        phase_start, 
        params['phase_vec_end'] + params['phase_vec_dt'], 
        params['phase_vec_dt']
    )
    high_fq_range = np.arange(
        amp_start, 
        params['amp_vec_end'] + params['amp_vec_dt'], 
        params['amp_vec_dt']
    )
    
    # --- 2. Instantiate and run the Comodulogram estimator ---
    estimator = Comodulogram(
        fs=fs,
        low_fq_range=low_fq_range,
        high_fq_range=high_fq_range,
        low_fq_width=params['phase_vec_dt'] * 2.0,
        method='tort',
        progress_bar=False
    )
    
    # pactools.Comodulogram.fit(sig, sig_driver=None)
    # sig: signal for amplitude extraction
    # sig_driver: signal for phase extraction (if None, uses sig)
    estimator.fit(amp_signal, phase_signal)
    comodulogram = estimator.comod_
    
    # --- 3. COLOR SCALING using absolute min/max ---
    if comodulogram.size > 0:
        vmin = np.nanmin(comodulogram)
        vmax = np.nanmax(comodulogram)
        if np.isclose(vmin, vmax):
            vmax = vmin + 1e-9 # Failsafe for flat data
    else:
        vmin, vmax = 0, 1
    
    # --- 4. PLOTTING (Using contourf for a smooth plot) ---
    fig, ax = plt.subplots(figsize=(10, 8))
    
    levels = 40 # Number of contour levels for a smooth gradient
    
    contour = ax.contourf(
        low_fq_range, 
        high_fq_range, 
        comodulogram.T, # Transpose to match (Y, X) => (Amp, Phase) for matplotlib
        levels=levels, 
        cmap='jet', 
        vmin=vmin, 
        vmax=vmax
    )
    
    fig.colorbar(contour, ax=ax, label='Modulation Index')
    ax.set_title(plot_title)
    ax.set_xlabel('Phase Frequency (Hz)')
    ax.set_ylabel('Amplitude Frequency (Hz)')
    
    fig.tight_layout()

    return fig, comodulogram

# ==============================================================================
# 3. MAIN ORCHESTRATOR FUNCTION (Updated for efficiency)
# ==============================================================================

def run_comodulogram_analysis(selections, params, file_map, load_mat_file_func):
    """
    Main orchestrator for running Comodulogram analysis on all configured time ranges.
    """
    results = {}
    figures = {}

    # --- A. WITHIN-CHANNEL COMODULOGRAM ---
    if not params.get('use_cross_channel', False):
        for file_name, channels in selections.items():
            if not channels or 'pac_config' in file_name: continue
            
            file_item = file_map.get(file_name)
            if not file_item: continue
            
            mat_contents = load_mat_file_func(file_item)
            if mat_contents is None: continue

            # Initialize file dictionary
            results[file_name] = {}
            figures[file_name] = {}

            for channel_name, time_ranges in channels.items():
                if channel_name == 'pac_config' or not time_ranges: continue
                
                channel_data = mat_contents[channel_name]
                # Initialize channel dictionary
                figures[file_name][channel_name] = {}

                available_fields = channel_data.dtype.names if hasattr(channel_data, 'dtype') else channel_data.keys()

                if 'times' in available_fields:
                    time_vector = channel_data['times'].flatten()
                    duration = time_vector[-1] - time_vector[0]
                    fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
                else:
                    fs_to_use = params['fs']
                
                signal_values = channel_data['values'].flatten()
                # Apply notch filter once per channel for efficiency
                if params.get('filter_50hz', True):
                    signal_values = utils.notch_filter_50hz(signal_values, fs_to_use, params['F_h'])

                for time_range in time_ranges:
                    time_range_str = f"{time_range[0]}-{time_range[1]}s"
                    
                    id_st = int(time_range[0] * fs_to_use)
                    id_end = int(time_range[1] * fs_to_use)
                    signal_slice = signal_values[id_st:id_end]
                    
                    plot_title = f'Comodulogram: {channel_name} ({time_range_str})'
                    fig, comod_data = _calculate_and_plot_comodulogram(
                        signal_slice, signal_slice, fs_to_use, plot_title, params
                    )
                    
                    results.setdefault(file_name, {}).setdefault(channel_name, {})[time_range_str] = comod_data.tolist()
                    figures[file_name][channel_name][plot_title] = fig
    
    # --- B. CROSS-CHANNEL COMODULOGRAM ---
    else:
        for file_name, pairs in params.get('channel_pairs', {}).items():
            if file_name not in selections: continue
            
            file_item = file_map.get(file_name)
            if not file_item: continue
            
            mat_contents = load_mat_file_func(file_item)
            if mat_contents is None: continue
            
            # Initialize dictionaries
            if file_name not in results: results[file_name] = {}
            if file_name not in figures: figures[file_name] = {}

            for phase_ch, amp_ch in pairs.items():
                time_ranges = selections[file_name].get(phase_ch, [])
                if not time_ranges: continue
                
                pair_name = f"Phase({utils.extract_short_name(phase_ch)})_Amp({utils.extract_short_name(amp_ch)})"
                
                phase_data_full = mat_contents[phase_ch]['values'].flatten()
                amp_data_full = mat_contents[amp_ch]['values'].flatten()

                # Determine fs using phase channel
                phase_channel_data = mat_contents[phase_ch]
                available_fields = phase_channel_data.dtype.names if hasattr(phase_channel_data, 'dtype') else phase_channel_data.keys()
                
                if 'times' in available_fields:
                    time_vector = phase_channel_data['times'].flatten()
                    duration = time_vector[-1] - time_vector[0]
                    fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
                else:
                    fs_to_use = params['fs']
                
                if params.get('filter_50hz', True):
                    phase_data_full = utils.notch_filter_50hz(phase_data_full, fs_to_use, params['F_h'])
                    amp_data_full = utils.notch_filter_50hz(amp_data_full, fs_to_use, params['F_h'])
                
                for time_range in time_ranges:
                    time_range_str = f"{time_range[0]}-{time_range[1]}s"
                    id_st = int(time_range[0] * fs_to_use)
                    id_end = int(time_range[1] * fs_to_use)
                    
                    phase_slice = phase_data_full[id_st:id_end]
                    amp_slice = amp_data_full[id_st:id_end]
                    
                    plot_title = f'Comodulogram: {pair_name} ({time_range_str})'
                    fig, comod_data = _calculate_and_plot_comodulogram(
                        phase_slice, amp_slice, fs_to_use, plot_title, params
                    )
                    
                    results.setdefault(file_name, {}).setdefault(pair_name, {})[time_range_str] = comod_data.tolist()
                    figures.setdefault(file_name, {}).setdefault(pair_name, {})[plot_title] = fig

    return results, figures
