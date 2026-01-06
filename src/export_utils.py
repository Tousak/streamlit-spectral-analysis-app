import pandas as pd
from io import BytesIO
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MatplotlibFigure
import io
import re
import streamlit as st
import zipfile
import plotly.graph_objects as go
import concurrent.futures
import numpy as np
import warnings

# A list of keys that are added during the hierarchical mean calculations.
# These keys have a different data structure and should be skipped by the flattening functions.
AGGREGATION_KEYS = ['mean_across_time', 'mean_across_channels', 'mean_across_pairs', 'grand_mean', 'grand_sem']

def _flatten_full_psd_results(psd_data, f_h):
    """
    Flattens the full PSD results into a wide format for Excel export,
    skipping any aggregated data.
    """
    rows = []
    for file_name, channels in psd_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict):
            continue
        for channel_name, time_slices in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(time_slices, dict):
                continue
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS:
                    continue
                
                if isinstance(values, dict) and 'full_psd' in values:
                    full_psd = values['full_psd']
                    
                    if 'power' not in full_psd:  # Ensure it's not an aggregated entry
                        continue

                    all_frequencies = np.array(full_psd.get('frequencies', []))
                    all_powers = np.array(full_psd.get('power', []))

                    if all_powers.size == 0:
                        continue
                    
                    valid_indices = np.where(all_frequencies <= f_h)[0]
                    if valid_indices.size == 0:
                        continue
                    
                    frequencies = all_frequencies[valid_indices]
                    powers = all_powers[valid_indices]

                    base_metadata = {
                        'File': file_name,
                        'Channel': channel_name,
                        'Time_Slice': time_slice,
                    }
                    
                    raw_row_data = {**base_metadata, 'Scale': 'Raw', **{f"{freq:.4f}": power for freq, power in zip(frequencies, powers)}}
                    rows.append(raw_row_data)

                    epsilon = np.finfo(float).eps
                    log_powers = 10 * np.log10(powers + epsilon)
                    log_row_data = {**base_metadata, 'Scale': 'Log10 (dB)', **{f"{freq:.4f}": lp for freq, lp in zip(frequencies, log_powers)}}
                    rows.append(log_row_data)
    return rows

def _flatten_psd_results(psd_data):
    """Flattens band power PSD results, skipping aggregated data."""
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, channels in psd_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict): continue
        for channel_name, time_slices in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(time_slices, dict): continue
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS: continue
                if isinstance(values, dict) and 'band_power' in values:
                    for i, band in enumerate(band_labels):
                        rows.append({
                            'File': file_name, 'Channel': channel_name, 
                            'Time_Slice': time_slice, 'Band': band, 
                            'Mean_Power': values['band_power']['means'][i], 
                            'SEM_Power': values['band_power']['errors'][i]
                        })
    return rows

def _flatten_pac_results(pac_data):
    """Flattens PAC results, skipping aggregated data."""
    rows = []
    for file_name, channels_or_pairs in pac_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels_or_pairs, dict): continue
        for name, bands in channels_or_pairs.items():
            if name in AGGREGATION_KEYS or not isinstance(bands, dict): continue
            for band_info, time_slices in bands.items():
                if band_info in AGGREGATION_KEYS or not isinstance(time_slices, dict): continue
                for time_slice, values in time_slices.items():
                     if time_slice in AGGREGATION_KEYS: continue
                     if time_slice.endswith('_sliding'): continue # Skip sliding window data
                     if isinstance(values, dict):
                        rows.append({
                            'File': file_name, 'Channel_or_Pair': name, 
                            'Bands': band_info, 'Time_Slice': time_slice, 
                            'MI': values.get('MI'), 'MVL': values.get('MVL'), 'PLV': values.get('PLV')
                        })
    return rows

def _flatten_coh_results(coh_data):
    """Flattens coherence results, skipping aggregated data."""
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, pairs in coh_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(pairs, dict): continue
        for pair_name, time_slices in pairs.items():
            if pair_name in AGGREGATION_KEYS or not isinstance(time_slices, dict): continue
            for time_slice, values in time_slices.items():
                if time_slice in AGGREGATION_KEYS: continue
                if isinstance(values, dict) and 'band_coherence' in values:
                    for i, band in enumerate(band_labels):
                        rows.append({
                            'File': file_name, 'Channel_Pair': pair_name, 
                            'Time_Slice': time_slice, 'Band': band, 
                            'Mean_Coherence': values['band_coherence']['means'][i], 
                            'SEM_Coherence': values['band_coherence']['errors'][i]
                        })
    return rows


def _flatten_psd_mean_across_time_results(psd_data):
    """
    Flattens mean across time ranges PSD results into a wide format for Excel export.
    """
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, channels in psd_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(channels, dict):
            continue
        for channel_name, data in channels.items():
            if channel_name in AGGREGATION_KEYS or not isinstance(data, dict):
                continue
            if 'mean_across_time' in data:
                mean_data = data['mean_across_time']['band_power']
                for i, band in enumerate(band_labels):
                    rows.append({
                        'File': file_name,
                        'Channel': channel_name,
                        'Band': band,
                        'Mean_Power': mean_data['means'][i],
                        'SEM_Power': mean_data['errors'][i]
                    })
    return rows

def _flatten_psd_mean_across_channels_results(psd_data):
    """
    Flattens mean across channels PSD results into a wide format for Excel export.
    """
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, data in psd_data.items():
        if file_name in AGGREGATION_KEYS or not isinstance(data, dict):
            continue
        if 'mean_across_channels' in data:
            mean_data = data['mean_across_channels']['band_power']
            for i, band in enumerate(band_labels):
                rows.append({
                    'File': file_name,
                    'Band': band,
                    'Mean_Power': mean_data['means'][i],
                    'SEM_Power': mean_data['errors'][i]
                })
    return rows

def _flatten_psd_grand_mean_full_psd_results(psd_data, f_h):
    """
    Flattens grand mean full PSD results into a wide format for Excel export.
    """
    rows = []
    if 'grand_mean' in psd_data:
        full_psd = psd_data['grand_mean']['full_psd']
        all_frequencies = np.array(full_psd.get('frequencies', []))
        all_powers = np.array(full_psd.get('mean_power', []))
        all_sems = np.array(full_psd.get('sem_power', []))

        if all_powers.size == 0:
            return []
        
        valid_indices = np.where(all_frequencies <= f_h)[0]
        if valid_indices.size == 0:
            return []
        
        frequencies = all_frequencies[valid_indices]
        powers = all_powers[valid_indices]
        sems = all_sems[valid_indices]

        base_metadata = {'Scale': 'Raw'}
        raw_row_data = {**base_metadata, **{f"{freq:.4f}": power for freq, power in zip(frequencies, powers)}}
        rows.append(raw_row_data)

        sem_row_data = {**base_metadata, 'Scale': 'SEM', **{f"{freq:.4f}": sem_val for freq, sem_val in zip(frequencies, sems)}}
        rows.append(sem_row_data)

        epsilon = np.finfo(float).eps
        log_powers = 10 * np.log10(powers + epsilon)
        log_row_data = {**base_metadata, 'Scale': 'Log10 (dB)', **{f"{freq:.4f}": lp for freq, lp in zip(frequencies, log_powers)}}
        rows.append(log_row_data)
    return rows

def export_to_excel(all_results, params):
    """
    Main function to export results to a multi-sheet Excel file.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']

        # --- Write Detailed Summary Sheets ---
        psd_rows = _flatten_psd_results(all_results.get('psd_results', {}))
        if psd_rows:
            pd.DataFrame(psd_rows).to_excel(writer, sheet_name='PSD_Summary', index=False)

        f_h = params.get('F_h', 100)
        full_psd_rows = _flatten_full_psd_results(all_results.get('psd_results', {}), f_h)
        if full_psd_rows:
            df_full_psd = pd.DataFrame(full_psd_rows)
            metadata_cols = ['File', 'Channel', 'Time_Slice', 'Scale']
            freq_cols = sorted([col for col in df_full_psd.columns if col not in metadata_cols], key=float)
            df_full_psd = df_full_psd[metadata_cols + freq_cols]
            df_full_psd.to_excel(writer, sheet_name='PSD_Full', index=False)

        pac_rows = _flatten_pac_results(all_results.get('pac_results', {}))
        if pac_rows:
            pd.DataFrame(pac_rows).to_excel(writer, sheet_name='PAC_Summary', index=False)

        coh_rows = _flatten_coh_results(all_results.get('coh_results', {}))
        if coh_rows:
            pd.DataFrame(coh_rows).to_excel(writer, sheet_name='Coherence_Summary', index=False)

        # --- Write Mean Across Time Ranges Sheets ---
        psd_mean_time_rows = _flatten_psd_mean_across_time_results(all_results.get('psd_results', {}))
        if psd_mean_time_rows:
            pd.DataFrame(psd_mean_time_rows).to_excel(writer, sheet_name='PSD_Mean_Time', index=False)

        # --- Write Mean Across Channels Sheets ---
        psd_mean_channels_rows = _flatten_psd_mean_across_channels_results(all_results.get('psd_results', {}))
        if psd_mean_channels_rows:
            pd.DataFrame(psd_mean_channels_rows).to_excel(writer, sheet_name='PSD_Mean_Channels', index=False)

        # --- Write Grand Mean Sheets ---
        psd_summary = all_results.get('psd_results', {})
        if 'grand_mean' in psd_summary:
            # Export Band Power Grand Mean
            df_psd_mean_band = pd.DataFrame(psd_summary['grand_mean']['band_power'])
            df_psd_mean_band['Band'] = band_labels
            df_psd_mean_band.to_excel(writer, sheet_name='Grand_Mean_PSD_Band', index=False)

            # Export Full PSD Grand Mean
            full_psd_grand_mean_rows = _flatten_psd_grand_mean_full_psd_results(psd_summary, f_h)
            if full_psd_grand_mean_rows:
                df_full_psd_grand_mean = pd.DataFrame(full_psd_grand_mean_rows)
                metadata_cols = ['Scale']
                freq_cols = sorted([col for col in df_full_psd_grand_mean.columns if col not in metadata_cols], key=float)
                df_full_psd_grand_mean = df_full_psd_grand_mean[metadata_cols + freq_cols]
                df_full_psd_grand_mean.to_excel(writer, sheet_name='Grand_Mean_PSD_Full', index=False)


        pac_summary = all_results.get('pac_results', {})
        if 'grand_mean' in pac_summary and 'grand_sem' in pac_summary:
            mean_data = pac_summary['grand_mean']
            sem_data = pac_summary['grand_sem']
            mean_row = {'Metric': 'Mean', **mean_data}
            sem_row = {'Metric': 'SEM', **sem_data}
            df_pac_mean = pd.DataFrame([mean_row, sem_row])
            df_pac_mean.to_excel(writer, sheet_name='Grand_Mean_PAC', index=False)

        coh_summary = all_results.get('coh_results', {})
        if 'grand_mean' in coh_summary:
            df_coh_mean = pd.DataFrame(coh_summary['grand_mean'])
            df_coh_mean['Band'] = band_labels
            df_coh_mean.to_excel(writer, sheet_name='Grand_Mean_Coherence', index=False)

    return output.getvalue() if writer.sheets else None


# Helper function to convert a single figure to bytes.
def _convert_figure_to_bytes(fig_obj, image_format):
    """Converts a single Plotly or Matplotlib figure to image bytes."""
    if isinstance(fig_obj, go.Figure):
        return fig_obj.to_image(format=image_format)
    elif isinstance(fig_obj, MatplotlibFigure):
        img_buffer = io.BytesIO()
        dpi = 150 if image_format == 'png' else 300 
        # Suppress Matplotlib warnings (e.g., about thread safety)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig_obj.savefig(img_buffer, format=image_format, bbox_inches='tight', dpi=dpi)
        return img_buffer.getvalue()
    return None

@st.cache_data
def create_figures_zip_fast(cache_key, _figures_dict, image_format):
    """
    Creates a zip archive in memory by converting figures to images in parallel.
    """
    zip_buffer = io.BytesIO()
    
    tasks = []
    for file_key, channels_dict in _figures_dict.items():
        for channel_key, plots_dict in channels_dict.items():
            for plot_key, fig_obj in plots_dict.items():
                sanitized_plot_key = re.sub(r'[\\/*?:"<>|]', "", plot_key)
                filename = f"{file_key}/{channel_key}/{sanitized_plot_key}.{image_format}"
                tasks.append((filename, fig_obj))

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_filename = {
                executor.submit(_convert_figure_to_bytes, fig_obj, image_format): filename
                for filename, fig_obj in tasks
            }
            for future in concurrent.futures.as_completed(future_to_filename):
                filename = future_to_filename[future]
                try:
                    image_bytes = future.result()
                    if image_bytes:
                        zip_file.writestr(filename, image_bytes)
                except Exception as e:
                    # Log error to console instead of UI to avoid confusing the user
                    print(f"Failed to process '{filename}': {e}")

    return zip_buffer.getvalue()
