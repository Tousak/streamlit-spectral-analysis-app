import numpy as np
import re
from scipy.stats import sem

# A list of keys that are added during the hierarchical mean calculations.
# These keys have a different data structure and should be skipped by the processing functions.
AGGREGATION_KEYS = ['mean_across_time', 'mean_across_channels', 'mean_across_pairs', 'grand_mean', 'grand_sem']

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
    
    if len(data_list) == 1:
        return {'mean': data_list[0], 'sem': 0.0}
    
def _process_pac_results(pac_data):
    """
    Calculates and adds hierarchical means and SEM for PAC data (MI, MVL, PLV).
    Mimics the structure of _process_psd_results.
    """
    # This will store the mean of each file, to be used for the grand mean calculation.
    # Structure: {band_info: [{'mean': file_mean, 'sem': file_sem}, ...]}
    all_files_means_by_band = {}

    for file_name, channels in pac_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict):
            continue

        # This will store the mean of each channel for the current file.
        # Structure: {band_info: [{'mean': channel_mean, 'sem': channel_sem}, ...]}
        all_channels_means_by_band = {}

        for channel_name, bands in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(bands, dict):
                continue

            for band_info, time_slices in bands.items():
                if band_info in AGGREGATION_KEYS or not isinstance(time_slices, dict):
                    continue

                # --- 1. Calculate Mean Across Time Ranges ---
                # Gather all scalar results for the current band across its time slices
                metrics_across_time = [
                    ts_data for ts, ts_data in time_slices.items() 
                    if ts not in AGGREGATION_KEYS and not ts.endswith('_sliding')
                ]
                
                if metrics_across_time:
                    # Convert list of dicts to dict of lists
                    metrics_dict = {k: [dic[k] for dic in metrics_across_time] for k in metrics_across_time[0]}

                    # Calculate mean
                    mean_across_time = {k: np.mean(v) for k, v in metrics_dict.items()}
                    
                    # Calculate SEM
                    if len(metrics_across_time) > 1:
                        sem_across_time = {k: sem(v, nan_policy='omit') for k, v in metrics_dict.items()}
                    else:
                        sem_across_time = {k: 0.0 for k in metrics_dict.keys()}
                    
                    # Add to the results dictionary
                    bands[band_info]['mean_across_time'] = {'means': mean_across_time, 'sems': sem_across_time}

                    # Store for next level of aggregation (mean across channels)
                    all_channels_means_by_band.setdefault(band_info, []).append({'mean': mean_across_time, 'sem': sem_across_time})

        # --- 2. Calculate Mean Across Channels ---
        for band_info, channel_means_list in all_channels_means_by_band.items():
            if len(channel_means_list) > 0:
                # List of mean dicts for the current band
                means_to_avg = [item['mean'] for item in channel_means_list]
                # Convert list of dicts to dict of lists
                metrics_dict = {k: [dic[k] for dic in means_to_avg] for k in means_to_avg[0]}

                # Calculate mean
                mean_across_channels = {k: np.mean(v) for k, v in metrics_dict.items()}

                # Calculate SEM
                if len(means_to_avg) > 1:
                    sem_across_channels = {k: sem(v, nan_policy='omit') for k, v in metrics_dict.items()}
                else:
                    sem_across_channels = {k: 0.0 for k in metrics_dict.keys()}

                # Add to the results dictionary
                pac_data[file_name].setdefault('mean_across_channels', {})[band_info] = {'means': mean_across_channels, 'sems': sem_across_channels}

                # Store for next level of aggregation (grand mean)
                all_files_means_by_band.setdefault(band_info, []).append({'mean': mean_across_channels, 'sem': sem_across_channels})

    # --- 3. Calculate Grand Mean (Mean Across Files) ---
    for band_info, file_means_list in all_files_means_by_band.items():
        if len(file_means_list) > 0:
            # List of mean dicts for the current band
            means_to_avg = [item['mean'] for item in file_means_list]
            # Convert list of dicts to dict of lists
            metrics_dict = {k: [dic[k] for dic in means_to_avg] for k in means_to_avg[0]}

            # Calculate mean
            grand_mean = {k: np.mean(v) for k, v in metrics_dict.items()}

            # Calculate SEM
            if len(means_to_avg) > 1:
                grand_sem = {k: sem(v, nan_policy='omit') for k, v in metrics_dict.items()}
            else:
                # If only one file, the grand SEM is the SEM from that file's channels
                grand_sem = file_means_list[0]['sem']

            # Add to the results dictionary
            pac_data.setdefault('grand_mean', {})[band_info] = {'means': grand_mean, 'sems': grand_sem}

def _process_psd_results(psd_data):
    """
    Calculates and adds hierarchical means and SEM for both band power and full PSD data,
    using time range durations as weights for averaging.
    """
    all_file_band_means_sems = []
    all_file_full_psd_means_sems = []
    frequencies = None

    for file_name, channels in psd_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict):
            continue

        all_channel_band_means_sems = []
        all_channel_full_psd_means_sems = []
        for channel_name, time_slices in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(time_slices, dict):
                continue

            band_means_list, band_errors_list = [], []
            full_psd_powers = []
            durations = [] # Store durations for weighted averaging
            
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS:
                    continue
                
                # Extract duration from time_slice string (e.g., "0-10s" -> 10)
                match = re.match(r'(\d+\.?\d*)-(\d+\.?\d*)s', time_slice)
                if match:
                    start_time = float(match.group(1))
                    end_time = float(match.group(2))
                    duration = end_time - start_time
                    durations.append(duration)
                else:
                    # Default to a weight of 1 if duration cannot be parsed
                    durations.append(1.0)

                if isinstance(values, dict):
                    if 'band_power' in values:
                        band_means_list.append(values['band_power']['means'])
                        band_errors_list.append(values['band_power']['errors'])
                    
                    if 'full_psd' in values and 'power' in values['full_psd']:
                        full_psd_powers.append(values['full_psd']['power'])
                        if frequencies is None:
                            frequencies = values['full_psd']['frequencies']
            
            if band_means_list:
                band_means_array = np.array(band_means_list)
                full_psd_powers_array = np.array(full_psd_powers)
                durations_array = np.array(durations)

                # Calculate weighted means across time ranges
                mean_band_across_time = np.average(band_means_array, axis=0, weights=durations_array)
                mean_psd_across_time = np.average(full_psd_powers_array, axis=0, weights=durations_array)
                
                # SEM calculation remains unweighted for now, as weighted SEM is more complex
                sem_band_across_time = np.sqrt(np.sum(np.square(band_errors_list), axis=0)) / len(band_errors_list) if len(band_errors_list) > 0 else np.zeros_like(mean_band_across_time)
                sem_psd_across_time = sem(full_psd_powers_array, axis=0, nan_policy='omit') if len(full_psd_powers_array) > 1 else np.zeros_like(mean_psd_across_time)

                channels[channel_name]['mean_across_time'] = {
                    'band_power': {'means': mean_band_across_time.tolist(), 'errors': sem_band_across_time.tolist()},
                    'full_psd': {'mean_power': mean_psd_across_time.tolist(), 'sem_power': sem_psd_across_time.tolist(), 'frequencies': frequencies}
                }
                all_channel_band_means_sems.append({'mean': mean_band_across_time, 'sem': sem_band_across_time, 'weight': np.sum(durations_array)})
                all_channel_full_psd_means_sems.append({'mean': mean_psd_across_time, 'sem': sem_psd_across_time, 'weight': np.sum(durations_array)})

        if all_channel_band_means_sems:
            # Extract means, SEMs, and weights for channel-wise averaging
            channel_means_band = np.array([d['mean'] for d in all_channel_band_means_sems])
            channel_sems_band = np.array([d['sem'] for d in all_channel_band_means_sems])
            channel_weights = np.array([d['weight'] for d in all_channel_band_means_sems])

            channel_means_psd = np.array([d['mean'] for d in all_channel_full_psd_means_sems])
            channel_sems_psd = np.array([d['sem'] for d in all_channel_full_psd_means_sems])

            # Calculate weighted means across channels
            mean_band_across_channels = np.average(channel_means_band, axis=0, weights=channel_weights)
            mean_psd_across_channels = np.average(channel_means_psd, axis=0, weights=channel_weights)
            
            # Calculate SEM of the means across channels
            if len(channel_means_band) > 1:
                sem_band_across_channels = sem(channel_means_band, axis=0, nan_policy='omit')
                sem_psd_across_channels = sem(channel_means_psd, axis=0, nan_policy='omit')
            else:
                sem_band_across_channels = np.zeros_like(mean_band_across_channels)
                sem_psd_across_channels = np.zeros_like(mean_psd_across_channels)

            psd_data[file_name]['mean_across_channels'] = {
                'band_power': {'means': mean_band_across_channels.tolist(), 'errors': sem_band_across_channels.tolist()},
                'full_psd': {'mean_power': mean_psd_across_channels.tolist(), 'sem_power': sem_psd_across_channels.tolist(), 'frequencies': frequencies}
            }
            all_file_band_means_sems.append({'mean': mean_band_across_channels, 'sem': sem_band_across_channels, 'weight': np.sum(channel_weights)})
            all_file_full_psd_means_sems.append({'mean': mean_psd_across_channels, 'sem': sem_psd_across_channels, 'weight': np.sum(channel_weights)})

    if all_file_band_means_sems:
        # If there is only one file, the "grand mean" is simply the "mean across channels" for that file,
        # and the SEM represents the variance across that file's channels.
        if len(all_file_band_means_sems) == 1:
            grand_mean_band = all_file_band_means_sems[0]['mean']
            grand_sem_band = all_file_band_means_sems[0]['sem']
            
            grand_mean_psd = all_file_full_psd_means_sems[0]['mean']
            grand_sem_psd = all_file_full_psd_means_sems[0]['sem']

        # If there are multiple files, calculate a true grand mean and SEM across the files.
        else:
            # Extract means and weights for grand averaging
            file_means_band = np.array([d['mean'] for d in all_file_band_means_sems])
            file_weights = np.array([d['weight'] for d in all_file_band_means_sems])
            file_means_psd = np.array([d['mean'] for d in all_file_full_psd_means_sems])

            # Calculate weighted grand means
            grand_mean_band = np.average(file_means_band, axis=0, weights=file_weights)
            grand_mean_psd = np.average(file_means_psd, axis=0, weights=file_weights)
            
            # Calculate SEM of the means across files
            grand_sem_band = sem(file_means_band, axis=0, nan_policy='omit')
            grand_sem_psd = sem(file_means_psd, axis=0, nan_policy='omit')

        psd_data['grand_mean'] = {
            'band_power': {'means': grand_mean_band.tolist(), 'errors': grand_sem_band.tolist()},
            'full_psd': {'mean_power': grand_mean_psd.tolist(), 'sem_power': grand_sem_psd.tolist(), 'frequencies': frequencies}
        }

def _process_coh_results(coh_data):
    """Calculates and adds hierarchical means and SEM for coherence data in-place."""
    all_file_means_and_sems = []

    for file_name, pairs in coh_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(pairs, dict): continue

        all_pair_means_and_sems = []
        for pair_name, time_slices in pairs.items():
            if pair_name in AGGREGATION_KEYS or not isinstance(time_slices, dict): continue

            means_list = []
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS: continue
                if isinstance(values, dict) and 'band_coherence' in values:
                    means_list.append(values['band_coherence']['means'])
            
            if means_list:
                mean_across_time = np.mean(means_list, axis=0)
                if len(means_list) > 1:
                    sem_across_time = sem(means_list, axis=0, nan_policy='omit')
                else:
                    sem_across_time = np.zeros_like(mean_across_time)
                
                pairs[pair_name]['mean_across_time'] = {'means': mean_across_time, 'errors': sem_across_time}
                all_pair_means_and_sems.append({'mean': mean_across_time, 'sem': sem_across_time})

        if all_pair_means_and_sems:
            pair_means = np.array([d['mean'] for d in all_pair_means_and_sems])
            mean_across_pairs = np.mean(pair_means, axis=0)
            if len(pair_means) > 1:
                sem_across_pairs = sem(pair_means, axis=0, nan_policy='omit')
            else:
                sem_across_pairs = np.zeros_like(mean_across_pairs)

            coh_data[file_name]['mean_across_pairs'] = {'means': mean_across_pairs, 'errors': sem_across_pairs}
            all_file_means_and_sems.append({'mean': mean_across_pairs, 'sem': sem_across_pairs})

    if all_file_means_and_sems:
        file_means = np.array([d['mean'] for d in all_file_means_and_sems])
        grand_mean = np.mean(file_means, axis=0)
        if len(file_means) > 1:
            grand_sem = sem(file_means, axis=0, nan_policy='omit')
        else:
            grand_sem = np.zeros_like(grand_mean)
            
        coh_data['grand_mean'] = {'means': grand_mean, 'errors': grand_sem}

def calculate_hierarchical_means(all_results):
    """Main orchestrator to calculate means and SEM for all analysis types."""
    if 'pac_results' in all_results:
        _process_pac_results(all_results['pac_results'])

    if 'psd_results' in all_results:
        _process_psd_results(all_results['psd_results'])
        
    if 'coh_results' in all_results:
        _process_coh_results(all_results['coh_results'])
        
    if 'comod_results' in all_results:
        _process_comod_results(all_results['comod_results'])
    
    return _clean_nans(all_results)

def _process_comod_results(comod_data):
    """
    Calculates and adds hierarchical means and SEM for Comodulogram data (2D matrices).
    """
    all_file_means = []

    for file_name, channels in comod_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict):
            continue

        all_channel_means = []
        for channel_name, time_slices in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(time_slices, dict):
                continue
            
            # Gather all matrices for the current channel across its time slices
            matrices_across_time = []
            for time_slice, matrix in time_slices.items():
                if time_slice in AGGREGATION_KEYS:
                    continue
                # Assuming matrix is a list of lists or np array
                matrices_across_time.append(np.array(matrix))
            
            if matrices_across_time:
                # Calculate mean across time
                mean_across_time = np.mean(matrices_across_time, axis=0)
                if len(matrices_across_time) > 1:
                    sem_across_time = sem(matrices_across_time, axis=0, nan_policy='omit')
                else:
                    sem_across_time = np.zeros_like(mean_across_time)
                
                # Store back in the structure
                # We store lists for JSON compatibility
                channels[channel_name]['mean_across_time'] = {
                    'mean': mean_across_time.tolist(), 
                    'sem': sem_across_time.tolist()
                }
                
                all_channel_means.append(mean_across_time)
        
        if all_channel_means:
            # Calculate mean across channels for this file
            mean_across_channels = np.mean(all_channel_means, axis=0)
            if len(all_channel_means) > 1:
                sem_across_channels = sem(all_channel_means, axis=0, nan_policy='omit')
            else:
                sem_across_channels = np.zeros_like(mean_across_channels)
            
            comod_data[file_name]['mean_across_channels'] = {
                'mean': mean_across_channels.tolist(),
                'sem': sem_across_channels.tolist()
            }
            
            all_file_means.append(mean_across_channels)

    if all_file_means:
        # Calculate Grand Mean across files
        grand_mean = np.mean(all_file_means, axis=0)
        if len(all_file_means) > 1:
            grand_sem = sem(all_file_means, axis=0, nan_policy='omit')
        else:
            grand_sem = np.zeros_like(grand_mean)
        
        comod_data['grand_mean'] = {
            'mean': grand_mean.tolist(),
            'sem': grand_sem.tolist()
        }

