import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go

def plot_COH(coh_figures):
    # Display plots using a multiselect
    plot_options = {}
    for file_figs in coh_figures.values():
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
            fig = plot_options[plot_title]
            if isinstance(fig, plt.Figure):
                st.pyplot(fig, use_container_width=True)
            elif isinstance(fig, go.Figure):
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write(f"Unsupported plot type for '{plot_title}'.")