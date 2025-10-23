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
    Calculates a Grand Mean and SEM and returns them, handling the case of no data.
    """
    all_mis, all_mvls, all_plvs = [], [], []

    for file_name, channels in pac_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict): continue
        for channel_name, bands in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(bands, dict): continue
            for band_info, time_slices in bands.items():
                if band_info in AGGREGATION_KEYS or not isinstance(time_slices, dict): continue
                for time_slice, values in time_slices.items():
                    if time_slice in AGGREGATION_KEYS: continue
                    if isinstance(values, dict):
                        if 'MI' in values and values['MI'] is not None:
                            all_mis.append(values['MI'])
                        if 'MVL' in values and values['MVL'] is not None:
                            all_mvls.append(values['MVL'])
                        if 'PLV' in values and values['PLV'] is not None:
                            all_plvs.append(values['PLV'])

    if all_mis:
        grand_mean = {
            'MI': np.nanmean(all_mis),
            'MVL': np.nanmean(all_mvls),
            'PLV': np.nanmean(all_plvs)
        }
        grand_sem = {
            'MI': sem(all_mis, nan_policy='omit'),
            'MVL': sem(all_mvls, nan_policy='omit'),
            'PLV': sem(all_plvs, nan_policy='omit')
        }
        return grand_mean, grand_sem
    else:
        return None, None

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
                sem_psd_across_time = sem(full_psd_powers_array, axis=0, nan_policy='omit') if len(full_psd_powers_array) > 0 else np.zeros_like(mean_psd_across_time)

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
            
            # SEM calculation remains unweighted for now
            sem_band_across_channels = np.sqrt(np.sum(np.square(channel_sems_band), axis=0)) / len(all_channel_band_means_sems)
            sem_psd_across_channels = np.sqrt(np.sum(np.square(channel_sems_psd), axis=0)) / len(all_channel_full_psd_means_sems)

            psd_data[file_name]['mean_across_channels'] = {
                'band_power': {'means': mean_band_across_channels.tolist(), 'errors': sem_band_across_channels.tolist()},
                'full_psd': {'mean_power': mean_psd_across_channels.tolist(), 'sem_power': sem_psd_across_channels.tolist(), 'frequencies': frequencies}
            }
            all_file_band_means_sems.append({'mean': mean_band_across_channels, 'sem': sem_band_across_channels, 'weight': np.sum(channel_weights)})
            all_file_full_psd_means_sems.append({'mean': mean_psd_across_channels, 'sem': sem_psd_across_channels, 'weight': np.sum(channel_weights)})

    if all_file_band_means_sems:
        # Extract means, SEMs, and weights for grand averaging
        file_means_band = np.array([d['mean'] for d in all_file_band_means_sems])
        file_sems_band = np.array([d['sem'] for d in all_file_band_means_sems])
        file_weights = np.array([d['weight'] for d in all_file_band_means_sems])

        file_means_psd = np.array([d['mean'] for d in all_file_full_psd_means_sems])
        file_sems_psd = np.array([d['sem'] for d in all_file_full_psd_means_sems])

        # Calculate weighted grand means
        grand_mean_band = np.average(file_means_band, axis=0, weights=file_weights)
        grand_mean_psd = np.average(file_means_psd, axis=0, weights=file_weights)
        
        # SEM calculation remains unweighted for now
        grand_sem_band = np.sqrt(np.sum(np.square(file_sems_band), axis=0)) / len(all_file_band_means_sems)
        grand_sem_psd = np.sqrt(np.sum(np.square(file_sems_psd), axis=0)) / len(all_file_full_psd_means_sems)

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

            means_list, errors_list = [], []
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS: continue
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

def calculate_hierarchical_means(all_results):
    """Main orchestrator to calculate means and SEM for all analysis types."""
    if 'pac_results' in all_results:
        mean, sem = _process_pac_results(all_results['pac_results'])
        if mean and sem:
            all_results['pac_results']['grand_mean'] = mean
            all_results['pac_results']['grand_sem'] = sem

    if 'psd_results' in all_results:
        _process_psd_results(all_results['psd_results'])
        
    if 'coh_results' in all_results:
        _process_coh_results(all_results['coh_results'])
    
    return _clean_nans(all_results)

