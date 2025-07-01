import socket
import threading
import pandas as pd
import dearpygui.dearpygui as dpg
import tkinter.filedialog
from collections import defaultdict
from processAccelerometerData import main_processing_function # Import functions used for visualising the data depending on the needs

# 0. Set-up before running the main code.
# Global variables
sensor_data = defaultdict(lambda: {'timestamp': [],'x-acceleration': [],'y-acceleration': [],'z-acceleration': []})
active_sensors = set()
buffer = ''
directory_path = None
# Board address; change only if there are any conflicts.
board_HOST = "192.168.4.1" # IPv4 DNS address of SoftAP (software enabled access point a.k.a. virtual router)
board_PORT = 8080 # Port number for the HTTP server running on the board.
# Connect to the board - our TCP server. The PC (this script) is the TCP client.
tcp_client = None # TCP = Transmission Control Protocol for exchanging data between devices in a computer network, ensuring that data is transmitted fully and in the correct order.
sensor_params = ["1 Hz", "2 G", "1000", ""] # Datarate, range, expected interval, actual interval

# 1. Connection and data reception functions.
# Function to receive data continuously from the ESP32 without blocking the main program.
def receive_data(sock, stop_event):
    global buffer
    while True:
        try:
            if not stop_event.is_set():
                data = sock.recv(4096).decode()
                if not data:
                    print("Connection closed by the server.")
                    break
                buffer += data
                # Process complete lines whilst preserving partial messages in the buffer
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    process_line(line.strip())
                    #dpg.set_value("data_log", f"{dpg.get_value('data_log')}\n{"Sensor " + line.strip().split(',')[0] + ":      X: " + line.strip().split(',')[2] + "    Y: " + line.strip().split(',')[3] + "    Z: " + line.strip().split(',')[4] + " m/s^2"}") # Old deprecated version with input text field
                    # Add data read live into the output table
                    #dpg.add_table_row(parent="data_log", user_data=line.strip().split(','))
                    dpg.add_table_row(parent="data_log", height=18)
                    with dpg.table_row(parent="data_log"):
                        dpg.add_text(f"{line.strip().split(',')[0]}")
                        dpg.add_text(f"{line.strip().split(',')[2]}")
                        dpg.add_text(f"{line.strip().split(',')[3]}")
                        dpg.add_text(f"{line.strip().split(',')[4]}")
                        dpg.add_text(f"{line.strip().split(',')[1]}")
                    dpg.set_y_scroll("data_log", dpg.get_y_scroll_max("data_log"))

                    if len(sensor_data[min(list(active_sensors))]['timestamp']) >= 2  and sensor_params[3] == "":
                        reference_sensor_id = min(list(active_sensors))
                        max_index = len(sensor_data[min(list(active_sensors))]['timestamp']) - 1
                        actual_interval = ((sensor_data[reference_sensor_id]['timestamp'][max_index] - sensor_data[reference_sensor_id]['timestamp'][max_index-1]) * 1000)
                        sensor_params[3] = round(actual_interval)
                        dpg.set_value("actual_interval_info", f"Actual interval between readings: {str(sensor_params[3])} ms")
        except(ConnectionResetError, BrokenPipeError):
            print("\n Connection lost.")
            break


# Function to convert sensor data to a Pandas DataFrame for processing.
def convert_to_dataframe():
    df = pd.DataFrame()
    for sensor_id in active_sensors:
        df_temp = pd.DataFrame(sensor_data[sensor_id])
        starting_time = df_temp['timestamp'].min()
        df_temp['normalized_timestamp'] = df_temp['timestamp'] - starting_time # Normalize timestamps by selecting starting recording time = 0 instead of using the value from Arduino as this one is counted from the start of the program/board
        df_temp['sensor_id'] = sensor_id
        df = pd.concat([df, df_temp])
        del df_temp, starting_time
    return df

# 2. GUI functions


# Respond to the main commands from the user
def command_callback(sender, command):
    global stop_event
    if tcp_client:
        if command == "SET_DATARATE":
            if dpg.get_value("datarate_choice") != sensor_params[0]: # If user selects different datarate than the default value set in the board set-up.
                new_datarate = dpg.get_value("datarate_choice").split()[0]
                if not stop_event.is_set(): # Pause data recording first if the user wants to change the recording parameters.
                    tcp_client.sendall(b"STOP\n")
                    stop_event.set()
                    dpg.set_value("status", "Recording was stopped to initialize the new datarate.")
                    dpg.set_value("actual_interval_info", "")
                    sensor_params[3] = ""
                message = (new_datarate + '\n').encode()
                tcp_client.sendall(message)
                dpg.set_value("status", "New sensor datarate was set to: " + dpg.get_value("datarate_choice"))
                sensor_params[0] = dpg.get_value("datarate_choice") # So that we don't overwrite the value if the user just clicks on the drop-down menu but doesn't change its value.
                expected_interval = int(1 / int(sensor_params[0].split()[0]) * 1000)
                sensor_params[2] = expected_interval
                dpg.set_value("expected_interval_info", f"Expected intervals between readings: {str(expected_interval)} ms")
        elif command == "SET_RANGE":
            if dpg.get_value("range_choice") != sensor_params[1]:  # If user selects different range than the default value set in the board set-up.
                new_range = dpg.get_value("range_choice").split()[0]
                if not stop_event.is_set():
                    tcp_client.sendall(b"STOP\n")
                    stop_event.set()
                    dpg.set_value("status", "Recording was stopped to initialize the new range.")
                    dpg.set_value("actual_interval_info", "")
                    sensor_params[3] = ""
                message = (new_range + '\n').encode()
                tcp_client.sendall(message)
                dpg.set_value("status", "New sensor range was set to: " + new_range + ' G')
                sensor_params[1] = dpg.get_value("range_choice")
        elif command == "EXIT":
            tcp_client.sendall(b"EXIT\n")
            dpg.stop_dearpygui()
        elif command == "START":
            clear_data()
            tcp_client.sendall(b"START\n")
            stop_event.clear()  # Unset the stop event flag to start printing data.
            dpg.set_value("status", f"Sent command: {command}")
        elif command == "STOP":
            tcp_client.sendall(b"STOP\n")  # Send the STOP command to the board so it doesn't just record and transmit data when we don't need it.
            dpg.set_value("status", f"Sent command: {command}")
            stop_event.set()
    elif tcp_client is None:
        if command == "EXIT":
            dpg.stop_dearpygui()
        else:
            dpg.set_value("status", "Connect to the board to record data or change the sensor parameters.")

# Function displaying and handling the window with the data processing options
def show_processing_window():
    with dpg.window(label="Processing options", tag="processing_window", autosize=True, pos=[250,150], on_close=lambda: processing_window_close()):
        sensors_list = list(active_sensors)
        sensors_list.append('All')
        with dpg.group(horizontal=True): # Horizontal group and text instead of a label because labels are to the right and it cannot be easily changed through attributes.
            dpg.add_text("Sensor selection       ")
            dpg.add_combo(sensors_list, default_value='All', tag="sensor_choice", width = 50)
        with dpg.group(horizontal=True):
            dpg.add_text("Processing method ")
            dpg.add_combo(["Acceleration vs time", "Magnitude of acceleration", "Fast Fourier transform", "CSV export"], default_value="Acceleration vs time", tag="processing_choice", width = 200)
        with dpg.group(horizontal=True):
            dpg.add_text("Use interval value: ")
            dpg.add_combo(["Actual", "Approximate (expected)"], default_value="Actual", tag="interval_choice", width=180)
        dpg.add_text("Processed files will be saved to:")
        dpg.add_text("SAVE LOCATION NOT SELECTED", tag="chosen_directory_log")
        dpg.add_button(label="Press to select the save location", tag="directory_dialog", callback=lambda: directory_select_callback())
        #dpg.add_input_text(multiline=True, readonly=True, tag="chosen_directory_log", width=380, height= 40)        # Commented out is an "uglier" way (you need to know the location - I want it to be easier for the user)
        #dpg.add_file_dialog(directory_selector=True, show=False, callback=directory_select_callback,tag="directory_dialog", cancel_callback=lambda: dpg.hide_item("directory_dialog"))
        #dpg.add_button(label="Select directory to save", callback=lambda: dpg.show_item("directory_dialog"))
        dpg.add_text("Saving status: Save OFF", tag="save_status_log")
        dpg.add_button(label="Run processing", callback=processing_callback)

# Function to delete the processing window and its context; otherwise if the user re-opens it, the app returns an error due to already existing aliases.
def processing_window_close():
    for item in ["processing_window", "directory_dialog", "save_choice", "processing_choice", "interval_choice",
                 "save_status_log", "chosen_directory_log", "sensor_choice"]:
        dpg.delete_item(item)

# Function handling data processing
def processing_callback():
    readings = convert_to_dataframe()
    if not readings.empty:
        sensor_choice = dpg.get_value("sensor_choice")
        plot_sensors = active_sensors if sensor_choice == "All" else list(sensor_choice) # Plot for all active sensors or one sensor
        processing_choice = dpg.get_value("processing_choice")
        saving_choice = bool(dpg.get_value("save_choice")) # Boolean value
        interval_choice = dpg.get_value("interval_choice")
        if interval_choice == "Actual":
            interval = sensor_params[2]
        else:
            interval = sensor_params[2]
        try:
            for (i,sensor) in enumerate(plot_sensors):
                dpg.set_value("status", "Processing sample (" + str(i+1) + "/" + str(len(plot_sensors)) + ")... Please wait...")
                single_sensor_data = readings.loc[(readings['sensor_id'] == int(sensor))]
                main_processing_function(single_sensor_data, int(sensor), interval, processing_choice, saving_choice, directory_path)
            dpg.set_value("status", "Data has been processed!")

        except ValueError as e:
            dpg.set_value("status", e)
    else:
        dpg.set_value("status", "No data to process.")

# Function allowing the user to select the directory to save the data
def directory_select_callback():
    global directory_path
    filepath = tkinter.filedialog.askdirectory()

    if filepath:
        directory_path = filepath + "/Processed data"
        dpg.set_value("chosen_directory_log", f"{directory_path}")
        dpg.set_value("save_status_log", "Saving status: Save ON")

# Function clearing the values of the variables but without disconnecting, i.e., the TCP data is stored
def clear_data():
    # Done for sensors bit
    for child in dpg.get_item_children('data_log')[1]: # Clear the data log
       dpg.delete_item(child)
    dpg.set_value("status", "Data erased succesfully.")

# 3. DearPyGUI main app window
dpg.create_context()
dpg.create_viewport(title='Accelerometer control', width=1100, height=800)
dpg.setup_dearpygui()

# Code for the theme of the GUI
# Each tuple: (RGB color, [list of theme color constants])
theme_col_groups = [
    ((44, 44, 46), [dpg.mvThemeCol_Text, dpg.mvThemeCol_TextDisabled]),
    ((242, 242, 247), [dpg.mvThemeCol_WindowBg]),
    ((229, 229, 234), [dpg.mvThemeCol_ChildBg, dpg.mvThemeCol_PopupBg, dpg.mvThemeCol_TableHeaderBg, dpg.mvThemeCol_TableRowBg, dpg.mvThemeCol_HeaderHovered, dpg.mvThemeCol_HeaderActive]),
    ((210, 221, 219), [dpg.mvThemeCol_FrameBg, dpg.mvThemeCol_TitleBg, dpg.mvThemeCol_MenuBarBg, dpg.mvThemeCol_ScrollbarBg, dpg.mvThemeCol_Button, dpg.mvThemeCol_Tab, dpg.mvThemeCol_Header]),
    ((185, 197, 195), [dpg.mvThemeCol_FrameBgHovered, dpg.mvThemeCol_ScrollbarGrab, dpg.mvThemeCol_SliderGrab, dpg.mvThemeCol_ButtonHovered, dpg.mvThemeCol_TabHovered]),
    ((163, 178, 175), [dpg.mvThemeCol_FrameBgActive, dpg.mvThemeCol_TitleBgActive, dpg.mvThemeCol_ScrollbarGrabHovered, dpg.mvThemeCol_SliderGrabActive, dpg.mvThemeCol_ButtonActive, dpg.mvThemeCol_TabActive, dpg.mvThemeCol_Separator, dpg.mvThemeCol_SeparatorHovered, dpg.mvThemeCol_SeparatorActive]),
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

# Adding these values to the global theme
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

# Item theme to make the connect/disconnect button stand out more
with dpg.theme() as item_theme_connect:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (146, 209, 161), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (123, 198, 140), category=dpg.mvThemeCat_Core)

# Change the default font to a bigger and more legible one
with dpg.font_registry():
    default_font = dpg.add_font("SFPRODISPLAYREGULAR.OTF", 18) # Default font
    header_font = dpg.add_font("SFPRODISPLAYBOLD.OTF", 30) # Font for the header
    child_header_font = dpg.add_font("SFPRODISPLAYMEDIUM.OTF", 20) # Font for the table headers

# Actual controls window
with dpg.window(label="Accelerometer control", tag="accelerometer control"):
    dpg.add_text("Arduino accelerometer control", tag="program_header")
    # Board connection controls
    with dpg.group(horizontal=True):
        dpg.add_text("Board host") # Text instead of labels in the commands below because the labels display to the right and it looks counter-intiutive.
        dpg.add_input_text(default_value=board_HOST, tag="host", width=150)
        dpg.add_text("Port")
        dpg.add_input_text(default_value=board_PORT, tag="port", width=80)
        dpg.add_text("Data rate")
        dpg.add_combo(["1 Hz", "10 Hz", "25 Hz", "50 Hz", "100 Hz"], default_value="1 Hz", tag="datarate_choice", width=100, callback=lambda: command_callback(None, "SET_DATARATE")) # LIS3DH specific settings. It can go up to 400 Hz 1620/5376 in low power mode, but it is not achieveable in this set-up.
        dpg.add_text("Range")
        dpg.add_combo(["2 G", "4 G", "8 G", "16 G"], default_value="2G", tag="range_choice", width=55, callback=lambda: command_callback(None, "SET_RANGE")) # LIS3DH specific settings

        dpg.add_button(label="Connect", tag ="connect_button", callback=connect_callback)

    dpg.add_text("Connection status: Not connected", tag="connection_status")

    # Control buttons
    with dpg.group(horizontal=True):
        dpg.add_button(label="Start recording", callback=lambda: command_callback(None, "START"))
        dpg.add_button(label="Stop recording", callback=lambda: command_callback(None, "STOP"))
        dpg.add_button(label="Process data", callback=show_processing_window)
        dpg.add_button(label="Clear data", callback=clear_data)
        dpg.add_button(label="Exit", callback=lambda: command_callback(None, "EXIT"))

    # Data display
    dpg.add_separator()
    dpg.add_text("Incoming data from the sensors:", tag="data_log_info")
    #dpg.add_input_text(multiline=True, readonly=True, tag="data_log", width=700, height=400) # Former way of receiving input data; deprecated for clarity reasons.
    # Table with headers for the incoming data which is always visible above the table for readability.
    with dpg.table(header_row=False, tag="headers", width=680):
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_row(tag="table_row_1")
        with dpg.table_row():
            labels = ['Sensor number', 'X [m/s^2]', 'Y [m/s^2]', 'Z [m/s^2]', 'Timestamp [ms]']
            for label in labels:
                dpg.add_text(label)
    # Table displaying the incoming data.
    table_column_tags = ['sensor_id_table', 'x_accel_table', 'y_accel_table', 'z_accel_table', 'timestamp_table']
    with dpg.group(horizontal=True):
        with dpg.child_window(width=700, height=400): # Necessary to keep the table with incoming data the same size rather than stretching the main window indefinitely.
            with dpg.table(tag="data_log"): # setting header_row = False causes the data not to be displayed?
                for column_tag in table_column_tags:
                    dpg.add_table_column(tag=column_tag)
        with dpg.group():
            dpg.add_text("Expected intervals between readings: 1000 ms", tag="expected_interval_info")
            dpg.add_text("", tag="actual_interval_info")


    # Status bar to communicate with the user rather than have to look at the Python IDE
    dpg.add_separator()
    dpg.add_text("Status: \n", tag="status_header")
    dpg.add_text(" ", tag="status")

dpg.set_primary_window("accelerometer control", True)
dpg.bind_theme(global_theme)
dpg.bind_font(default_font)
dpg.bind_item_font('program_header', header_font)
dpg.bind_item_font('data_log_info', child_header_font)
dpg.bind_item_font('status_header', child_header_font)
dpg.bind_item_theme('connect_button', item_theme_connect)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()

if tcp_client:
    tcp_client.close()
