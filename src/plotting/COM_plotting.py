import streamlit as st

def plot_COM(comod_figures):
    plot_options = {}
    for file_figs in comod_figures.values():
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