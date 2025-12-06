import re
import os
import numpy as np
import streamlit as st
import scipy.signal
import h5py
import glob
from src import utils


# --- ADD THIS HELPER FUNCTION HERE ---
def clean_mat_struct(struct):
    """
    Recursively cleans a loaded MATLAB struct from scipy.io.loadmat.
    Converts structured arrays to dictionaries and removes singleton dimensions.
    """
    if isinstance(struct, np.ndarray) and struct.dtype.names:
        # It's a structured array, convert to dict
        new_dict = {}
        for field_name in struct.dtype.names:
            # Recursively clean each field
            new_dict[field_name] = clean_mat_struct(struct[field_name][0, 0])
        return new_dict
    elif isinstance(struct, np.ndarray) and struct.size == 1:
        # It's a single value wrapped in an array, extract it
        return struct.item()
    else:
        # It's a regular value or array, return as is
        return struct
    


def read_hdf5_item(item):
    """
    Recursively reads an item from an HDF5 file loaded with h5py.
    """
    if isinstance(item, h5py.Group):
        # It's a group (like a MATLAB struct), convert to dict
        return {key: read_hdf5_item(value) for key, value in item.items()}
    elif isinstance(item, h5py.Dataset):
        # It's a dataset (like a MATLAB array), get its value
        # The [()] syntax is a common way to read the full dataset value
        return item[()]
    else:
        return item

@st.cache_data
def load_mat_file(file_item):
    """
    A cached function to load a .mat file robustly.
    It handles both old and new (v7.3 HDF5) formats.
    Streamlit's caching will only run this function if the input 'file_item' has changed.
    """
    print(f"--- Loading file from disk: {getattr(file_item, 'name', file_item)} ---") # For debugging
    mat_contents = None
    try:
        # First, try the standard loader for older .mat files
        mat_contents = scipy.io.loadmat(file_item)
    except NotImplementedError:
        # If it's a v7.3 file, use h5py as a fallback
        try:
            with h5py.File(file_item, 'r') as f:
                mat_contents = read_hdf5_item(f)
        except Exception as h5_error:
            st.error(f"Failed to read HDF5 file: {h5_error}")
    except Exception as e:
        st.error(f"Could not read file. Error: {e}")
        
    return mat_contents 

# Add this new function to your file
def handle_channel_selection_change(file_name):
    """
    This function is called whenever a multiselect's value changes.
    It updates the main selections dictionary to add new channels or remove old ones.
    """
    # Get the list of currently selected channels from the widget's state
    selected_channels = st.session_state[f"multiselect_{file_name}"]
    
    # Add newly selected channels to our main selections dictionary
    for channel in selected_channels:
        if channel not in st.session_state.selections[file_name]:
            st.session_state.selections[file_name][channel] = []
            
    # Remove deselected channels
    for channel in list(st.session_state.selections[file_name].keys()):
        if channel not in selected_channels:
            del st.session_state.selections[file_name][channel]
    utils.reset_values


# Replace your old function with this new version
def files_struturization():
    if 'selections' not in st.session_state:
        st.session_state.selections = {}

    if st.session_state.file_list:
        st.info("Select channels and define time ranges for each file you want to process.")
        
        global_settings_enabled = st.toggle("Set parameters for all files at once")

        if global_settings_enabled:
            with st.expander("Global Configuration", expanded=True):
                # Step 1: Gather all unique SHORT channel names for the UI
                all_short_channels = set()
                all_long_channels = []
                for file_item in st.session_state.file_list:
                    mat_contents = load_mat_file(file_item)
                    if mat_contents:
                        # Find all relevant channel keys in the file
                        channels_in_file = [var for var in mat_contents.keys() if re.search(r"Ch\d{1,2}", var)]
                        all_long_channels.extend(channels_in_file)

                # Create a unique set of the short names for the UI
                if all_long_channels:
                    all_short_channels = {utils.extract_short_name(c) for c in all_long_channels}
                
                sorted_short_channels = sorted(list(all_short_channels))
                
                # The multiselect now uses the unique short names
                global_selected_short_channels = st.multiselect(
                    "Select Global Channels",
                    options=sorted_short_channels,
                )
                
                global_time_ranges_str = st.text_input("Enter Global Time Ranges (e.g., 10 20.5; 30 45)")
                
                apply_to_all = st.button("Apply to All Files")

                if apply_to_all:
                    parsed_global_ranges = utils.parse_time_ranges(global_time_ranges_str)
                    if parsed_global_ranges is not None:
                        # Step 2: Update apply logic to map short names back to long names
                        for file_item in st.session_state.file_list:
                            file_name = os.path.basename(file_item) if isinstance(file_item, str) else file_item.name
                            
                            mat_contents = load_mat_file(file_item)
                            if not mat_contents:
                                continue

                            st.session_state.selections[file_name] = {}
                            
                            # Iterate through the actual (long) channel names in the file
                            for long_channel_name in mat_contents.keys():
                                # Get its short name
                                short_name = utils.extract_short_name(long_channel_name)
                                # If its short name is in the user's global selection, apply the setting
                                if short_name in global_selected_short_channels:
                                    st.session_state.selections[file_name][long_channel_name] = parsed_global_ranges

                        st.success("Global settings applied to all applicable files!")
                        st.rerun()
                    else:
                        st.error("Invalid format for global time ranges.")

        else:
            for file_item in st.session_state.file_list:
                if isinstance(file_item, str):
                    file_name = os.path.basename(file_item)
                else:
                    file_name = file_item.name

                with st.expander(f"⚙️ Configure File: **{file_name}**"):
                    mat_contents = load_mat_file(file_item)
                    
                    if mat_contents is None:
                        st.error("File could not be loaded.")
                        continue

                    available_channels = sorted([
                        var for var in mat_contents.keys() if re.search(r"Ch\d{1,2}", var)
                    ])

                    if not available_channels:
                        st.warning("No channels matching the pattern 'ChX' or 'ChXX' found.")
                        continue

                    st.session_state.selections.setdefault(file_name, {})
                    
                    st.multiselect(
                        "Define Channels",
                        options=available_channels,
                        default=list(st.session_state.selections[file_name].keys()),
                        key=f"multiselect_{file_name}",
                        on_change=handle_channel_selection_change,
                        args=(file_name,),
                        format_func=utils.extract_short_name
                    )
                    
                    for channel_name in st.session_state.selections[file_name]:
                        with st.container(border=True):
                            st.markdown(f"**Time Ranges for `{utils.extract_short_name(channel_name)}`** || Example: `10 20.5; 30 45`")

                            default_text = "; ".join([f"{r[0]} {r[1]}" for r in st.session_state.selections[file_name][channel_name]])

                            text_input = st.text_input(
                                "Time ranges:",
                                value=default_text,
                                key=f"text_{file_name}_{channel_name}",
                                label_visibility='collapsed',
                                on_change = utils.reset_values
                            )
                            
                            if text_input:
                                parsed_ranges = utils.parse_time_ranges(text_input)
                                if parsed_ranges is not None:
                                    st.session_state.selections[file_name][channel_name] = parsed_ranges
                                else:
                                    st.error("Invalid format. Use space-separated numbers and semicolon-separated pairs.", icon="❗")
                            else:
                                st.session_state.selections[file_name][channel_name] = []
    else:
        st.warning("Please upload files or load from a folder to begin.")


def file_list_creator():
    st.session_state.file_list = []
    # Initialize a session state variable to hold the files

    col1, col2 = st.columns(2)

    # --- COLUMN 1: File Uploader ---
    with col1:
        st.subheader("Option A: Upload Files")
        uploaded_files = st.file_uploader(
            "Select one or more .mat files.",
            type=['mat'],
            accept_multiple_files=True
        )
        if uploaded_files:
            # If user uploads files, this becomes the definitive list
            st.session_state.file_list = uploaded_files
            st.success("Files uploaded successfully!")
        else:
            st.session_state.file_list = False

    # --- COLUMN 2: Folder Picker (Path Input) ---
    with col2:
        st.subheader("Option B: Load from Folder")
        
        folder_path = st.text_input("Paste the absolute path to your folder:")
        
        if st.button("Load files from folder"):
            if folder_path and os.path.isdir(folder_path):
                # Use glob to find all .mat files in the given path
                mat_files_paths = glob.glob(os.path.join(folder_path, '*.mat'))
                if mat_files_paths:
                    st.session_state.file_list = mat_files_paths
                    st.success(f"Found {len(mat_files_paths)} `.mat` files.")
                else:
                    st.error(f"No `.mat` files found in '{folder_path}'")
            else:
                st.error("Invalid path. Please provide a valid folder path.")


    # --- Unify and display the list of files to be processed ---
    # The rest of your script will now use st.session_state.file_list
    if 'uploaded_files' in locals():
        del uploaded_files # Clean up to avoid confusion        