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
