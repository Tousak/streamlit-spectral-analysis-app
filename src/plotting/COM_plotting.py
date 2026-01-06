import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from src.analysis_utils import AGGREGATION_KEYS

def _plot_mean_comodulogram(comodulogram, title, params):
    """
    Helper to plot a mean comodulogram matrix.
    """
    comodulogram = np.array(comodulogram)
    
    # Reconstruct axes
    phase_start = params.get('phase_vec_start', 0.1)
    if phase_start <= 0: phase_start = 0.1
    
    amp_start = params.get('amp_vec_start', 0.1)
    if amp_start <= 0: amp_start = 0.1

    low_fq_range = np.arange(
        phase_start, 
        params['phase_vec_end'] + params['phase_vec_dt'], 
        params['phase_vec_dt']
    )
    high_fq_range = np.arange(
        amp_start, 
        params['amp_vec_end'] + params['amp_vec_dt'], 
        params['amp_vec_dt']
    )

    # Ensure dimensions match (trim if necessary, though they should match)
    # Comodulogram shape: (len(low_fq), len(high_fq)) or vice versa?
    # pactools: (n_low, n_high) usually. But check Comodulogram.py logic:
    # contourf(low_fq_range, high_fq_range, comodulogram, ...)
    # If shapes mismatch, we might need to adjust.
    # Usually pactools output matches the ranges provided.
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    if comodulogram.size > 0:
        vmin = np.nanmin(comodulogram)
        vmax = np.nanmax(comodulogram)
        if np.isclose(vmin, vmax): vmax = vmin + 1e-9
    else:
        vmin, vmax = 0, 1

    try:
        contour = ax.contourf(
            low_fq_range, 
            high_fq_range, 
            comodulogram.T, # Transpose to match (Y, X) => (Amp, Phase)
            levels=40, 
            cmap='jet', 
            vmin=vmin, 
            vmax=vmax
        )
        fig.colorbar(contour, ax=ax, label='Modulation Index')
    except Exception as e:
        st.error(f"Error plotting mean comodulogram: {e}")
        return None

    ax.set_title(title)
    ax.set_xlabel('Phase Frequency (Hz)')
    ax.set_ylabel('Amplitude Frequency (Hz)')
    fig.tight_layout()
    return fig

def plot_COM(comod_results, comod_figures, params):
    st.subheader("📊 Comodulogram Plots")

    if not comod_results:
        st.info("Calculate results to view Comodulogram plots.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "Detail Plots",
        "Mean Across Time Ranges",
        "Mean Across Channels",
        "Mean Across Files"
    ])

    # --- TAB 1: Detail Plots ---
    with tab1:
        plot_options = {}
        if comod_figures:
            for file_figs in comod_figures.values():
                for chan_figs in file_figs.values():
                    for plot_name, fig in chan_figs.items():
                        plot_options[plot_name] = fig
        
        if not plot_options:
            st.warning("No detail plots generated.")
        else:
            selected_plots = st.multiselect(
                "Select comodulogram plots to display:",
                options=list(plot_options.keys()),
                key='comod_select'
            )
            if selected_plots:
                for plot_title in selected_plots:
                    st.pyplot(plot_options[plot_title], use_container_width=True)

    # --- TAB 2: Mean Across Time ---
    with tab2:
        valid_files = [f for f, d in comod_results.items() if f not in AGGREGATION_KEYS and isinstance(d, dict)]
        col1, col2 = st.columns(2)
        with col1:
            file_time = st.selectbox("Select File:", valid_files, key="com_file_time")
        
        if file_time:
            valid_chans = [c for c, d in comod_results[file_time].items() 
                           if c not in AGGREGATION_KEYS and isinstance(d, dict) and 'mean_across_time' in d]
            with col2:
                chan_time = st.selectbox("Select Channel/Pair:", valid_chans, key="com_chan_time")
            
            if chan_time:
                mean_matrix = comod_results[file_time][chan_time]['mean_across_time']['mean']
                fig = _plot_mean_comodulogram(mean_matrix, f"Mean Comodulogram: {chan_time}", params)
                if fig: st.pyplot(fig, use_container_width=True)

    # --- TAB 3: Mean Across Channels ---
    with tab3:
        valid_files_chan = [f for f, d in comod_results.items() 
                            if f not in AGGREGATION_KEYS and isinstance(d, dict) and 'mean_across_channels' in d]
        col1, _ = st.columns(2)
        with col1:
            file_chan = st.selectbox("Select File:", valid_files_chan, key="com_file_chan")
        
        if file_chan:
            mean_matrix = comod_results[file_chan]['mean_across_channels']['mean']
            fig = _plot_mean_comodulogram(mean_matrix, f"Mean Comodulogram Across Channels: {file_chan}", params)
            if fig: st.pyplot(fig, use_container_width=True)

    # --- TAB 4: Grand Mean ---
    with tab4:
        grand_mean_data = comod_results.get('grand_mean')
        if grand_mean_data:
            mean_matrix = grand_mean_data['mean']
            fig = _plot_mean_comodulogram(mean_matrix, "Grand Mean Comodulogram (All Files)", params)
            if fig: st.pyplot(fig, use_container_width=True)
        else:
            st.warning("Grand mean not available.")