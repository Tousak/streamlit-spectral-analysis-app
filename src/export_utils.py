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


def export_to_excel(all_results):
    """
    Main function to export results to a multi-sheet Excel file.
    (Corrected version with proper band labeling and PAC grand mean handling)
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']

        # --- 1. Write Detailed Summary Sheets ---
        psd_rows = _flatten_psd_results(all_results.get('psd_results', {}))
        if psd_rows:
            pd.DataFrame(psd_rows).to_excel(writer, sheet_name='PSD_Summary', index=False)

        pac_rows = _flatten_pac_results(all_results.get('pac_results', {}))
        if pac_rows:
            pd.DataFrame(pac_rows).to_excel(writer, sheet_name='PAC_Summary', index=False)

        coh_rows = _flatten_coh_results(all_results.get('coh_results', {}))
        if coh_rows:
            pd.DataFrame(coh_rows).to_excel(writer, sheet_name='Coherence_Summary', index=False)

        # --- 2. Write Grand Mean Sheets (Corrected) ---
        # PSD Grand Mean
        psd_summary = all_results.get('psd_results', {})
        if 'grand_mean' in psd_summary:
            df_psd_mean = pd.DataFrame(psd_summary['grand_mean'])
            df_psd_mean['Band'] = band_labels # Add the band names
            df_psd_mean.to_excel(writer, sheet_name='Grand_Mean_PSD', index=False)

        # --- PAC Grand Mean (Corrected for two-row format) ---
        pac_summary = all_results.get('pac_results', {})
        if 'grand_mean' in pac_summary and 'grand_sem' in pac_summary:
            mean_data = pac_summary['grand_mean']
            sem_data = pac_summary['grand_sem']
            
            # Create two dictionaries, one for each row
            mean_row = {'Metric': 'Mean', 'MI': mean_data.get('MI'), 'MVL': mean_data.get('MVL'), 'PLV': mean_data.get('PLV')}
            sem_row = {'Metric': 'SEM', 'MI': sem_data.get('MI'), 'MVL': sem_data.get('MVL'), 'PLV': sem_data.get('PLV')}
            
            # Create the DataFrame from a list of the two rows
            df_pac_mean = pd.DataFrame([mean_row, sem_row])
            df_pac_mean.to_excel(writer, sheet_name='Grand_Mean_PAC', index=False)

        # Coherence Grand Mean
        coh_summary = all_results.get('coh_results', {})
        if 'grand_mean' in coh_summary:
            df_coh_mean = pd.DataFrame(coh_summary['grand_mean'])
            df_coh_mean['Band'] = band_labels # Add the band names
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
                    st.error(f"Failed to process '{filename}': {e}")

    return zip_buffer.getvalue()




















# def create_figures_zip(figures_dict, image_format):
#     """
#     Creates a zip archive in memory from a complex dictionary of figures.

#     Args:
#         figures_dict (dict): The nested dictionary containing figures.
#         image_format (str): The desired image format ('svg' or 'png').

#     Returns:
#         bytes: The content of the generated zip file.
#     """
#     zip_buffer = io.BytesIO()
#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#         # Level 1: Iterate through files (e.g., "PSD_346_baseline...")
#         for file_key, channels_dict in figures_dict.items():
#             # Level 2: Iterate through channels (e.g., "Data2_Ch10")
#             for channel_key, plots_dict in channels_dict.items():
#                 # Level 3: Iterate through individual plots
#                 for plot_key, fig_obj in plots_dict.items():
                    
#                     # --- Create a clean, descriptive filename ---
#                     # Remove special characters that are invalid in filenames
#                     sanitized_plot_key = re.sub(r'[\\/*?:"<>|]', "", plot_key)
#                     filename = f"{file_key}/{channel_key}/{sanitized_plot_key}.{image_format}"

#                     image_bytes = None
#                     try:
#                         # --- Handle Plotly Figures ---
#                         if isinstance(fig_obj, go.Figure):
#                             image_bytes = fig_obj.to_image(format=image_format)

#                         # --- Handle Matplotlib Figures ---
#                         elif isinstance(fig_obj, MatplotlibFigure):
#                             # Matplotlib saves to a buffer
#                             img_buffer = io.BytesIO()
#                             fig_obj.savefig(img_buffer, format=image_format, bbox_inches='tight', dpi=300)
#                             image_bytes = img_buffer.getvalue()
#                             img_buffer.close()
                        
#                         else:
#                             # Skip if the object is not a recognized figure type
#                             st.warning(f"Skipping unrecognized object for: {filename}")
#                             continue

#                         # Add the generated image bytes to the zip file
#                         if image_bytes:
#                             zip_file.writestr(filename, image_bytes)

#                     except Exception as e:
#                         st.error(f"Failed to process '{filename}': {e}")

#     return zip_buffer.getvalue()