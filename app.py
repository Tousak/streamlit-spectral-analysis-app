import streamlit as st
import scipy.signal
import os
from src import main_FE, utils, file_loader, PSD, PAC, Comudologram, coherence, analysis_utils, export_utils, file_loader
from src.plotting import time_plotting, PSD_plotting, PAC_plotting, COH_plotting, COM_plotting
import pandas as pd
import io

from src import utils


for key in [
    "psd_results", "psd_figures", "pac_figures", "pac_results",
    "coh_figures", "coh_results", "comod_figures"
]:
    if key not in st.session_state:
        st.session_state[key] = False

start_button = False # Initialize start_button



# --- Page Configuration ---
st.set_page_config(page_title="Signal Processing Dashboard", layout="wide")

st.title("🔬 Signal Analysis App")


file_loader.file_list_creator()

# --- 2. PROCESS THE FILES FROM SESSION STATE ---
st.header("📂 Filtered File Contents")
file_loader.files_struturization()
st.divider()

# Create a mapping from filename to the file object for easy access later
file_map = {}
if st.session_state.file_list:
    for item in st.session_state.file_list:
        if isinstance(item, str):
            file_map[os.path.basename(item)] = item
        else:
            file_map[item.name] = item

if 'selections' in st.session_state:
    # Get the set of currently uploaded filenames
    current_files = set(file_map.keys())
    
    # Get the set of filenames currently in the selections dictionary
    selected_files = set(st.session_state.selections.keys())
    
    # Find which files have been removed
    files_to_remove = selected_files - current_files
    
    # Remove the old, "ghost" files from the selections state
    for file_name in files_to_remove:
        del st.session_state.selections[file_name]   
choosed = utils.has_non_empty_third_level(st.session_state.selections)


# ==============================================================================
# TIME DOMAIN SECTION
# ==============================================================================
st.subheader("📈 Signal in Time Domain")
if 'selections' in st.session_state and utils.has_non_empty_third_level(st.session_state.selections):
    time_plotting.plot_signal_from_selections(file_map)
else:
    st.info("Upload files and configure channels to view signals.")


# ==============================================================================
# PSD SECTION 
# ==============================================================================
if st.session_state.file_list and choosed:

    # PSD parametrs input
    st.subheader('PSD settings')
    params = main_FE.PSD_settings()
    params['spec_win_size'], params['spec_noverlap'], spec_overlap_percent = utils.calculate_spectrogram_params(params['fs'], params['desired_freq_res'], params['desired_time_res'])

    # Construct welch_params from the main params
    nfft_welch = int(params['fs'] / params['desired_resolution']) # Assuming desired_resolution is 0.25
    params['welch_params'] = {
        'window': scipy.signal.windows.hamming(nfft_welch),
        'noverlap': nfft_welch // 2,
        'nfft': nfft_welch
    }

    st.divider()
    PAC_calc_state = st.toggle('Activate PAC calculations', on_change=utils.reset_values)
    if PAC_calc_state:
        
        st.subheader('PAC settings')
        # PAC parametrs input
        pac_params = main_FE.PAC_settings(st.session_state.selections)
        pac_params['fs'] = params['fs']
        pac_params['F_h'] = params['F_h']
 

    
    start_button = st.button("Start Calculations")
    # In app.py, inside your button-click logic

    if "psd_figures" not in st.session_state:
        st.session_state.psd_figures=False

    if start_button and st.session_state.file_list and choosed:
        if not st.session_state.get('selections'):
            st.warning("No files or channels have been configured.")
        else:
            with st.spinner("Calculating PSD... Please wait."):
                # Run the analysis to get all results and figure objects
                psd_results, psd_figures = PSD.run_psd_analysis(
                    selections=st.session_state.selections,
                    params=params,
                    file_map=file_map,
                    load_mat_file_func=file_loader.load_mat_file
                )
                
                # Store numerical results
                st.session_state.psd_results = psd_results
                st.session_state.psd_figures = psd_figures
            st.success("PSD Analysis Complete!")


st.divider()
if st.session_state.get('psd_results'):
    PSD_plotting.plot_PSDs(params)
else:
    st.info("No PSD results to display")

# ==============================================================================
# PAC SECTION 
# ==============================================================================
if st.session_state.file_list and choosed:                 
    if PAC_calc_state and start_button:

        with st.spinner("Calculating PAC... This may take a moment."):
            # Call the main orchestrator function
            pac_results, pac_figures = PAC.run_pac_analysis(
                selections=st.session_state.selections,
                pac_params=pac_params,
                file_map=file_map,
                load_mat_file_func=file_loader.load_mat_file # Pass the cached loader function
            )
            st.session_state.pac_figures=pac_figures
            st.session_state.pac_results=pac_results


        st.success("PAC Analysis Complete!")

if st.session_state.get('pac_results') and st.session_state.get('pac_figures'):    
    PAC_plotting.plot_PAC(st.session_state.pac_results, st.session_state.pac_figures)
else:
    st.info("No PAC results to display")

# ==============================================================================
# COH SECTION
# ==============================================================================
if st.session_state.file_list and choosed:                 
    
    if PAC_calc_state and start_button:
        if pac_params.get('calculate_coherence'):
            with st.spinner("Calculating Coherence..."):
                coh_results, coh_figures = coherence.run_coherence_analysis(
                    selections=st.session_state.selections,
                    params=params, # Pass main params for F_c, F_h etc.
                    pac_params=pac_params,
                    file_map=file_map,
                    load_mat_file_func=file_loader.load_mat_file
                )
                # Store results in session state
                st.session_state.coh_results = coh_results
                st.session_state.coh_figures = coh_figures
            
            st.success("Coherence analysis complete!")      

# --- Display logic for Coherence plots ---

if 'coh_results' in st.session_state and st.session_state.coh_results:
    COH_plotting.plot_COH(st.session_state.coh_figures)
else:
    st.info("No COH results to display")


# ==============================================================================
# COM SECTION
# ==============================================================================
if st.session_state.file_list and choosed:
    if PAC_calc_state and pac_params["comudolo_state"]:                 
        if pac_params['comudolo_state'] and start_button:
            with st.spinner("Calculating Comodulograms... This is computationally intensive and may take a long time."):
                # Call the new orchestrator function
                comod_results, comod_figures = Comudologram.run_comodulogram_analysis(
                    selections=st.session_state.selections,
                    params={**params, **pac_params}, # Combine PSD and PAC params
                    file_map=file_map,
                    load_mat_file_func=file_loader.load_mat_file
                )
                st.session_state.comod_figures = comod_figures
            
            st.success("Comodulogram analysis complete!")

# --- Display logic for Comodulogram plots ---
if 'comod_figures' in st.session_state and st.session_state.comod_figures:
    COM_plotting.plot_COM(st.session_state.comod_figures)
else:
    st.info("No Comudologram results to display")


# ==============================================================================
# Export SECTION
# ==============================================================================

merged_results = utils.merge_results_from_session()
if 'results' not in st.session_state:
    st.session_state.results = False

# Calculate hierarchical means, which modifies merged_results in-place
processed_results = analysis_utils.calculate_hierarchical_means(merged_results)

# Update session state with the processed data for each analysis type
if 'psd_results' in processed_results:
    st.session_state.psd_results = processed_results['psd_results']
if 'pac_results' in processed_results:
    st.session_state.pac_results = processed_results['pac_results']
if 'coh_results' in processed_results:
    st.session_state.coh_results = processed_results['coh_results']

st.session_state.results = processed_results
if start_button:
    st.rerun()
st.divider()
if st.session_state.get('results'):
    if len(st.session_state.results) > 0:
        st.header("💾 Export Results")

# --- GATHER ALL FIGURE DICTIONARIES (CORRECTED MERGE LOGIC) ---
all_figures = {}
sources = {
    "PSD": st.session_state.get('psd_figures'),
    "PAC": st.session_state.get('pac_figures'),
    "COH": st.session_state.get('coh_figures'),
    "COMOD": st.session_state.get('comod_figures')
}
figure_exist = False
for prefix, fig_dict in sources.items():
    if fig_dict: # Check if the dictionary exists and is not empty
        for original_key, fig_value in fig_dict.items():
            # Create a new, unique key
            new_key = f"{prefix}_{original_key}"
            all_figures[new_key] = fig_value
            figure_exist = True
# --- END GATHERING ---

# Check if there are any results to export
if 'results' in st.session_state and st.session_state.results:
    if len(st.session_state.results) > 0:
        file_name_input = st.text_input(
            "Enter a name for the Excel file:", 
            value="analysis_results.xlsx"
        )
        
        c1,c2,c3,c4 = st.columns([1,1,1,4])

        # Generate the Excel file, passing the newly created 'all_figures' dict
        excel_data = export_utils.export_to_excel(
            st.session_state.results,
            params
        )
        if excel_data:
            c1.download_button(
                label="📥 Download Results as Excel",
                data=excel_data,
                file_name=file_name_input,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No numerical results were generated to export.")
     
    if figure_exist:
        results_key = tuple(sorted(st.session_state.results.keys()))
        
        with c2:
            if 'svg_zip_bytes' not in st.session_state:
                st.session_state.svg_zip_bytes = None
            if st.button('Convert figures to svg', key='button_svg', width="stretch"):
                with st.spinner("Preparing vector figures (.svg)..."):
                    st.session_state.svg_zip_bytes = export_utils.create_figures_zip_fast(
                        results_key,  # The key for caching
                        all_figures,  # The unhashable data (note: no underscore here)
                        'svg'
                    )
            if st.session_state.svg_zip_bytes is not None:
                st.download_button(
                    label="📁 Download as Vector (.svg)",
                    data=st.session_state.svg_zip_bytes,
                    file_name="vector_figures.zip",
                    mime="application/zip"
                )
        
        with c3:
            if 'png_zip_bytes' not in st.session_state:
                st.session_state.png_zip_bytes = None
            
            if st.button('Convert figures to png', key='button_png', width="stretch"):
                with st.spinner("Preparing image figures (.png)..."):
                    st.session_state.png_zip_bytes = export_utils.create_figures_zip_fast(
                        results_key, 
                        all_figures, 
                        'png'
                    )
            if st.session_state.png_zip_bytes is not None:
                st.download_button(
                    label="🖼️ Download as Image (.png)",
                    data=st.session_state.png_zip_bytes,
                    file_name="image_figures.zip",
                    mime="application/zip"
                )
    else:
        st.info("Generate figures to enable download.")
else:
    st.warning("No results to export. Please run an analysis first.")

