import pandas as pd
from io import BytesIO
from openpyxl.drawing.image import Image
import matplotlib.pyplot as plt

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