# Roadmap: Global Settings Feature

**Objective:** To add a feature that allows users to set analysis channels and time ranges for all loaded files at once, improving efficiency and reducing repetitive tasks.

This guide outlines a simplified, non-production implementation. It omits error handling for clarity.

---

### Step 1: Create the Global Settings UI in `src/file_loader.py`

This step involves adding the user interface elements that will control the global settings.

1.  **Add a Global Toggle:**
    *   At the very top of the `files_struturization` function, add a toggle switch to turn the global settings mode on or off.
    *   `global_settings_enabled = st.toggle("Set parameters for all files at once")`

2.  **Create a Conditional UI Block:**
    *   Use an `if global_settings_enabled:` block to show the global controls. The existing per-file logic will go in the `else` block later.

3.  **Build the Global Configuration Expander:**
    *   Inside the `if` block, create an expander: `with st.expander("Global Configuration", expanded=True):`.
    *   **Gather All Unique Channels:**
        *   Create an empty Python `set` called `all_channels`.
        *   Loop through each `file_item` in `st.session_state.file_list`.
        *   Load the file's contents: `mat_contents = load_mat_file(file_item)`.
        *   Find the channels in that file (e.g., variables matching `Ch\d+`).
        *   Add these channels to the `all_channels` set. The set will automatically handle duplicates.
    *   **Create Global Widgets:**
        *   Add a multiselect widget for channel selection, using the `all_channels` set as its `options`.
        *   Add a text input widget for the global time ranges.
        *   Add a button: `apply_to_all = st.button("Apply to All Files")`.

---

### Step 2: Implement the "Apply to All" Logic in `src/file_loader.py`

This step makes the "Apply to All" button functional.

1.  **Create a Button-Clicked Condition:**
    *   Inside the global settings expander, create an `if apply_to_all:` block.

2.  **Get User Input:**
    *   Inside this `if` block, get the list of channels selected in the global multiselect widget.
    *   Get the string from the global time range text input.

3.  **Process and Apply Settings:**
    *   Parse the time range string into a list of lists using `utils.parse_time_ranges`.
    *   Loop through each `file_item` in `st.session_state.file_list` to apply the settings to each file.
    *   **Inside the loop:**
        *   Get the `file_name`.
        *   Load the file's contents (`mat_contents`) to get its list of *specific* available channels.
        *   Reset the current selections for that file: `st.session_state.selections[file_name] = {}`.
        *   Start another loop through the globally selected channels.
        *   **Inside the inner loop:**
            *   Check if the global channel exists in this specific file's available channels.
            *   If it does, add the channel and the parsed global time ranges to the session state: `st.session_state.selections[file_name][global_channel] = parsed_global_ranges`.

---

### Step 3: Restructure the UI Flow in `src/file_loader.py`

This step ensures that either the global UI or the per-file UI is shown, but not both.

1.  **Add the `else` Block:**
    *   After the `if global_settings_enabled:` block, add an `else:` block.
    *   Move all the existing code for the per-file expanders (the original `for file_item in st.session_state.file_list:` loop and its contents) inside this `else` block.

This completes the basic implementation. When the toggle is ON, the user sees the global controls. When it's OFF, the user sees the original detailed per-file controls...
