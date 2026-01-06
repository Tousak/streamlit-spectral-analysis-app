import streamlit as st
import numpy as np
import os
import glob
from src import utils


def PSD_settings():
    with st.expander("⚙️ PSD Parameters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("General Settings")
            
            norm_type = st.checkbox("Normalize Power Spectrum", value=False, on_change=utils.reset_values)
            c1, c2, c3 = st.columns(3)
            fs = c1.number_input("Sampling Frequency [Hz]", min_value=1, value=2000, on_change=utils.reset_values)
            F_h = c2.number_input("Max Frequency of Interest [Hz]", min_value=1, value=100, on_change=utils.reset_values)
            desired_resolution = c3.number_input("Frequency Resolution [Hz]", min_value=0.01, value=0.25, step=0.01, format="%.2f", on_change=utils.reset_values)
            

            st.subheader("Frequency Bands")
            c1, c2 = st.columns(2)
            delta = c1.slider("Delta Band [Hz]", 0.1, 20.0, (1.0, 4.0), 0.1, on_change=utils.reset_values)
            theta = c1.slider("Theta Band [Hz]", 0.1, 20.0, (4.0, 10.0), 0.1, on_change=utils.reset_values)
            alpha = c1.slider("Alpha Band [Hz]", 0.1, 30.0, (10.0, 14.0), 0.1, on_change=utils.reset_values)
            beta = c2.slider("Beta Band [Hz]", 0.1, 50.0, (14.0, 30.0), 0.1, on_change=utils.reset_values)
            gamma_l = c2.slider("Low Gamma Band [Hz]", 10.0, 100.0, (30.0, 55.0), 0.1, on_change=utils.reset_values)
            gamma_h = c2.slider("High Gamma Band [Hz]", 10.0, 150.0, (55.0, 100.0), 0.1, on_change=utils.reset_values)
            F_c = np.array([delta, theta, alpha, beta, gamma_l, gamma_h])

        with col2:
            st.subheader("Spectrogram Settings")
            c1, c2, c3 = st.columns(3)
            spec_stat = c1.checkbox("Calculate Spectrogram", value=False, on_change=utils.reset_values)
            
            
            desired_freq_res = c2.number_input("Spectrogram Freq. Res. [Hz]", min_value=0.1, value=1.0, step=0.1, on_change=utils.reset_values)
            desired_time_res = c3.number_input("Spectrogram Time Res. [s]", min_value=0.01, value=0.25, step=0.01, on_change=utils.reset_values)

            
            c1, c2 = st.columns(2)
            spec_F_range = c1.slider("Spectrogram Frequency Range [Hz]", 0, fs // 2, (0, 100), on_change=utils.reset_values)
            k_cax = c2.slider("Spectrogram Color Axis Range [dB]", -150, 0, (-80, -20),on_change=utils.reset_values)

            st.subheader("Output Settings")
            SEM_state = st.checkbox("Store SEM of PSD and PAC in Excel", value=True)

    return {
        "fs": fs,
        "F_h": F_h,
        "norm_type": norm_type,
        "F_c": F_c,
        "desired_resolution": desired_resolution,
        "spec_stat": spec_stat,
        "desired_freq_res": desired_freq_res,
        "desired_time_res": desired_time_res,
        "spec_F_range": spec_F_range,
        "k_cax": k_cax,
        "SEM_state": SEM_state
    }

# This function now needs the selections dictionary to know which channels are available
def PAC_settings(selections):
    with st.expander("⚙️ PAC Parameters", expanded=True):
        # --- Dynamic Band Definition ---
        st.subheader("1. Define Frequency Bands for Analysis")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Phase Bands**")
            phase_bands_str = st.text_input(
                "Enter Phase Bands (e.g., `4 8; 8 12`)",
                value="4 10", # Default value
                key="pac_phase_bands",
                on_change=utils.reset_values
            )
        with c2:
            st.markdown("**Amplitude Bands**")
            amp_bands_str = st.text_input(
                "Enter Amp Bands (e.g., `30 55; 55 100`)",
                value="30 55; 55 100", # Default value
                key="pac_amp_bands",
                on_change=utils.reset_values
            )

        # Parse the text inputs
        phase_freq_bands = utils.parse_time_ranges(phase_bands_str) or []
        amp_freq_bands = utils.parse_time_ranges(amp_bands_str) or []

        st.divider()

        # --- Cross-Channel Pairing Logic ---
        st.subheader("2. Configure Channel Pairing")
        c1,c2,c3,c4,c5,c6 = st.columns([1, 1, 1,1,1,1])

        use_cross_channel = c1.checkbox("Enable Between-Channels Pairing", key="pac_cross_channel_toggle", on_change=utils.reset_values)
        calculate_coherence = c2.checkbox("Calculate Coherence", key="coherence_toggle", on_change=utils.reset_values)
        


        # c2, c3,c4 = st.columns(3)
        if calculate_coherence:
            calculate_coheregram =c3.checkbox("Calculate Coheregram", value=False)
            if calculate_coheregram:
                coheregram_time_res = c4.number_input("Time Resolution [s]", value=1, min_value=1, step=1)
                coheregram_freq_res = c5.number_input("Freq Resolution [Hz]", value=1, min_value=1, step=1)
                max_F_coherergam = c6.number_input("Max Freq of interest [Hz]", value=100, min_value=10, step=1)
            else:
                coheregram_time_res, coheregram_freq_res, max_F_coherergam = False, False, False
        else:
            coheregram_time_res, coheregram_freq_res, max_F_coherergam, calculate_coheregram = False, False, False, False
        pairs = {}
        if use_cross_channel or calculate_coherence:
            # Iterate through each file that has channels selected
            for file_name, file_selections in selections.items():
                # Filter out the 'pac_config' key to get only channel names
                selected_channels = [ch for ch in file_selections.keys() if ch != 'pac_config']
                
                if not selected_channels: continue

                with st.container(border=True):
                    st.markdown(f"**Pairings for file: `{file_name}`**")
                    pairs[file_name] = {}
                    
                    for source_channel in selected_channels:
                        cols = st.columns([1, 2])
                        cols[0].markdown(f"**{utils.extract_short_name(source_channel)}** pairs with:")
                        
                        pairing_options = ["(None)"] + selected_channels
                        
                        paired_channel = cols[1].selectbox(
                            f"Select pair for {source_channel}",
                            options=pairing_options,
                            key=f"pair_select_{file_name}_{source_channel}",
                            label_visibility="collapsed",
                            format_func=utils.extract_short_name,
                            on_change=utils.reset_values
                        )
                        if paired_channel != "(None)":
                            pairs[file_name][source_channel] = paired_channel

        st.divider()

        # --- Other PAC and Comodulogram Settings (No Change) ---
        st.subheader("3. Other PAC & Comodulogram Settings")
        col3, col4 = st.columns(2)
        with col3:
            n_bins = st.number_input("Number of Bins for MI", min_value=2, value=18, on_change=utils.reset_values)
            st.markdown("**Sliding Window PAC**")
            c1, c2, c3 = st.columns(3)
            slide_state = c1.checkbox("Apply Sliding Window", value=False, on_change=utils.reset_values)


            sliding_window_duration_s = False

            if slide_state:
                sliding_window_duration_s = c2.number_input("Duration [s]", value=10.0, on_change=utils.reset_values)
                overlap_sliding = c3.slider("Overlap", 0.0, 1.0, 0.5, on_change=utils.reset_values)
            else:
                sliding_window_duration_s = False
                overlap_sliding = False
            
            


            

        with col4:
            comudolo_state = st.checkbox("Calculate Comodulogram", value=False, on_change=utils.reset_values)
            
            if comudolo_state:
                st.markdown("**Phase Axis Vector (for plot)**")
                c1,c2,c3 = st.columns(3)
                phase_vec_start = c1.number_input("Phase Freq Start [Hz]", value=0, on_change=utils.reset_values)
                phase_vec_dt = c2.number_input("Phase Freq Step [Hz]", min_value=1, value=2, on_change=utils.reset_values)
                phase_vec_end = c3.number_input("Phase Freq End [Hz]", value=100, on_change=utils.reset_values)

                st.markdown("**Amplitude Axis Vector (for plot)**")

                c1,c2,c3 = st.columns(3)
                amp_vec_start = c1.number_input("Amplitude Freq Start [Hz]", value=0,on_change=utils.reset_values)
                amp_vec_dt = c2.number_input("Amplitude Freq Step [Hz]", min_value=1, value=2,on_change=utils.reset_values)
                amp_vec_end = c3.number_input("Amplitude Freq End [Hz]", value=100,on_change=utils.reset_values)
                
            else:
                phase_vec_start = False
                phase_vec_dt  =False
                phase_vec_end = False
                amp_vec_start  =False
                amp_vec_dt = False
                amp_vec_end = False
                cax_cmd_vals = False

    # Return a dictionary with the new dynamic structure
    return {
        "PAC_state": True, # Assuming if this function is called, PAC is on
        "phase_freq_bands": phase_freq_bands,
        "amp_freq_bands": amp_freq_bands,
        "use_cross_channel": use_cross_channel,
        "calculate_coherence": calculate_coherence,
        "channel_pairs": pairs,
        "n_bins": n_bins,
        
        "slide_state": slide_state,
        "sliding_window_duration_s": sliding_window_duration_s,
        "overlap_sliding": overlap_sliding,
        

        "calculate_coheregram": calculate_coheregram,
        "coheregram_time_res": coheregram_time_res,
        "coheregram_freq_res": coheregram_freq_res,      
        "max_F_coherergam": max_F_coherergam,  

        "comudolo_state": comudolo_state,
        "phase_vec_start": phase_vec_start,
        "phase_vec_dt": phase_vec_dt,
        "phase_vec_end": phase_vec_end,
        "amp_vec_start": amp_vec_start,
        "amp_vec_dt": amp_vec_dt,
        "amp_vec_end": amp_vec_end,
    }
    



# def PAC_settings():
#     with st.expander("⚙️ PAC Parameters", expanded=True):
#         col3, col4 = st.columns(2)

#         with col3:
#             st.subheader("Phase-Amplitude Coupling (PAC) Settings")
#             PAC_state = st.checkbox("Calculate PAC", value=True)

#             c1,c2 = st.columns(2)
#             n_bins = c2.number_input("Number of Bins for MI", min_value=2, value=18, help="Default is 18 bins.")
#             phase_freq_band = c1.slider(
#                 "Phase Providing Band (e.g., Theta) [Hz]", 
#                 0.0, 50.0, (4.0, 10.0)
#             )
#             Amp_freq_band1 = c1.slider(
#                 "Amplitude Providing Band 1 (e.g., Gamma) [Hz]", 
#                 10.0, 150.0, (55.0, 80.0)
#             )
#             Amp_freq_band2 = c2.slider(
#                 "Amplitude Providing Band 2 (e.g., Gamma) [Hz]", 
#                 10.0, 150.0, (80.0, 100.0)
#             )
            
            
#             st.subheader("Sliding Window PAC")

#             c1,c2,c3 = st.columns(3)
#             slide_state = c1.checkbox("Apply Sliding Window PAC", value=False)
#             sliding_window_duration_s = c2.number_input("Sliding Window Duration [s]", min_value=0.1, value=10.0)
#             overlap_sliding = c3.slider("Sliding Window Overlap", 0.0, 1.0, 0.5, 0.05, format="%.2f")

#         with col4:
#             st.subheader("Comodulogram Settings")
#             comudolo_state = st.checkbox("Calculate Comodulogram", value=False)
            
            
#             st.markdown("**Phase Axis Vector (for plot)**")
#             c1,c2,c3 = st.columns(3)
#             phase_vec_start = c1.number_input("Phase Freq Start [Hz]", value=0)
#             phase_vec_dt = c2.number_input("Phase Freq Step [Hz]", min_value=1, value=2)
#             phase_vec_end = c3.number_input("Phase Freq End [Hz]", value=100)

#             st.markdown("**Amplitude Axis Vector (for plot)**")

#             c1,c2,c3 = st.columns(3)
#             amp_vec_start = c1.number_input("Amplitude Freq Start [Hz]", value=0)
#             amp_vec_dt = c2.number_input("Amplitude Freq Step [Hz]", min_value=1, value=2)
#             amp_vec_end = c3.number_input("Amplitude Freq End [Hz]", value=100)
            
#             st.markdown("**Comodulogram Color Axis**")
#             cax_cmd_vals = st.slider(
#                 "Color axis range `[x, y]`", 
#                 min_value=0.0, max_value=0.001, value=(0.0, 0.0005), 
#                 step=0.00001, format="%.5f"
#             )

#     return {
#         "PAC_state": PAC_state,
#         "phase_freq_band": phase_freq_band,
#         "Amp_freq_band1": Amp_freq_band1,
#         "Amp_freq_band2": Amp_freq_band2,
#         "n_bins": n_bins,
#         "slide_state": slide_state,
#         "sliding_window_duration_s": sliding_window_duration_s,
#         "overlap_sliding": overlap_sliding,
#         "comudolo_state": comudolo_state,
#         "phase_vec_start": phase_vec_start,
#         "phase_vec_dt": phase_vec_dt,
#         "phase_vec_end": phase_vec_end,
#         "amp_vec_start": amp_vec_start,
#         "amp_vec_dt": amp_vec_dt,
#         "amp_vec_end": amp_vec_end,
#         "cax_cmd_vals": cax_cmd_vals
#     }
    

