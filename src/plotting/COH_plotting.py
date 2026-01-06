import streamlit as st
import plotly.graph_objects as go
from src.analysis_utils import AGGREGATION_KEYS

def plot_mean_coh_barchart(mean_metrics, sem_metrics, title_prefix):
    """
    Generates a Plotly bar chart for mean Coherence metrics with SEM.
    """
    band_labels = ['Delta', 'Theta', 'Alpha', 'Beta', 'Low Gamma', 'High Gamma']
    
    fig = go.Figure(data=go.Bar(
        x=band_labels,
        y=mean_metrics,
        error_y=dict(type='data', array=sem_metrics, visible=True),
        marker_color='rgba(31,119,180,0.6)'
    ))

    fig.update_layout(
        title=title_prefix,
        yaxis_title="Mean Coherence",
        xaxis_title="Frequency Band",
        yaxis_range=[0, 1.0], # Coherence is bounded [0, 1]
        template='plotly_white'
    )
    return fig

def plot_COH(coh_results, coh_figures):
    st.subheader("📊 Coherence Plots")

    if not coh_results:
        st.info("Calculate and process results to view Coherence plots.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "Detail Plots",
        "Mean Across Time Ranges",
        "Mean Across Pairs",
        "Mean Across Files"
    ])

    # --- TAB 1: Detail Plots ---
    with tab1:
        st.markdown("##### View detailed Coherence plots for a specific analysis.")
        plot_options = {}
        if coh_figures:
            for file_figs in coh_figures.values():
                for pair_figs in file_figs.values():
                    for plot_name, fig in pair_figs.items():
                        plot_options[plot_name] = fig
        
        if not plot_options:
            st.warning("No detail plots were generated. Please run the calculation.")
        else:
            selected_plots = st.multiselect(
                "Select coherence plots to display:",
                options=list(plot_options.keys()),
                key='coh_select'
            )
            if selected_plots:
                for plot_title in selected_plots:
                    st.plotly_chart(plot_options[plot_title], use_container_width=True)

    # --- TAB 2: Mean across time ranges ---
    with tab2:
        st.markdown("##### Average Coherence across time ranges for a specific pair.")
        
        # Filter files that have pair data (excluding aggregation keys)
        valid_files = [f for f, d in coh_results.items() if f not in AGGREGATION_KEYS and isinstance(d, dict)]
        
        col1, col2 = st.columns(2)
        with col1:
            file_for_mean_time = st.selectbox("Select a file:", valid_files, key="coh_file_mean_time")
        
        if file_for_mean_time:
            # Filter pairs that have 'mean_across_time'
            valid_pairs = [p for p, d in coh_results[file_for_mean_time].items() 
                           if p not in AGGREGATION_KEYS and isinstance(d, dict) and 'mean_across_time' in d]
            
            with col2:
                pair_for_mean_time = st.selectbox("Select a pair:", valid_pairs, key="coh_pair_mean_time")
            
            if pair_for_mean_time:
                mean_data = coh_results[file_for_mean_time][pair_for_mean_time]['mean_across_time']
                fig = plot_mean_coh_barchart(
                    mean_metrics=mean_data['means'],
                    sem_metrics=mean_data['errors'],
                    title_prefix=f"Mean Coherence: {pair_for_mean_time}"
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: Mean across pairs ---
    with tab3:
        st.markdown("##### Average Coherence across all pairs for a specific file.")
        
        # Filter files that have 'mean_across_pairs'
        valid_files_pairs = [f for f, d in coh_results.items() 
                             if f not in AGGREGATION_KEYS and isinstance(d, dict) and 'mean_across_pairs' in d]

        col1, _ = st.columns(2)
        with col1:
            file_for_mean_pairs = st.selectbox("Select a file:", valid_files_pairs, key="coh_file_mean_pairs")
        
        if file_for_mean_pairs:
            mean_data = coh_results[file_for_mean_pairs]['mean_across_pairs']
            fig = plot_mean_coh_barchart(
                mean_metrics=mean_data['means'],
                sem_metrics=mean_data['errors'],
                title_prefix=f"Mean Coherence Across Pairs: {file_for_mean_pairs}"
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- TAB 4: Grand Mean across all files ---
    with tab4:
        st.markdown("##### Grand average Coherence across all files.")
        
        grand_mean_data = coh_results.get('grand_mean')
        if not grand_mean_data:
            st.warning("Grand mean data not available. Please run calculations on multiple files or pairs.")
        else:
            fig = plot_mean_coh_barchart(
                mean_metrics=grand_mean_data['means'],
                sem_metrics=grand_mean_data['errors'],
                title_prefix="Grand Mean Coherence (All Files)"
            )
            st.plotly_chart(fig, use_container_width=True)