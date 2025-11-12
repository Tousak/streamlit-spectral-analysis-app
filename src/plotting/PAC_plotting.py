import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.analysis_utils import AGGREGATION_KEYS

def plot_mean_pac_barchart(mean_metrics, sem_metrics, title_prefix):
    """
    Generates a Plotly figure with 3 subplots for mean PAC metrics with SEM.
    """
    metrics_labels = list(mean_metrics.keys()) # Should be ['MI', 'MVL', 'PLV']
    
    # Create a figure with 3 subplots in 1 row
    fig = make_subplots(rows=1, cols=3, subplot_titles=metrics_labels)

    # Define colors for each metric
    colors = ['rgba(222,45,38,0.6)', 'rgba(44,160,44,0.6)', 'rgba(31,119,180,0.6)']

    for i, metric in enumerate(metrics_labels):
        mean_val = mean_metrics.get(metric, 0)
        sem_val = sem_metrics.get(metric, 0)
        
        # Calculate dynamic y-axis range for this specific subplot
        max_val = mean_val + sem_val
        y_axis_upper_bound = max_val * 1.2 if max_val > 0 else 0.1 # Use a small default if 0

        fig.add_trace(
            go.Bar(
                x=[metric], 
                y=[mean_val], 
                error_y=dict(type='data', array=[sem_val], visible=True),
                name=metric,
                marker_color=colors[i]
            ),
            row=1, col=i+1
        )
        fig.update_yaxes(title_text="Value", range=[0, y_axis_upper_bound], row=1, col=i+1)

    fig.update_layout(
        title_text=title_prefix,
        showlegend=False,
        template='plotly_white'
    )
    return fig

def plot_PAC(pac_results, pac_figures):
    st.subheader("📊 PAC Analysis")

    if not pac_results:
        st.info("Calculate and process results to view PAC plots.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "Detail Plots",
        "Mean Across Time Ranges",
        "Mean Across Channels",
        "Mean Across Files"
    ])

    # --- TAB 1: Detail Plots ---
    with tab1:
        st.markdown("##### View detailed PAC plots for a specific analysis.")
        plot_options = {}
        if pac_figures:
            for file_name, channel_figs in pac_figures.items():
                for channel_name, figs in channel_figs.items():
                    for plot_name, fig in figs.items():
                        plot_options[plot_name] = fig
        
        if not plot_options:
            st.warning("No detail plots were generated. Please run the calculation.")
        else:
            selected_plots = st.multiselect(
                "Select plots to display:",
                options=list(plot_options.keys()),
            )
            if selected_plots:
                for plot_name in selected_plots:
                    fig_to_display = plot_options[plot_name]
                    with st.container(border=True):
                        st.pyplot(fig_to_display)
                        plt.close(fig_to_display)

    # --- Common data extraction for mean tabs ---
    # Get a list of all unique band combinations that have mean data
    all_bands = sorted(list(set(
        band for file in pac_results.values() if isinstance(file, dict)
        for chan in file.values() if isinstance(chan, dict)
        for band in chan.keys() if band not in AGGREGATION_KEYS
    )))

    # --- TAB 2: Mean across time ranges ---
    with tab2:
        st.markdown("##### Average PAC across time ranges for a specific channel and band.")
        if not all_bands:
            st.warning("No PAC data available to calculate means.")
        else:
            sel_col1, sel_col2, sel_col3 = st.columns(3)
            
            # Get files that have at least one channel with mean_across_time
            valid_files = [f for f, d in pac_results.items() if isinstance(d, dict) and any('mean_across_time' in v.get(band, {}) for v in d.values() if isinstance(v, dict) for band in all_bands)]
            
            with sel_col1:
                file_for_mean_time = st.selectbox("Select a file:", valid_files, key="pac_file_mean_time")

            if file_for_mean_time:
                # Get channels in the selected file that have mean_across_time data
                valid_channels = [c for c, d in pac_results[file_for_mean_time].items() if isinstance(d, dict) and any('mean_across_time' in v for v in d.values())]
                with sel_col2:
                    channel_for_mean_time = st.selectbox("Select a channel:", valid_channels, key="pac_chan_mean_time")
                
                if channel_for_mean_time:
                    # Get bands for the selected channel that have mean_across_time data
                    valid_bands = [b for b, d in pac_results[file_for_mean_time][channel_for_mean_time].items() if isinstance(d, dict) and 'mean_across_time' in d]
                    with sel_col3:
                        band_for_mean_time = st.selectbox("Select a band:", valid_bands, key="pac_band_mean_time")

                    if band_for_mean_time:
                        mean_data = pac_results[file_for_mean_time][channel_for_mean_time][band_for_mean_time].get('mean_across_time')
                        if mean_data:
                            fig = plot_mean_pac_barchart(
                                mean_metrics=mean_data['means'],
                                sem_metrics=mean_data['sems'],
                                title_prefix=f"Mean PAC: {channel_for_mean_time} ({band_for_mean_time})"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("Could not retrieve mean data for this selection.")

    # --- TAB 3: Mean across channels ---
    with tab3:
        st.markdown("##### Average PAC across channels for a specific file and band.")
        if not all_bands:
            st.warning("No PAC data available to calculate means.")
        else:
            sel_col1, sel_col2 = st.columns(2)
            
            # Get files that have mean_across_channels data
            valid_files = [f for f, d in pac_results.items() if isinstance(d, dict) and 'mean_across_channels' in d]
            
            with sel_col1:
                file_for_mean_chan = st.selectbox("Select a file:", valid_files, key="pac_file_mean_chan")

            if file_for_mean_chan:
                # Get bands that have been averaged across channels for this file
                valid_bands = list(pac_results[file_for_mean_chan].get('mean_across_channels', {}).keys())
                with sel_col2:
                    band_for_mean_chan = st.selectbox("Select a band:", valid_bands, key="pac_band_mean_chan")

                if band_for_mean_chan:
                    mean_data = pac_results[file_for_mean_chan]['mean_across_channels'].get(band_for_mean_chan)
                    if mean_data:
                        fig = plot_mean_pac_barchart(
                            mean_metrics=mean_data['means'],
                            sem_metrics=mean_data['sems'],
                            title_prefix=f"Mean PAC: {file_for_mean_chan} ({band_for_mean_chan})"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Could not retrieve mean data for this selection.")

    # --- TAB 4: Grand Mean across all files ---
    with tab4:
        st.markdown("##### Grand average PAC across all files for a specific band.")
        if not all_bands:
            st.warning("No PAC data available to calculate means.")
        else:
            grand_mean_data = pac_results.get('grand_mean')
            if not grand_mean_data:
                st.warning("Grand mean data not available. Please run calculations on multiple files or channels.")
            else:
                valid_bands = list(grand_mean_data.keys())
                band_for_grand_mean = st.selectbox("Select a band:", valid_bands, key="pac_band_grand_mean")

                if band_for_grand_mean:
                    mean_data = grand_mean_data.get(band_for_grand_mean)
                    if mean_data:
                        fig = plot_mean_pac_barchart(
                            mean_metrics=mean_data['means'],
                            sem_metrics=mean_data['sems'],
                            title_prefix=f"Grand Mean PAC ({band_for_grand_mean})"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Could not retrieve grand mean data for this selection.")
