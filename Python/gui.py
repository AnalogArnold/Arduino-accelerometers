##################################################################################################################
#
# Class AccelerometerReaderGUI creates a simple graphical user interface to enable the user to easily communicate with
# the Adafruit board and process the data without having to look at the code. It contains all theme information and
# uses TCPClient class to establish a connection with the board, and the SensorDataManager class to process the data.
#
# Version: 2.0 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################

import dearpygui.dearpygui as dpg
import tkinter.filedialog
from sensor_data_manager import SensorDataManager
from tcp_client import TCPClient

class AccelerometerReaderGUI:
    def __init__(self):
        self.data_manager = SensorDataManager()
        self.tcp_client = TCPClient(self.data_manager)
        self.directory_path = None
        # Set-up gui upon initialization
        self.setup_gui()

    def setup_gui(self):
        """Sets up the GUI for the accelerometer reader."""
        dpg.create_context()
        dpg.create_viewport(title='Accelerometer controller', width=1100, height=800)
        self._create_main_window()
        self._setup_theme()
        dpg.set_primary_window("accelerometer_control", True)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        # Check network connection before the user does anything else
        self.tcp_client.get_current_network()

    def _create_main_window(self):
        """Creates the main controls window."""
        with dpg.window(label="accelerometer control", tag="accelerometer_control"):
            # Header
            dpg.add_text("Arduino accelerometer controller", tag="program_header")

            # Board connection control panel
            with dpg.group(horizontal=True):
                # Add text instead of labels because labels are always on the left, and it does not look intuitive.
                # Board host is the IPv4 DNS address of SoftAP (software enabled access point a.k.a. virtual router)
                dpg.add_text("Board Host")
                dpg.add_input_text(default_value="192.168.4.1", tag="host", width=150)
                # Port number for the HTTP server running on the board.
                dpg.add_text("Port")
                dpg.add_input_text(default_value="8080", tag="port", width=80)
                dpg.add_text("Data Rate")
                dpg.add_combo(["1 Hz", "10 Hz", "25 Hz", "50 Hz", "100 Hz"],
                              default_value="1 Hz", tag="datarate_choice", width=100,
                              callback=lambda: self._command_callback(None, "SET_DATARATE"))
                dpg.add_text("Range")
                dpg.add_combo(["2 G", "4 G", "8 G", "16 G"],
                              default_value="2 G", tag="range_choice", width=55,
                              callback=lambda: self._command_callback(None, "SET_RANGE"))
                dpg.add_button(label="Connect", tag="connect_button", callback=self._connect_callback)
            with dpg.group(horizontal=True):
                dpg.add_text("Connection status: Not connected", tag="connection_status")
                dpg.add_text("", tag="connection_warning",  color=(178, 34, 34), wrap=600, indent=240)

            # Control buttons on the menu bar
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start recording", callback=lambda: self._command_callback(None, "START"))
                dpg.add_button(label="Stop recording", callback=lambda: self._command_callback(None, "STOP"))
                dpg.add_button(label="Process data", callback=self._show_processing_window)
                dpg.add_button(label="Clear data", callback=self._clear_data_callback)

            # Data display
            dpg.add_separator()
            dpg.add_text("Incoming data from the sensors:", tag="data_log_info")

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
                # Define child window with a predefined size - necessary to keep the table with incoming data the
                # same size rather than stretching the main window indefinitely.
                with dpg.child_window(width=700, height=400):
                    with dpg.table(tag="data_log"): # setting header_row = False causes the data not to be displayed?
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
                                dpg.add_text("No", tag=f"sensor_detected_cell_{str(i)}")
                                dpg.add_text(f"#{str(j)}:")
                                dpg.add_text("No", tag=f"sensor_detected_cell_{str(j)}")
                    dpg.add_text("", tag="detected_sensors_info")
                    dpg.add_separator()
                    dpg.add_text(f"Expected intervals between readings: {str(self.data_manager.params[2])} ms", tag="expected_interval_info")
                    dpg.add_text("Actual Interval: -- ms", tag="actual_interval_info")
                    dpg.add_text("", tag="interval_mismatch_info", color=(178, 34, 34), wrap=350)

            # Status bar to communicate with the user rather than have to look at the Python IDE
            dpg.add_separator()
            dpg.add_text("Status:", tag="status_header")
            dpg.add_text("Ready", tag="status")

    def _setup_theme(self):
        """Sets up the theme for the GUI."""
        # Each tuple: (RGB color, [list of theme color constants])
        theme_col_groups = [
            ((44, 44, 46), [dpg.mvThemeCol_Text, dpg.mvThemeCol_TextDisabled]),
            ((242, 242, 247), [dpg.mvThemeCol_WindowBg]),
            ((229, 229, 234), [dpg.mvThemeCol_ChildBg, dpg.mvThemeCol_PopupBg, dpg.mvThemeCol_TableHeaderBg,
                               dpg.mvThemeCol_TableRowBg,dpg.mvThemeCol_HeaderHovered, dpg.mvThemeCol_HeaderActive]),
            ((210, 221, 219), [dpg.mvThemeCol_FrameBg, dpg.mvThemeCol_TitleBg, dpg.mvThemeCol_MenuBarBg,
                               dpg.mvThemeCol_ScrollbarBg, dpg.mvThemeCol_Button, dpg.mvThemeCol_Tab,
                               dpg.mvThemeCol_Header]),
            ((185, 197, 195), [dpg.mvThemeCol_FrameBgHovered, dpg.mvThemeCol_ScrollbarGrab, dpg.mvThemeCol_SliderGrab,
                               dpg.mvThemeCol_ButtonHovered, dpg.mvThemeCol_TabHovered]),
            ((163, 178, 175), [dpg.mvThemeCol_FrameBgActive, dpg.mvThemeCol_TitleBgActive,
                               dpg.mvThemeCol_ScrollbarGrabHovered, dpg.mvThemeCol_SliderGrabActive,
                               dpg.mvThemeCol_ButtonActive, dpg.mvThemeCol_TabActive, dpg.mvThemeCol_Separator,
                               dpg.mvThemeCol_SeparatorHovered, dpg.mvThemeCol_SeparatorActive]),
            ((154, 165, 163), [dpg.mvThemeCol_ScrollbarGrabActive, dpg.mvThemeCol_CheckMark]),
            ((217, 228, 226), [dpg.mvThemeCol_TitleBgCollapsed])
        ]
        style_var_groups = [
            (dpg.mvStyleVar_WindowPadding, 15, 10),
            (dpg.mvStyleVar_FrameRounding, 5),
            (dpg.mvStyleVar_ChildRounding, 5),
            (dpg.mvStyleVar_FramePadding, 5, 1),
            (dpg.mvStyleVar_ItemSpacing, 5, 4),
            (dpg.mvStyleVar_ScrollbarSize, 13),
            (dpg.mvStyleVar_WindowTitleAlign, 0.5, 0.0)
        ]
        # Add the above values to the global theme
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                for color, col_list in theme_col_groups:
                    for col in col_list:
                        dpg.add_theme_color(col, color, category=dpg.mvThemeCat_Core)
                for style_var in style_var_groups:
                    if len(style_var) == 2:
                        var, value = style_var
                        dpg.add_theme_style(var, value, category=dpg.mvThemeCat_Core)
                    else:
                        var, x_val, y_val = style_var
                        dpg.add_theme_style(var, x_val, y_val, category=dpg.mvThemeCat_Core)

        # Define the item theme to make the connect button stand out more
        with dpg.theme() as item_theme_connect:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (146, 209, 161), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (123, 198, 140), category=dpg.mvThemeCat_Core)

        # Change the default font to a bigger and more legible one
        with dpg.font_registry():
            default_font = dpg.add_font("main_files/Fonts/SFPRODISPLAYREGULAR.OTF", 18)  # Default font
            header_font = dpg.add_font("main_files/Fonts/SFPRODISPLAYBOLD.OTF", 30)  # Font for the header
            child_header_font = dpg.add_font("main_files/Fonts/SFPRODISPLAYMEDIUM.OTF", 20)  # Font for the table headers

        # Bind the theme to the GUI
        dpg.bind_theme(global_theme)
        dpg.bind_font(default_font)
        dpg.bind_item_font("program_header", header_font)
        dpg.bind_item_font("data_log_info", child_header_font)
        dpg.bind_item_font("status_header", child_header_font)
        dpg.bind_item_font("detected_sensors_header", child_header_font)
        dpg.bind_item_theme("connect_button", item_theme_connect)

    def _connect_callback(self):
        """GUI callback calling the TCP class to establish the local connection with the Adafruit board."""
        host = dpg.get_value("host")
        port = int(dpg.get_value("port"))
        self.tcp_client.get_current_network()
        if self.tcp_client.connect(host, port):
            dpg.set_value("status", "Connected successfully!")
            dpg.set_value("connection_status", "Connection status: Connected")
            dpg.delete_item("connect_button")
            dpg.set_value("connection_warning", "")
        else:
            dpg.set_value("status", "Cannot connect.")

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
                dpg.set_value("status", f"Sent command: {command}")
        else:
            dpg.set_value("status", "Connect to the board to record data or change the sensor parameters.")

    def _start_recording(self):
        """Starts the recording of sensor data."""
        self._clear_data_callback()
        # Unset the stop event flag to start printing data.
        self.tcp_client.stop_event.clear()
        self.tcp_client.send_command("START")

    def _show_processing_window(self):
        """Displays and handles the window with data processing options."""
        with dpg.window(label="Processing Options", tag="processing_window",
                        autosize=True, pos=[250, 150], on_close=self._close_processing_window):
            sensors_list = list(self.data_manager.active_sensors)
            sensors_list.append('All')
            # Horizontal group and text instead of a label because labels are to the right and it cannot be easily
            # changed through attributes.
            with dpg.group(horizontal=True):
                dpg.add_text("Sensor selection       ")
                dpg.add_combo(sensors_list, default_value='All', tag="sensor_choice", width=50)
            with dpg.group(horizontal=True):
                dpg.add_text("Processing method ")
                dpg.add_combo(
                    ["Acceleration vs time", "Magnitude of acceleration", "Fast Fourier transform", "CSV export"],
                    default_value="Acceleration vs time", tag="processing_choice", width=200)
            with dpg.group(horizontal=True):
                dpg.add_text("Use interval value: ")
                dpg.add_combo(["Actual", "Approximate (expected)"], default_value="Actual", tag="interval_choice",
                              width=180)
            dpg.add_text("Processed files will be saved to:")
            dpg.add_text("SAVE LOCATION NOT SELECTED", tag="chosen_directory_log")
            dpg.add_button(label="Press to select the save location", tag="directory_dialog",callback=lambda:self._directory_select_callback())
            dpg.add_text("Saving status: Save OFF", tag="save_status_log")
            dpg.add_button(label="Run processing", callback=self._processing_callback)

    def _close_processing_window(self) :
        """Callback for the close button of the processing window. Deletes all items from the processing window to
        avoid DPG's 'alias already exists' error when the window is closed and reopened."""
        for item in ["processing_window", "directory_dialog","processing_choice", "interval_choice",
                     "save_status_log", "chosen_directory_log", "sensor_choice"]:
            dpg.delete_item(item)

    def _processing_callback(self):
        self.data_manager.process_dataframe(self.directory_path)

    def _directory_select_callback(self):
        """Callback for the directory selection button. Opens a file dialog to select the directory where the data
        will be stored, then saves its path to the GUI."""
        filepath = tkinter.filedialog.askdirectory()
        if filepath:
            self.directory_path = filepath + "/Processed data"
            dpg.set_value("chosen_directory_log", f"{self.directory_path}")
            dpg.set_value("save_status_log", "Saving status: Save ON")

    def _clear_data_callback(self):
        """Clears the values of the variables but without disconnecting, i.e., the TCP data is stored."""
        self.data_manager.clear_data()
        # Clear the data log
        for child in dpg.get_item_children('data_log')[1]:
            dpg.delete_item(child)
        dpg.set_value("status", "Data cleared successfully")
        dpg.set_value("actual_interval_info", "Actual Interval: ---- ms")

    def run(self):
        dpg.start_dearpygui()
        dpg.destroy_context()
