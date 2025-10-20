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
# export_utils.py

def _flatten_full_psd_results(psd_data, f_h): # <-- Add f_h argument
    """
    Flattens the full PSD results into a wide format for Excel export.
    Filters frequencies up to f_h.
    Creates two rows for each time slice: one for raw power and one for log10 power (dB).
    """
    rows = []
    for file_name, channels in psd_data.items():
        if not isinstance(channels, dict): continue
        for channel_name, time_slices in channels.items():
            if not isinstance(time_slices, dict): continue
            for time_slice, values in time_slices.items():
                if isinstance(values, dict) and 'full_psd' in values:
                    full_psd = values['full_psd']
                    
                    # Get all frequencies and powers
                    all_frequencies = np.array(full_psd.get('frequencies', []))
                    all_powers = np.array(full_psd.get('power', []))
                    
                    # --- NEW: Filter data based on f_h ---
                    valid_indices = np.where(all_frequencies <= f_h)[0]
                    if valid_indices.size == 0: continue # Skip if no data in range
                    
                    # Apply the filter to get only the data you need
                    frequencies = all_frequencies[valid_indices]
                    powers = all_powers[valid_indices]
                    # --- END OF NEW SECTION ---

                    base_metadata = {
                        'File': file_name,
                        'Channel': channel_name,
                        'Time_Slice': time_slice,
                    }
                    
                    # 1. Create and append the Raw Power Row
                    raw_row_data = base_metadata.copy()
                    raw_row_data['Scale'] = 'Raw'
                    raw_power_dict = {f"{freq:.4f}": power for freq, power in zip(frequencies, powers)}
                    raw_row_data.update(raw_power_dict)
                    rows.append(raw_row_data)

                    # 2. Create and append the Log Power (dB) Row
                    epsilon = np.finfo(float).eps
                    log_powers = 10 * np.log10(powers + epsilon)
                    
                    log_row_data = base_metadata.copy()
                    log_row_data['Scale'] = 'Log10 (dB)'
                    log_power_dict = {f"{freq:.4f}": log_power for freq, log_power in zip(frequencies, log_powers)}
                    log_row_data.update(log_power_dict)
                    rows.append(log_row_data)
    return rows

# --- Ensure all your flattening helper functions are in this file ---
def _flatten_psd_results(psd_data):
    # ... (your existing function)
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, channels in psd_data.items():
        if not isinstance(channels, dict): continue
        for channel_name, time_slices in channels.items():
            if not isinstance(time_slices, dict): continue
            for time_slice, values in time_slices.items():
                if isinstance(values, dict) and 'band_power' in values:
                    for i, band in enumerate(band_labels):
                        rows.append({'File': file_name, 'Channel': channel_name, 'Time_Slice': time_slice, 'Band': band, 'Mean_Power': values['band_power']['means'][i], 'SEM_Power': values['band_power']['errors'][i]})
    return rows

def _flatten_pac_results(pac_data):
    # ... (your existing function)
    rows = []
    for file_name, channels_or_pairs in pac_data.items():
        if not isinstance(channels_or_pairs, dict): continue
        for name, bands in channels_or_pairs.items():
            if not isinstance(bands, dict): continue
            for band_info, time_slices in bands.items():
                if not isinstance(time_slices, dict): continue
                for time_slice, values in time_slices.items():
                     if isinstance(values, dict):
                        rows.append({'File': file_name, 'Channel_or_Pair': name, 'Bands': band_info, 'Time_Slice': time_slice, 'MI': values.get('MI'), 'MVL': values.get('MVL'), 'PLV': values.get('PLV')})
    return rows

def _flatten_coh_results(coh_data):
    # ... (your existing function)
    rows = []
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    for file_name, pairs in coh_data.items():
        if not isinstance(pairs, dict): continue
        for pair_name, time_slices in pairs.items():
            if not isinstance(time_slices, dict): continue
            for time_slice, values in time_slices.items():
                if isinstance(values, dict) and 'band_coherence' in values:
                    for i, band in enumerate(band_labels):
                        rows.append({'File': file_name, 'Channel_Pair': pair_name, 'Time_Slice': time_slice, 'Band': band, 'Mean_Coherence': values['band_coherence']['means'][i], 'SEM_Coherence': values['band_coherence']['errors'][i]})
    return rows


# export_utils.py

def export_to_excel(all_results, params):
    """
    Main function to export results to a multi-sheet Excel file.
    (Now includes raw and log full PSD data)
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']

        # --- 1. Write Detailed Summary Sheets ---
        psd_rows = _flatten_psd_results(all_results.get('psd_results', {}))
        if psd_rows:
            pd.DataFrame(psd_rows).to_excel(writer, sheet_name='PSD_Summary', index=False)

        # --- UPDATED SECTION for Full PSD ---
        f_h = params.get('F_h', 100)
        full_psd_rows = _flatten_full_psd_results(
            all_results.get('psd_results', {}),
            f_h
            )
        if full_psd_rows:
            df_full_psd = pd.DataFrame(full_psd_rows)
            # Add 'Scale' to the list of metadata columns for sorting
            metadata_cols = ['File', 'Channel', 'Time_Slice', 'Scale']
            freq_cols = sorted(
                [col for col in df_full_psd.columns if col not in metadata_cols],
                key=float
            )
            # Reorder DataFrame columns
            df_full_psd = df_full_psd[metadata_cols + freq_cols]
            df_full_psd.to_excel(writer, sheet_name='PSD_Full', index=False)
        # --- END OF UPDATED SECTION ---

        pac_rows = _flatten_pac_results(all_results.get('pac_results', {}))
        if pac_rows:
            pd.DataFrame(pac_rows).to_excel(writer, sheet_name='PAC_Summary', index=False)

        coh_rows = _flatten_coh_results(all_results.get('coh_results', {}))
        if coh_rows:
            pd.DataFrame(coh_rows).to_excel(writer, sheet_name='Coherence_Summary', index=False)

        # --- 2. Write Grand Mean Sheets (No changes needed here) ---
        # ... (rest of your function remains the same) ...
        psd_summary = all_results.get('psd_results', {})
        if 'grand_mean' in psd_summary:
            df_psd_mean = pd.DataFrame(psd_summary['grand_mean'])
            df_psd_mean['Band'] = band_labels
            df_psd_mean.to_excel(writer, sheet_name='Grand_Mean_PSD', index=False)

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

    if writer.sheets:
        return output.getvalue()
    else:
        return None



# Helper function to convert a single figure to bytes.
# This makes it easy to run this specific task in a separate thread.
def _convert_figure_to_bytes(fig_obj, image_format):
    """Converts a single Plotly or Matplotlib figure to image bytes."""
    if isinstance(fig_obj, go.Figure):
        # For Plotly figures
        return fig_obj.to_image(format=image_format)
    
    elif isinstance(fig_obj, MatplotlibFigure):
        # For Matplotlib figures
        img_buffer = io.BytesIO()
        # Consider making DPI an optional parameter for even faster PNG generation
        dpi = 150 if image_format == 'png' else 300 
        fig_obj.savefig(img_buffer, format=image_format, bbox_inches='tight', dpi=dpi)
        return img_buffer.getvalue()
        
    return None # Return None for unrecognized types


@st.cache_data
def create_figures_zip_fast(cache_key, _figures_dict, image_format):
    """
    Creates a zip archive in memory by converting figures to images in parallel.
    The `cache_key` parameter is used by Streamlit to track changes.
    The `_figures_dict` is ignored by the cache (due to the underscore) but
    is used by the function's logic.
    """
    print(f"CACHE MISS: Generating new ZIP file for key: {cache_key} and format: {image_format}") # For debugging
    
    zip_buffer = io.BytesIO()
    
    # Flatten the nested dictionary into a list of (path, figure_object) tuples
    tasks = []
    # Use the ignored _figures_dict for the actual work
    for file_key, channels_dict in _figures_dict.items():
        for channel_key, plots_dict in channels_dict.items():
            for plot_key, fig_obj in plots_dict.items():
                sanitized_plot_key = re.sub(r'[\\/*?:"<>|]', "", plot_key)
                filename = f"{file_key}/{channel_key}/{sanitized_plot_key}.{image_format}"
                tasks.append((filename, fig_obj))

    # The rest of your function remains exactly the same...
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=
                                                   4) as executor:
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
                    st.error(f"Failed to process '{filename}': {e}")

    return zip_buffer.getvalue()







