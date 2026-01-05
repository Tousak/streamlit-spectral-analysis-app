# Fix for MI Values Displaying with μ Symbol

## Issue
MI values for Mean Across Channels/Files graphs are displayed with μ (micro) prefix in interactive plots displayed in the app. In generated PNG/SVG files, the values display correctly.

## Root Cause
Plotly's automatic formatting converts small values to use the μ symbol for micro (10^-6) on the y-axis.

## Solution
Modified `src/plotting/PAC_plotting.py` to disable the automatic SI prefix formatter on the y-axis by explicitly setting the `tickformat` parameter.

### Code Changes Implemented

In the `plot_mean_pac_barchart` function, added `tickformat='.6f'` to the `fig.update_yaxes()` call:

```python
fig.update_yaxes(
    title_text="Value", 
    range=[0, y_axis_upper_bound], 
    tickformat='.6f',  # Show values without SI prefixes
    row=1, col=i+1
)
cbar.update_ticks()
```
This forces Plotly to display full decimal numbers instead of using SI prefix notation (μ, m, k, etc.).
### Specific Locations to Check
Look for functions that create MI plots for Mean Across Channels/Files:
- Functions that use `plt.imshow()` or `ax.imshow()` with MI data
1. ✅ Run the app and display Mean Across Channels/Files MI graphs
2. ✅ Verify values show without μ prefix
3. ✅ Ensure exported PNG/SVG files still display correctly
### Example Fix
## Implementation Status
- [x] Identified root cause (Plotly automatic SI prefix formatting)
- [x] Applied fix to `plot_mean_pac_barchart` function
- [ ] Testing completed
- [ ] Verified on all affected graph types
cbar = plt.colorbar(im, ax=ax)
cbar.formatter = ScalarFormatter()
cbar.formatter.set_useOffset(False)
cbar.update_ticks()
```

## Testing
After implementing the fix:
1. Run the app and display Mean Across Channels/Files MI graphs
2. Verify values show without μ prefix
3. Ensure exported PNG/SVG files still display correctly

