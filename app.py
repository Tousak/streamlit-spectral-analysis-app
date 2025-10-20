import streamlit as st
import numpy as np
import scipy.signal
import os
from src import main_FE, utils, file_loader, PSD, PAC, Comudologram, coherence, analysis_utils, export_utils
import re
from src import file_loader
import matplotlib.pyplot as plt
import pandas as pd
import io

from src import utils


for key in [
    "psd_results", "psd_figures", "pac_figures", "pac_results",
    "coh_figures", "coh_results", "comod_figures"
]:
    if key not in st.session_state:
        st.session_state[key] = False



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
def has_non_empty_third_level(data: dict) -> bool:
    """
    Check if any third-level value in the nested dictionary is non-empty.
    Returns True if at least one is non-empty, otherwise False.
    """
    for second_level in data.values():
        if isinstance(second_level, dict):
            for third_level_value in second_level.values():
                if third_level_value:  # Non-empty
                    return True
    return False


choosed = has_non_empty_third_level(st.session_state.selections)



################# PSD ########################
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
st.write(st.session_state.psd_results)
if st.session_state.get('psd_figures') and st.session_state.psd_figures:
    
    plot_groups = {} 

    for file_name, channel_figs_dict in st.session_state.psd_figures.items():
        for channel_name, named_figs in channel_figs_dict.items():
            
            figures_by_timerange = {}

            for plot_name, fig in named_figs.items():
                match = re.search(r'(\d{1,4}\.?\d*-\d{1,4}\.?\d*s)', plot_name)
                if match:
                    time_range_str = match.group(1)
                    
                    # 💡 CHANGE 1: The value is now a DICTIONARY, not a list.
                    # This lets us store plots by name.
                    figures_by_timerange.setdefault(time_range_str, {
                        'main_plots': {},
                        'spectrogram': {}
                    })
                    
                    if "Spectrogram" in plot_name:
                        # Store the spectrogram with its full name as the key
                        figures_by_timerange[time_range_str]['spectrogram'][plot_name] = fig
                    else:
                        # Store main plots with their full name as the key
                        figures_by_timerange[time_range_str]['main_plots'][plot_name] = fig

            for time_range, groups in figures_by_timerange.items():
                if groups['main_plots']:
                    group_name = f"{file_name} -> {channel_name} ({time_range}) - Main Plots"
                    plot_groups[group_name] = groups['main_plots']
                
                if groups['spectrogram']:
                    group_name = f"{file_name} -> {channel_name} ({time_range}) - Spectrogram"
                    plot_groups[group_name] = groups['spectrogram']
    
    st.subheader("📊 PSD Plots")
    st.info("Select an analysis group to display its plots.")

    selected_groups = st.multiselect(
        "Select an analysis to display:",
        options=list(plot_groups.keys())
    )

    # --- 💡 CHANGE 2: Updated Display Logic ---
    if selected_groups:
        for group_name in selected_groups:
            st.markdown(f"### Displaying plots for: **{group_name}**")
            
            # This is now a DICTIONARY of {plot_name: fig_object}
            figs_to_display = plot_groups[group_name]
            
            # --- If it's the Main Plots group, use a 2-column layout ---
            if "Main Plots" in group_name:
                col1, col2 = st.columns(2)
                for plot_name, fig in figs_to_display.items():
                    if "Signal" in plot_name or "PSD" in plot_name:
                        col1.plotly_chart(fig, use_container_width=True, key=plot_name)
                    elif "Band Power" in plot_name:
                        col2.plotly_chart(fig, use_container_width=True, key=plot_name)
            
            # --- Otherwise (for the Spectrogram), display normally ---
            else:
                for plot_name, fig in figs_to_display.items():
                    st.plotly_chart(fig, use_container_width=True, key=plot_name)

            st.divider()


####################### PAC #############################
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

if st.session_state.get('pac_figures') and st.session_state.pac_figures:    
    plot_options = {} # Using a dict to map descriptive titles to figure objects
    pac_figures = st.session_state.pac_figures
    # Loop through the nested figure structure to create the options
    for file_name, channel_figs in pac_figures.items():
        # 'figs' is a dictionary: {'plot_name': fig_object, ...}
        for channel_name, figs in channel_figs.items():
            # --- CHANGE IS HERE ---
            # Loop through both the plot_name (key) and fig (value)
            for plot_name, fig in figs.items():
                # No need to call get_suptitle(), plot_name is already the title
                plot_options[plot_name] = fig
            # --- END CHANGE ---

    st.subheader("📊 PAC Plots")

    # Create the multiselect widget
    selected_plots = st.multiselect(
        "Select plots to display:",
        options=list(plot_options.keys()),
        label_visibility="collapsed"
    )

    # Loop through the user's selections and display the plots
    if selected_plots:
        for plot_name in selected_plots:
            fig_to_display = plot_options[plot_name]
            # You had a 'width' parameter for st.container which is not valid.
            # Use columns or set the page layout to 'wide' for more space.
            with st.container(border=True):
                st.pyplot(fig_to_display)
                plt.close(fig_to_display)


########################## COHERENCE ##########################
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
    
    # st.subheader("Numerical Coherence Results")
    # st.json(st.session_state.coh_results)

    # Display plots using a multiselect
    plot_options = {}
    for file_figs in st.session_state.coh_figures.values():
        for pair_figs in file_figs.values():
            for plot_name, fig in pair_figs.items():
                plot_options[plot_name] = fig
    
    st.subheader("📊 Coherence Plots")
    selected_plots = st.multiselect(
        "Select coherence plots to display:",
        options=list(plot_options.keys()),
        key='coh_select'
    )
    if selected_plots:
        for plot_title in selected_plots:
 
            st.plotly_chart(plot_options[plot_title], use_container_width=True)

########################### COMUDOLOGRAM #######################
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
    plot_options = {}
    for file_figs in st.session_state.comod_figures.values():
        for chan_figs in file_figs.values():
            for plot_name, fig in chan_figs.items():
                plot_options[plot_name] = fig
    
    st.subheader("📊 Comodulogram Plots")
    selected_plots = st.multiselect(
        "Select comodulogram plots to display:",
        options=list(plot_options.keys()),
        key='comod_select'
    )
    if selected_plots:
        for plot_title in selected_plots:
            st.pyplot(plot_options[plot_title], use_container_width=True)     

############ Export ##############

#Merge results
merged_results = utils.merge_results_from_session()
if 'results' not in st.session_state:
    st.session_state.results = False



def export_to_excel(results_dict):
    """
    (Your existing function to export numerical results to Excel)
    This function should remain as it is.
    """
    # ... (your existing code for creating the excel file)
    # For example:
    output = io.BytesIO()
    if results_dict:
        # This is just a placeholder for your actual excel logic
        df = pd.DataFrame.from_dict({(i): results_dict[i] 
                                    for i in results_dict.keys()},
                                   orient='index')
        df.to_excel(output)
        output.seek(0)
        return output
    return None

st.session_state.results = analysis_utils.calculate_hierarchical_means(merged_results)
st.divider()
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
        
        c1,c2,c3,c4 = st.columns([1,1,1,5])

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














