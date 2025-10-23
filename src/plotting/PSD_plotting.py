import plotly.graph_objects as go
import numpy as np

def plot_mean_psd_with_sem(mean_power, sem_power, frequencies, title, f_h_max):
    """
    Generates a Plotly figure of the mean PSD with SEM represented as a shaded area.
    """
    # Ensure data are numpy arrays for filtering
    mean_power = np.array(mean_power)
    sem_power = np.array(sem_power)
    frequencies = np.array(frequencies)

    # Filter data up to the maximum frequency F_h
    idx = np.where(frequencies <= f_h_max)
    frequencies = frequencies[idx]
    mean_power = mean_power[idx]
    sem_power = sem_power[idx]

    fig = go.Figure()

    # Define the upper and lower bounds for the shaded SEM area
    upper_bound = mean_power + sem_power
    lower_bound = mean_power - sem_power
    
    # The shaded area should not go below zero on a log plot
    lower_bound = np.maximum(lower_bound, 1e-12) 


    # Add the SEM shaded area trace
    # It's drawn by plotting the upper bound, then the lower bound in reverse
    fig.add_trace(go.Scatter(
        x=np.concatenate([frequencies, frequencies[::-1]]),
        y=np.concatenate([upper_bound, lower_bound[::-1]]),
        fill='toself',
        fillcolor='rgba(0,176,246,0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="none",
        name='SEM'
    ))

    # Add the mean power line trace
    fig.add_trace(go.Scatter(
        x=frequencies,
        y=mean_power,
        mode='lines',
        line=dict(color='rgba(0,176,246,1)'),
        name='Mean PSD'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Frequency [Hz]',
        yaxis_title='Power [V^2/Hz]',
        yaxis_type="log",
        showlegend=True,
        template='plotly_white'
    )
    return fig

def plot_mean_band_power_with_sem(mean_bands, sem_bands, title):
    """
    Generates a Plotly bar chart for mean band power with SEM as error bars.
    """
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    fig = go.Figure(data=go.Bar(
        x=band_labels,
        y=mean_bands,
        error_y=dict(type='data', array=sem_bands, visible=True),
        marker_color='rgba(0,176,246,0.6)'
    ))
    fig.update_layout(
        title=title,
        yaxis_title='Power [V^2/Hz]',
        xaxis_title='Frequency Band',
        template='plotly_white'
    )
    return fig


import streamlit as st
import re
def plot_PSDs(params):
    st.subheader("📊 PSD Analysis")

    psd_results = st.session_state.get('psd_results', {})
    psd_figures = st.session_state.get('psd_figures', {}) 

    if not psd_results:
        st.info("Calculate and process results to view PSD plots.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "Single Time Range",
            "Mean Across Time Ranges",
            "Mean Across Channels",
            "Mean Across Files"
        ])

        # --- TAB 1: Single Time Range ---
        with tab1:
            st.markdown("##### View PSD for a specific file, channel, and time range.")
            sel_col1, sel_col2, sel_col3 = st.columns(3)

            if not psd_figures:
                st.warning("No figures were generated. Please run the calculation.")
            else:
                valid_files = [f for f in psd_figures.keys() if psd_figures.get(f)]
                if not valid_files:
                    st.warning("No files with PSD figures found.")
                else:
                    with sel_col1:
                        selected_file = st.selectbox("Select a file:", valid_files, key="psd_file_select")
                    
                    valid_channels = [c for c in psd_figures[selected_file].keys() if psd_figures[selected_file].get(c)] if selected_file else []
                    if not valid_channels:
                        st.warning("No channels with PSD figures found for this file.")
                    else:
                        with sel_col2:
                            selected_channel = st.selectbox("Select a channel:", valid_channels, key="psd_channel_select")
                        
                        time_ranges = sorted(list(set(
                            re.search(r'(\d{1,4}\.?\d*-\d{1,4}\.?\d*s)', name).group(1)
                            for name in psd_figures[selected_file][selected_channel].keys() if re.search(r'(\d{1,4}\.?\d*-\d{1,4}\.?\d*s)', name)
                        ))) if selected_channel else []

                        if not time_ranges:
                            st.warning("No time ranges found for this channel.")
                        else:
                            with sel_col3:
                                selected_time_range = st.selectbox("Select a time range:", time_ranges, key="psd_time_select")
                            
                            st.markdown(f"**Displaying:** `{selected_file} -> {selected_channel} ({selected_time_range})`")
                            plot_col1, plot_col2 = st.columns(2)

                            psd_plot_name = f"PSD | {selected_channel} ({selected_time_range})"
                            if psd_plot_name in psd_figures[selected_file][selected_channel]:
                                plot_col1.plotly_chart(psd_figures[selected_file][selected_channel][psd_plot_name], use_container_width=True)
                            
                            band_plot_name = f"Band Power | {selected_channel} ({selected_time_range})"
                            if band_plot_name in psd_figures[selected_file][selected_channel]:
                                plot_col2.plotly_chart(psd_figures[selected_file][selected_channel][band_plot_name], use_container_width=True)

        # --- TAB 2: Mean across time ranges ---
        with tab2:
            st.markdown("##### View the average PSD across all time ranges for a specific channel.")
            sel_col1, sel_col2, _ = st.columns(3)
            
            valid_files_mean_time = [f for f, d in psd_results.items() if isinstance(d, dict) and any('mean_across_time' in v for v in d.values() if isinstance(v, dict))]
            if not valid_files_mean_time:
                st.warning("No data available for mean across time ranges. Please run calculations.")
            else:
                with sel_col1:
                    file_for_mean_time = st.selectbox("Select a file:", valid_files_mean_time, key="psd_file_mean_time")
                
                valid_channels_mean_time = [c for c, d in psd_results[file_for_mean_time].items() if isinstance(d, dict) and 'mean_across_time' in d] if file_for_mean_time else []
                if not valid_channels_mean_time:
                    st.warning("No channels with mean data found for this file.")
                else:
                    with sel_col2:
                        channel_for_mean_time = st.selectbox("Select a channel:", valid_channels_mean_time, key="psd_chan_mean_time")

                    mean_data = psd_results[file_for_mean_time][channel_for_mean_time].get('mean_across_time', {}) if channel_for_mean_time else {}
                    if not mean_data:
                        st.error("Could not retrieve mean data for this selection.")
                    else:
                        plot_col1, plot_col2 = st.columns(2)
                        
                        full_psd_data = mean_data.get('full_psd')
                        if full_psd_data:
                            fig_mean_psd = plot_mean_psd_with_sem(
                                mean_power=full_psd_data['mean_power'], sem_power=full_psd_data['sem_power'],
                                frequencies=full_psd_data['frequencies'], title=f"Mean PSD: {channel_for_mean_time}", f_h_max=params['F_h']
                            )
                            plot_col1.plotly_chart(fig_mean_psd, use_container_width=True)

                        band_power_data = mean_data.get('band_power')
                        if band_power_data:
                            fig_mean_band = plot_mean_band_power_with_sem(
                                mean_bands=band_power_data['means'], sem_bands=band_power_data['errors'], title=f"Mean Band Power: {channel_for_mean_time}"
                            )
                            plot_col2.plotly_chart(fig_mean_band, use_container_width=True)

        # --- TAB 3: Mean across channels ---
        with tab3:
            st.markdown("##### View the average PSD across all selected channels for a specific file.")
            sel_col1, _, _ = st.columns(3)
            
            valid_files_mean_chan = [f for f, d in psd_results.items() if isinstance(d, dict) and 'mean_across_channels' in d]
            if not valid_files_mean_chan:
                st.warning("No data available for mean across channels. Please run calculations.")
            else:
                with sel_col1:
                    file_for_mean_chan = st.selectbox("Select a file:", valid_files_mean_chan, key="psd_file_mean_chan")
                
                mean_data = psd_results[file_for_mean_chan].get('mean_across_channels', {}) if file_for_mean_chan else {}
                if not mean_data:
                    st.error("Could not retrieve mean data for this selection.")
                else:
                    plot_col1, plot_col2 = st.columns(2)
                    
                    full_psd_data = mean_data.get('full_psd')
                    if full_psd_data:
                        fig_mean_psd = plot_mean_psd_with_sem(
                            mean_power=full_psd_data['mean_power'], sem_power=full_psd_data['sem_power'],
                            frequencies=full_psd_data['frequencies'], title=f"Mean PSD: {file_for_mean_chan}", f_h_max=params['F_h']
                        )
                        plot_col1.plotly_chart(fig_mean_psd, use_container_width=True)
                    
                    band_power_data = mean_data.get('band_power')
                    if band_power_data:
                        fig_mean_band = plot_mean_band_power_with_sem(
                            mean_bands=band_power_data['means'], sem_bands=band_power_data['errors'], title=f"Mean Band Power: {file_for_mean_chan}"
                        )
                        plot_col2.plotly_chart(fig_mean_band, use_container_width=True)

        # --- TAB 4: Grand Mean across all files ---
        with tab4:
            st.markdown("##### View the grand average PSD across all selected files.")
            
            grand_mean_data = psd_results.get('grand_mean')
            if not grand_mean_data:
                st.warning("Grand mean data not available. Please run calculations on multiple files.")
            else:
                plot_col1, plot_col2 = st.columns(2)
                
                full_psd_data = grand_mean_data.get('full_psd')
                if full_psd_data:
                    fig_grand_mean_psd = plot_mean_psd_with_sem(
                        mean_power=full_psd_data['mean_power'], sem_power=full_psd_data['sem_power'],
                        frequencies=full_psd_data['frequencies'], title="Grand Mean PSD Across All Files", f_h_max=params['F_h']
                    )
                    plot_col1.plotly_chart(fig_grand_mean_psd, use_container_width=True)

                band_power_data = grand_mean_data.get('band_power')
                if band_power_data:
                    fig_grand_mean_band = plot_mean_band_power_with_sem(
                        mean_bands=band_power_data['means'], sem_bands=band_power_data['errors'], title="Grand Mean Band Power Across All Files"
                    )
                    plot_col2.plotly_chart(fig_grand_mean_band, use_container_width=True)