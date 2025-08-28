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

def _calculate_and_plot_comodulogram(data_slice, fs, chann_name, time_range_str, params):
    """
    Core function to calculate and plot a smooth comodulogram using pactools for 
    calculation and Matplotlib's contourf for plotting.
    """
    chann_name = utils.remove_invalid_chars(chann_name)
    
    # --- Ensure start frequencies are always positive ---
    phase_start = params.get('phase_vec_start', 0.1)
    if phase_start <= 0:
        phase_start = 0.1 
        
    amp_start = params.get('amp_vec_start', 0.1)
    if amp_start <= 0:
        amp_start = 0.1
    # --- END FIX ---

    # --- 1. Define frequency ranges for the analysis ---
    low_fq_range = np.arange(
        phase_start, 
        params['phase_vec_end'], 
        params['phase_vec_dt']
    )
    high_fq_range = np.arange(
        amp_start, 
        params['amp_vec_end'], 
        params['amp_vec_dt']
    )
    
    # The notch filter is now applied in the orchestrator function before this is called
    lfp = data_slice

    # --- 2. Instantiate and run the Comodulogram estimator ---
    estimator = Comodulogram(
        fs=fs,
        low_fq_range=low_fq_range,
        high_fq_range=high_fq_range,
        low_fq_width=params['phase_vec_dt'] * 2.0,
        method='tort',
        progress_bar=False
    )
    estimator.fit(lfp)
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
        comodulogram, 
        levels=levels, 
        cmap='jet', 
        vmin=vmin, 
        vmax=vmax
    )
    
    fig.colorbar(contour, ax=ax, label='Modulation Index')
    ax.set_title(f'Comodulogram: {chann_name} ({time_range_str})')
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

    for file_name, channels in selections.items():
        if not channels or 'pac_config' in file_name: continue
        
        file_item = file_map.get(file_name)
        if not file_item: continue
        
        mat_contents = load_mat_file_func(file_item)
        if mat_contents is None: continue

        for channel_name, time_ranges in channels.items():
            if channel_name == 'pac_config' or not time_ranges: continue
            
            channel_data = mat_contents[channel_name]

            available_fields = channel_data.dtype.names if hasattr(channel_data, 'dtype') else channel_data.keys()

            if 'times' in available_fields:
                time_vector = channel_data['times'].flatten()
                duration = time_vector[-1] - time_vector[0]
                fs_to_use = round((len(time_vector) - 1) / duration) if duration > 0 else params['fs']
            else:
                fs_to_use = params['fs']
            
            signal_values = channel_data['values'].flatten()
            # Apply notch filter once per channel for efficiency
            signal_values = utils.notch_filter_50hz(signal_values, fs_to_use, params['F_h'])

            for time_range in time_ranges:
                time_range_str = f"{time_range[0]}-{time_range[1]}s"
                
                id_st = int(time_range[0] * fs_to_use)
                id_end = int(time_range[1] * fs_to_use)
                signal_slice = signal_values[id_st:id_end]
                
                fig, comod_data = _calculate_and_plot_comodulogram(
                    signal_slice, fs_to_use, channel_name, time_range_str, params
                )
                
                results.setdefault(file_name, {}).setdefault(channel_name, {})[time_range_str] = comod_data.tolist()
                figures.setdefault(file_name, {}).setdefault(channel_name, {})[fig.get_axes()[0].get_title()] = fig

    return results, figures
