import numpy as np
from scipy.stats import sem
def _clean_nans(value):
    """Recursively replace NaN with None for JSON compatibility."""
    if isinstance(value, dict):
        return {k: _clean_nans(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_nans(v) for v in value]
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, np.ndarray):
        return _clean_nans(value.tolist())
    return value

def _aggregate_and_calculate(data_list):
    """Helper to calculate mean and SEM, handling single-item lists correctly."""
    if not data_list:
        return {'mean': None, 'sem': None}
    
    # If only one item, mean is the item itself, and SEM is 0
    if len(data_list) == 1:
        return {'mean': data_list[0], 'sem': 0.0}
    
def _process_pac_results(pac_data):
    """
    Calculates a Grand Mean and SEM and returns them, handling the case of no data.
    """
    all_mis, all_mvls, all_plvs = [], [], []

    # ... (your existing loop to collect all the values is correct) ...
    for file_name, channels in pac_data.items():
        if not isinstance(channels, dict): continue
        for channel_name, bands in channels.items():
            if not isinstance(bands, dict): continue
            for band_info, time_slices in bands.items():
                if not isinstance(time_slices, dict): continue
                for time_slice, values in time_slices.items():
                    if isinstance(values, dict):
                        if 'MI' in values and values['MI'] is not None:
                            all_mis.append(values['MI'])
                        if 'MVL' in values and values['MVL'] is not None:
                            all_mvls.append(values['MVL'])
                        if 'PLV' in values and values['PLV'] is not None:
                            all_plvs.append(values['PLV'])

    if all_mis:
        # --- CHANGE IS HERE ---
        # Use np.nanmean to safely ignore any NaN values
        grand_mean = {
            'MI': np.nanmean(all_mis),
            'MVL': np.nanmean(all_mvls),
            'PLV': np.nanmean(all_plvs)
        }
        # --- END CHANGE ---
        
        grand_sem = {
            'MI': sem(all_mis, nan_policy='omit'),
            'MVL': sem(all_mvls, nan_policy='omit'),
            'PLV': sem(all_plvs, nan_policy='omit')
        }
        return grand_mean, grand_sem
    else:
        return None, None

def _process_psd_results(psd_data):
    """Calculates and adds hierarchical means and SEM for PSD data in-place."""
    all_file_means_and_sems = []

    for file_name, channels in psd_data.items():
        if not isinstance(channels, dict): continue

        all_channel_means_and_sems = []
        for channel_name, time_slices in channels.items():
            if not isinstance(time_slices, dict): continue

            # Level 1: Mean & SEM across Time Ranges
            means_list, errors_list = [], []
            for time_slice, values in time_slices.items():
                if isinstance(values, dict) and 'band_power' in values:
                    means_list.append(values['band_power']['means'])
                    errors_list.append(values['band_power']['errors'])
            
            if means_list:
                mean_across_time = np.mean(means_list, axis=0)
                # Propagate the error for the mean of means
                sem_across_time = np.sqrt(np.sum(np.square(errors_list), axis=0)) / len(errors_list)
                
                channels[channel_name]['mean_across_time'] = {'means': mean_across_time.tolist(), 'errors': sem_across_time.tolist()}
                all_channel_means_and_sems.append({'mean': mean_across_time, 'sem': sem_across_time})

        # Level 2: Mean & SEM across Channels
        if all_channel_means_and_sems:
            # Calculate mean and SEM from the collected means/sems of the channels
            mean_across_channels = np.mean([d['mean'] for d in all_channel_means_and_sems], axis=0)
            sem_across_channels = np.sqrt(np.sum(np.square([d['sem'] for d in all_channel_means_and_sems]), axis=0)) / len(all_channel_means_and_sems)
            
            psd_data[file_name]['mean_across_channels'] = {'means': mean_across_channels.tolist(), 'errors': sem_across_channels.tolist()}
            all_file_means_and_sems.append({'mean': mean_across_channels, 'sem': sem_across_channels})

    # Level 3: Grand Mean & SEM across all files
    if all_file_means_and_sems:
        grand_mean = np.mean([d['mean'] for d in all_file_means_and_sems], axis=0)
        grand_sem = np.sqrt(np.sum(np.square([d['sem'] for d in all_file_means_and_sems]), axis=0)) / len(all_file_means_and_sems)
        
        psd_data['grand_mean'] = {'means': grand_mean.tolist(), 'errors': grand_sem.tolist()}

# --- NEW FUNCTION FOR COHERENCE RESULTS ---
def _process_coh_results(coh_data):
    """Calculates and adds hierarchical means and SEM for coherence data in-place."""
    all_file_means_and_sems = []

    for file_name, pairs in coh_data.items():
        if not isinstance(pairs, dict): continue

        all_pair_means_and_sems = []
        for pair_name, time_slices in pairs.items():
            if not isinstance(time_slices, dict): continue

            means_list, errors_list = [], []
            for time_slice, values in time_slices.items():
                if isinstance(values, dict) and 'band_coherence' in values:
                    means_list.append(values['band_coherence']['means'])
                    errors_list.append(values['band_coherence']['errors'])
            
            if means_list:
                mean_across_time = np.mean(means_list, axis=0)
                sem_across_time = np.sqrt(np.sum(np.square(errors_list), axis=0)) / len(errors_list)
                pairs[pair_name]['mean_across_time'] = {'means': mean_across_time, 'errors': sem_across_time}
                all_pair_means_and_sems.append({'mean': mean_across_time, 'sem': sem_across_time})

        if all_pair_means_and_sems:
            mean_across_pairs = np.mean([d['mean'] for d in all_pair_means_and_sems], axis=0)
            sem_across_pairs = np.sqrt(np.sum(np.square([d['sem'] for d in all_pair_means_and_sems]), axis=0)) / len(all_pair_means_and_sems)
            coh_data[file_name]['mean_across_pairs'] = {'means': mean_across_pairs, 'errors': sem_across_pairs}
            all_file_means_and_sems.append({'mean': mean_across_pairs, 'sem': sem_across_pairs})

    if all_file_means_and_sems:
        grand_mean = np.mean([d['mean'] for d in all_file_means_and_sems], axis=0)
        grand_sem = np.sqrt(np.sum(np.square([d['sem'] for d in all_file_means_and_sems]), axis=0)) / len(all_file_means_and_sems)
        coh_data['grand_mean'] = {'means': grand_mean, 'errors': grand_sem}

import streamlit as st
def calculate_hierarchical_means(all_results):
    """Main orchestrator to calculate means and SEM for all analysis types."""
    if 'pac_results' in all_results:
        # --- CHANGE IS HERE ---
        # Capture the returned values
        mean, sem = _process_pac_results(all_results['pac_results'])
        
        # Add them to the dictionary here
        if mean and sem:
            all_results['pac_results']['grand_mean'] = mean
            all_results['pac_results']['grand_sem'] = sem

    if 'psd_results' in all_results:
        _process_psd_results(all_results['psd_results'])
    if 'coh_results' in all_results:
        _process_coh_results(all_results['coh_results'])
    
    return _clean_nans(all_results)