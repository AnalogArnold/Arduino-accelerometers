##################################################################################################################
#
# Class AccelerometerReaderGUI creates a simple graphical user interface to enable the user to easily communicate with
# the Adafruit board and process the data without having to look at the code. It contains the GUI structure, uses
# TCPClient class to establish a connection with the board, and the SensorDataManager class to process the data.
# It also contains a few utility functions to plot the real-time data using the GUI engine.
#
# Version: 2.4 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################

import tkinter.filedialog
import threading
import dearpygui.dearpygui as dpg
import time
import os
from math import ceil
import modules.gui_style as style
from modules.sensor_data_manager import SensorDataManager, post_process_dataframe
from modules.tcp_client import TCPClient, get_current_network
from modules.global_settings import *

class AccelerometerReaderGUI:
    def __init__(self):
        self.data_manager = SensorDataManager()
        self.tcp_client = TCPClient(self.data_manager)
        self.save_directory_path = None
        self.open_directory_path = None
        self.stop_plot_event = threading.Event()
        self.stop_plot_event.set()
        self.live_plotting_thread = None
        self.post_processing_sensors = []
        # Set-up gui upon initialization
        self.setup_gui()

    def setup_gui(self):
        """Sets up the GUI for the accelerometer reader."""
        dpg.create_context()
        dpg.create_viewport(title='Accelerometer controller', width=1300, height=800)
        self._create_main_window()
        style.setup_gui_theme()
        dpg.set_primary_window("accelerometer_control", True)
        dpg.setup_dearpygui()
        # Reset the sensors when closing the program window
        dpg.set_exit_callback(callback=lambda: self.tcp_client.reset_sensors())
        dpg.show_viewport()
        # Check network connection before the user does anything else
        get_current_network()

    def _create_main_window(self):
        """Creates the primary window for the GUI."""
        with dpg.window(label="accelerometer control", tag="accelerometer_control"):
            # Menu bar items
            with dpg.group(tag="menu bar"):
                dpg.add_text("Arduino accelerometer controller", tag="program_header") # Header
                # Board connection control panel
                with dpg.group(horizontal=True):
                    # Add text instead of labels because labels are always on the left, and it does not look intuitive.
                    # Board host is the IPv4 DNS address of SoftAP (software enabled access point a.k.a. virtual router)
                    dpg.add_text("Board Host")
                    dpg.add_input_text(default_value="192.168.4.1", tag="host", width=150)
                    # Port number for the HTTP server running on the board.
                    dpg.add_text("Port")
                    dpg.add_input_text(default_value="8080", tag="port", width=80)
                    dpg.add_text("Datarate")
                    dpg.add_combo(["1 Hz", "10 Hz", "25 Hz", "50 Hz", "100 Hz"],
                                  default_value="1 Hz", tag="datarate_choice", width=100,
                                  callback=lambda: self._command_callback(None, "SET_DATARATE"))
                    dpg.add_text("Range")
                    dpg.add_combo(["2 G", "4 G", "8 G", "16 G"],
                                  default_value="2 G", tag="range_choice", width=55,
                                  callback=lambda: self._command_callback(None, "SET_RANGE"))
                    dpg.add_button(label="Connect", tag="connect_button", callback=self._connect_callback)
                    dpg.add_button(label="Disconnect", tag="disconnect_button", callback=self._disconnect_callback)
                with dpg.group(horizontal=True):
                    dpg.add_text("Connection status: Not connected", tag="connection_status")
                    dpg.add_text("", tag="connection_warning",  color=(178, 34, 34), wrap=600, indent=240)
                with dpg.tab_bar(label="tab_bar"):
                    dpg.add_tab(label="Data acquisition", tag="data_acquisition_tab")
                    dpg.add_tab(label="Post-processing", tag="post_processing_tab")
            self._create_data_acquisition_tab()
            self._create_post_processing_tab()
            # Status bar to communicate with the user rather than have to look at the Python IDE
            dpg.add_separator()
            dpg.add_text("Status:", tag="status_header")
            dpg.add_text("Ready", tag=STATUS)

    def _create_data_acquisition_tab(self):
        """Creates the contents of the data acquisition tab."""
        with dpg.group(parent="data_acquisition_tab"):
            dpg.add_text("Data acquisition from the sensors", tag="data_log_header")
            # Control buttons on the menu bar
            # Control buttons on the menu bar
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start recording", callback=lambda: self._command_callback(None, "START"))
                dpg.add_button(label="Stop recording", callback=lambda: self._command_callback(None, "STOP"))
                dpg.add_button(label="Show live data", callback=self._show_live_plot_window)
                dpg.add_button(label="Process/export data", callback=self._show_processing_window)
                dpg.add_button(label="Clear data", callback=self._clear_data_callback)

            # Data display
            # Table headers for the incoming data which is always visible above the table for readability.
            with dpg.table(header_row=False, tag="headers", width=680):
                dpg.add_table_row(tag="table_row_1")
                labels = ["Sensor number", "X [m/s^2]", "Y [m/s^2]", "Z [m/s^2]", "Timestamp [ms]"]
                # Create columns for the header row
                for i in range(len(labels)):
                    dpg.add_table_column()
                # Append text to the header row
                with dpg.table_row():
                    for label in labels:
                        dpg.add_text(label)

            # Table displaying the incoming data
            with dpg.group(horizontal=True):
                # Define the child window with a predefined size - necessary to keep the table with incoming data the
                # same size rather than stretching the main window indefinitely.
                with dpg.child_window(width=700, height=400):
                    with dpg.table(tag=DATA_LOG): # setting header_row = False causes the data not to be displayed?
                        for _ in range(5):
                            dpg.add_table_column()
                # Display information about detected sensors and intervals next to the data log
                with dpg.group():
                    dpg.add_text("Detected sensors:", tag="detected_sensors_header")
                    with dpg.table(header_row=False, tag="detected_sensors_table", width=130):
                        for i in range(4):
                            dpg.add_table_column(label=f"sensor_column_{str(i)}")
                        for i,j in zip([0,1,2,3],[4,5,6,7]):
                            with dpg.table_row():
                                dpg.add_text(f"#{str(i)}:")
                                dpg.add_checkbox(tag=f"sensor_detected_cell_{str(i)}", enabled=False)
                                dpg.add_text(f"#{str(j)}:")
                                dpg.add_checkbox(tag=f"sensor_detected_cell_{str(j)}", enabled=False)
                    dpg.add_text("", tag="detected_sensors_info")
                    dpg.add_separator()
                    with dpg.group(tag="interval_info_displays"):
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"Expected interval between readings:", tag="expected_interval_label")
                            dpg.add_input_text(tag="expected_interval_info",label="ms", width=60, readonly=True)
                            dpg.set_value("expected_interval_info", str(self.data_manager.params[2]))
                        with dpg.group(horizontal=True):
                            dpg.add_text("Actual interval:", tag="actual_interval_label")
                            dpg.add_input_text(tag="actual_interval_info",label="ms", width=60, readonly=True)
                    dpg.add_text("", tag="interval_mismatch_info", color=(178, 34, 34), wrap=350)

    def _create_post_processing_tab(self):
        """Creates the contents of the post-processing tab."""
        with dpg.group(parent="post_processing_tab", horizontal=True):
            with dpg.group():
                dpg.add_text("Post-processing saved data", tag="post_processing_header")
                dpg.add_text("Selected directory with data:")
                dpg.add_text("NOT SELECTED", tag="chosen_open_directory_log")
                dpg.add_button(label="Press to select", tag="open_directory_dialog",
                               callback=lambda: self._directory_select_callback("open"))
                dpg.add_text("Sensor selection       ")
                dpg.add_combo(["N/A"], default_value="N/A", tag="sensor_choice_post", width=60)
                dpg.add_text("Processing method ")
                dpg.add_combo(["Acceleration vs time", "Magnitude of acceleration", "Fast Fourier transform",],
                                     default_value="Acceleration vs time", tag="processing_choice_post",
                                    width=200, callback=lambda: style.toggle_interval_box("post"))
                with dpg.group(horizontal=True, tag="interval_box_post", show=False):
                    dpg.add_text("Use custom interval value:")
                    dpg.add_checkbox(tag="custom_interval_choice", callback=lambda: style.toggle_custom_interval_input())
                dpg.add_input_double(label="ms", tag="custom_interval_value", min_value=0, max_value=10000, show=False,
                                     width=150)
                with dpg.group(horizontal=True):
                    dpg.add_text("Save processed data in the same directory:")
                    dpg.add_checkbox(tag="saving_choice_post")
                dpg.add_button(label="Run processing", callback=lambda:self._processing_callback("post"))
            # Define the child window to display the graphs from the processing
            dpg.add_child_window(tag="post_processing_plots", width=650, height=500)

    def _update_sensors_for_postprocessing(self):
        """Updates the sensors list for the post-processing tab by analyzing the filenames in the selected folder."""
        if self.open_directory_path is not None:
            files_detected = os.listdir(self.open_directory_path)
            # Strip the filenames in the form "S_X something.type" to detect the sensor IDs for which we have data.
            sensor_numbers = [filename.split("_")[1].split(" ")[0] for filename in files_detected]
            sensor_numbers = sorted(list(set(sensor_numbers)))
            self.post_processing_sensors = sensor_numbers.copy() # To keep them separate
            sensor_numbers.append("All")
            dpg.configure_item("sensor_choice_post", items=sensor_numbers, default_value="All")
        return True

    def _close_window(self, window_name):
        """Callback for the close button of data-related windows (live plotting and data processing). Deletes the window
        and its children (contents; default in delete_item) to avoid DPG's 'alias already exists' error when the window
        is closed and reopened."""
        if window_name == "live_plot_window":
            self.stop_plot_event.set()
        dpg.delete_item(window_name)

    def _connect_callback(self):
        """GUI callback calling the TCP class to establish the local connection with the Adafruit board."""
        host = dpg.get_value("host")
        port = int(dpg.get_value("port"))
        get_current_network()
        if self.tcp_client.connect(host, port):
            dpg.set_value(STATUS, "Connected successfully!")
            dpg.set_value("connection_status", "Connection status: Connected")
            dpg.set_value("connection_warning", "")
        else:
            dpg.set_value(STATUS, "Cannot connect.")

    def _disconnect_callback(self):
        """GUI callback calling the TCP class to disconnect from the Adafruit board."""
        if self.tcp_client.disconnect():
            dpg.set_value(STATUS, "Disconnected successfully!")

    def _command_callback(self, sender, command):
        """Guides the app and Adafruit behavior depending on the command selected by the user from the menu bar."""
        if self.tcp_client.connected:
            if command in ["SET_DATARATE", "SET_RANGE"]:
                self.tcp_client.update_sensor_parameters(command)
            elif command in ["START", "STOP"]:
                if command == "START":
                    self._start_recording()
                else:
                    self.tcp_client.stop_recording()
                dpg.set_value(STATUS, f"Sent command: {command}")
        else:
            dpg.set_value(STATUS, "Connect to the board to record data or change the sensor parameters.")
            # Reset to the default value to reflect the lack of change in hardware
            dpg.set_value("datarate_choice", "1 Hz")
            dpg.set_value("range_choice", "2 G")

    def _start_recording(self):
        """Starts the recording of sensor data."""
        self._clear_data_callback()
        # Unset the stop event flag to start printing data.
        self.tcp_client.stop_event.clear()
        self.tcp_client.send_command("START")

    def _clear_data_callback(self):
        """Clears the values of the variables but without disconnecting, i.e., the TCP data is stored."""
        self.data_manager.clear_data()
        # Clear the data log
        for child in dpg.get_item_children('data_log')[1]:
            dpg.delete_item(child)
        dpg.set_value(STATUS, "Data cleared successfully")
        dpg.set_value("actual_interval_info", "")

    def _show_processing_window(self):
        """Displays and handles the window with data processing options."""
        with dpg.window(label="Processing options", tag="processing_window",
                        autosize=True, pos=[250, 150], on_close=self._close_window("processing_window")):
            dpg.add_text("Options to process the data right now. Note that plotting may take a while.",
                         wrap=350)
            sensors_list = list(self.data_manager.active_sensors)
            sensors_list.append('All')
            # Horizontal group and text instead of a label because labels are to the right, and it cannot be easily
            # changed through attributes.
            with dpg.group(horizontal=True):
                dpg.add_text("Sensor selection       ")
                dpg.add_combo(sensors_list, default_value='All', tag="sensor_choice", width=50)
            with dpg.group(horizontal=True):
                dpg.add_text("Processing method ")
                dpg.add_combo(
                    ["Acceleration vs time", "Magnitude of acceleration", "Fast Fourier transform", "CSV export"],
                    default_value="CSV export", tag="processing_choice", width=200,
                    callback=lambda: style.toggle_interval_box("live"))
            with dpg.group(horizontal=True, tag="interval_box", show=False):
                dpg.add_text("Use interval value ")
                dpg.add_combo(["Actual", "Approximate (expected)"], default_value="Actual", tag="interval_choice",
                              width=180)
            dpg.add_text("Processed files will be saved to:")
            dpg.add_text("SAVE LOCATION NOT SELECTED", tag="chosen_save_directory_log")
            dpg.add_button(label="Press to select the save location", tag="save_directory_dialog",callback=lambda:self._directory_select_callback("save"))
            dpg.add_text("Saving status: Save OFF", tag="save_status_log")
            dpg.add_button(label="Run processing", callback=lambda:self._processing_callback("live"))

    def _processing_callback(self, sender):
        if sender == "post":
        # Post-processing tab fields
            if self.open_directory_path is None:
                dpg.set_value(STATUS, "Select a folder with the data to process first.")
            else:
                sensor_choice = dpg.get_value("sensor_choice_post")
                sensor_list = self.post_processing_sensors if sensor_choice == "All" else list(sensor_choice)
                post_process_dataframe(self.open_directory_path, sensor_list)
        else:
        # Processing in the "data acquisition" tab fields
            if dpg.get_value("processing_choice") == "CSV export" and self.save_directory_path is None:
                with dpg.window(tag="processing_warning_popup", modal=True, no_title_bar=True, width=400):
                    dpg.add_text("Warning! You haven't selected a directory to save the CSV file. The processing will return nothing.",
                                 wrap=390)
                    dpg.add_button(label="OK", callback=lambda: dpg.delete_item("processing_warning_popup"))
                    return
            self.data_manager.process_dataframe(self.save_directory_path)

    def _directory_select_callback(self, mode):
        """Callback for the directory selection button. Opens a file dialog to select the directory where the data
        will be stored, then saves its path to the GUI."""
        filepath = tkinter.filedialog.askdirectory()
        if filepath:
            # Choose a directory either for saving or opening the processed data files.
            if mode == "save":
                self.save_directory_path = filepath + "/Processed data"
                dpg.set_value("chosen_save_directory_log", f"{self.save_directory_path}")
                dpg.set_value("save_status_log", "Saving status: Save ON")
            elif mode == "open":
                self.open_directory_path = filepath
                self._update_sensors_for_postprocessing()
                dpg.set_value("chosen_open_directory_log", f"{self.open_directory_path}")

    def _show_live_plot_window(self):
        """Displays and handles the window processing the data in real time."""
        with dpg.window(label="Live data", tag="live_plot_window", autosize=True, pos=[500, 0],
                        on_close=lambda:self._close_window("live_plot_window")):
            # Stack the plots together in 2 columns and a number of rows dependent on the number of active sensors
            # Check if there is any data to plot (if there are sensors detected, it should not be)
            if bool(self.data_manager.active_sensors):
                # Create a group to display the subplots in 2 groups.
                subplot_tags = [] # Store existing subplot cell tags for the subplots
                number_of_rows = ceil(len(self.data_manager.active_sensors)/2) # Number of rows with 2 plots per row
                with dpg.group(tag="live_subplots"):
                    for i in range(number_of_rows):
                        with dpg.group(horizontal=True):
                            for sensor_id in list(self.data_manager.active_sensors)[i::number_of_rows]:
                            # Create subplots and their tags, so they can be updated rather than re-created
                                subplot_tag = f"{sensor_id}_subplot"
                                dpg.add_subplots(3,1,tag=subplot_tag, height=380, width=380)
                                subplot_tags.append(subplot_tag)
                # Start the live plotting thread
                if self.live_plotting_thread is None:
                    self.live_plotting_thread = threading.Thread(target=self._plot_live_data,
                                                                 args=[subplot_tags], daemon=True)
                    self.live_plotting_thread.start()
                self.stop_plot_event.clear()
            else:
                dpg.add_text("Nothing to plot.")

    def _plot_live_data(self, subplot_tags):
        """Plots the real-time acceleration vs time data for all detected sensors."""
        labels = [X_DATA, Y_DATA, Z_DATA]
        while True:
            try:
             # Plot only if the event flag is not set and the window exists (to prevent dpg crashes)
                if dpg.does_alias_exist("live_plot_window"):
                    if not self.stop_plot_event.is_set():
                            for subplot_tag in subplot_tags:
                                sensor_id = int(subplot_tag.split("_")[0])
                                # Create tags for every x- and y-axis to keep the aliases separate
                                x_tags = [f"x_axis_{i}_s_{sensor_id}" for i in range(1,4)]
                                y_tags = [f"y_axis_{i}_s_{sensor_id}" for i in range(1,4)]
                                # Plot in 3 vertical subplots for every sensor
                                for label, x_tag, y_tag in zip(labels, x_tags, y_tags):
                                    self._create_plot_on_subplot(sensor_id, label, x_tag, y_tag, subplot_tag)
                                time.sleep(0.05) # Slight delay to give time to fetch the data
                            # Pause plotting is the recording is paused too
                            if self.tcp_client.stop_event.is_set():
                                self.stop_plot_event.set()
                    # If recording is restarted, re-open the window to reset the data, mostly if more/fewer sensors
                    # have been connected. Then start plotting
                    elif not self.tcp_client.stop_event.is_set() and self.stop_plot_event.is_set():
                        self._close_window("live_plot_window")
                        time.sleep(1) # Short delay to fetch enough data to initialize all subplots
                        self._show_live_plot_window()
            except:
                pass # Exceptions are usually from issues with dpg aliases, which sort themselves out, so we can pass

    def _create_plot_on_subplot(self, sensor_id, label, x_tag, y_tag, subplot_tag):
        """Either creates individual plots on a subplot or adds values and re-adjusts the axes on existing ones."""
        plot_tag = f"plot_s_{sensor_id}_{label}"
        x_time = self.data_manager.data[sensor_id][NORMALIZED_TIMESTAMP]
        y_data = self.data_manager.data[sensor_id][label]
        if not dpg.does_item_exist(plot_tag):
            with dpg.plot(parent=subplot_tag):
                dpg.add_plot_axis(dpg.mvXAxis, label="Time [s]", no_gridlines=True, tag=x_tag)
                dpg.add_plot_axis(dpg.mvYAxis, label=label, no_gridlines=True, tag=y_tag)
                dpg.add_line_series(x_time, y_data, parent=y_tag, tag=plot_tag)  # Plot
                # Remove the ticks and labels from the upper x-axes since they're shared
                if label != Z_DATA:
                    dpg.configure_item(x_tag, no_tick_marks=True, no_tick_labels=True, label="")
        else:
            dpg.fit_axis_data(x_tag)
            dpg.fit_axis_data(y_tag)
            dpg.configure_item(plot_tag, x=x_time, y=y_data)

    def run(self):
        dpg.start_dearpygui()
        dpg.destroy_context()
