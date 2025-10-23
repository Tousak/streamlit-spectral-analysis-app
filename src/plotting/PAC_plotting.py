import streamlit as st
import matplotlib.pyplot as plt

def plot_PAC(pac_figures):
    plot_options = {} # Using a dict to map descriptive titles to figure objects
    # pac_figures = st.session_state.pac_figures
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