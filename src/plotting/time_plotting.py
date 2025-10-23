import streamlit as st
import plotly.graph_objects as go
from src import file_loader, utils
import numpy as np



def plot_signal_from_selections(file_map: dict):
    """Plot signal based on user selections in the Streamlit app."""
    sig_col1, sig_col2, sig_col3 = st.columns(3)

    with sig_col1:
        # Get files that have actual time range selections
        valid_files_for_signal = {f: data for f, data in st.session_state.selections.items() if utils.has_non_empty_third_level({f: data})}
        if not valid_files_for_signal:
            st.info("Select files and configure channels and time ranges to see a signal.")
        else:
            selected_sig_file = st.selectbox("Select file:", list(valid_files_for_signal.keys()), key="sig_file")

    if 'selected_sig_file' in locals() and selected_sig_file:
        with sig_col2:
            channels_with_ranges = {c: tr for c, tr in st.session_state.selections[selected_sig_file].items() if tr}
            selected_sig_channel = st.selectbox("Select channel:", list(channels_with_ranges.keys()), key="sig_chan")

        if 'selected_sig_channel' in locals() and selected_sig_channel:
            with sig_col3:
                time_ranges = channels_with_ranges[selected_sig_channel]
                time_range_options = [f"{tr[0]}-{tr[1]}s" for tr in time_ranges]
                selected_sig_time_range_str = st.selectbox("Select time range:", time_range_options, key="sig_time")

            if selected_sig_time_range_str:
                start_str, end_str = selected_sig_time_range_str.replace('s', '').split('-')
                start_time, end_time = float(start_str), float(end_str)
                
                # Load data and plot
                try:
                    mat_data = file_loader.load_mat_file(file_map[selected_sig_file])
                    channel_data = mat_data[selected_sig_channel]
                    
                    times = channel_data['times'].flatten()
                    values = channel_data['values'].flatten()

                    # Find indices for slicing
                    start_idx = np.searchsorted(times, start_time, side='left')
                    end_idx = np.searchsorted(times, end_time, side='right')
                    
                    sliced_times = times[start_idx:end_idx]
                    sliced_values = values[start_idx:end_idx]
                    
                    fig_signal = go.Figure()
                    fig_signal.add_trace(go.Scatter(x=sliced_times, y=sliced_values, mode='lines'))
                    fig_signal.update_layout(
                        title=f'Signal: {selected_sig_channel} ({selected_sig_time_range_str})',
                        xaxis_title='Time [s]',
                        yaxis_title='Amplitude'
                    )
                    st.plotly_chart(fig_signal, use_container_width=True)

                except Exception as e:
                    st.error(f"Failed to load or plot signal: {e}")