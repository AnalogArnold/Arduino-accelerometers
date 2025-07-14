##################################################################################################################
#
# Class TCPClient is responsible for the connection and communication with the ESP32 server using TCP/IP protocol.
# It receives data continuously from the ESP32 server using a separate thread, and sends user commands such as start,
# stop, or adjusting the hardware settings without having to do it directly from the Arduino IDE. It then feeds the
# data to the SensorDataManager class for further processing.
#
# Version: Version: 2.3 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################

import socket
import subprocess
import threading
import dearpygui.dearpygui as dpg
import time

class TCPClient:
    """ Handles the connection and communication with the ESP32 server using TCP/IP protocol."""

    def __init__(self, data_manager):
        self.BUFFER_SIZE = 4096
        self.SERVER_NAME = "ESP32_AP" # Change if the network emitted by the Adafruit has a different name.
        self.data_manager = data_manager
        self.socket = None
        self.stop_event = threading.Event() # Event flag for stopping the receiver thread.
        self.receiver_thread = None
        self.connected = False

    def connect(self, host, port):
        """Establishes connection with the Arduino (EP32) server.
            Starts a thread to receive data continuously from the EP32 without blocking the main program (so the rest of
            the code can keep on running). It also contains a 2 s timeout in case a connection cannot be established or
            it suddenly stops receiving data (e.g., Arduino resets mid-recording),  so the program does not freeze. We
            set this thread as a daemon thread i.e., such that will automatically terminate when the main program
            ends. Used for threads providing background services, like receiving data continuously."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set timeout to 2 seconds so the program doesn't get stuck.
            self.socket.settimeout(2)
            self.socket.connect((host, port))
            self.socket.settimeout(None)
            self.stop_event.set() # Start the program in a stopped state.
            self.receiver_thread = threading.Thread(target=self._receive_data, daemon=True)
            self.receiver_thread.start()
            self.connected = True
            return True
        except Exception as e:
            dpg.set_value("status", f"Connection failed: {str(e)}")
            return False

    def disconnect(self):
        """Disconnects from the ESP32 server. Stops the receiver thread and closes the connection."""
        if self.connected:
            self.socket.close()
            self.socket.shutdown(socket.SHUT_RDWR)
            self.stop_event.set()
            self.socket = None
            self.connected = False
            self.receiver_thread.join()
            self.receiver_thread = None
            dpg.set_value("connection_status", "Connection status: Disconnected")
            return True
        return False

    def _receive_data(self):
        """Receives data continously from the ESP32 without blocking the main program."""
        while True:
            try:
                if not self.stop_event.is_set():
                    data = self.socket.recv(self.BUFFER_SIZE).decode()
                    self.data_manager.buffer += data
                    # Process complete lines whilst preserving partial messages in the buffer
                    while '\n' in self.data_manager.buffer:
                        line, self.data_manager.buffer = self.data_manager.buffer.split('\n', 1)
                        self.data_manager.process_line(line.strip())
                        self._update_gui_table(line)
                        self._update_actual_interval()
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
                dpg.set_value("status", "Connection lost.")
                self.disconnect()
                break
            except TimeoutError as e:
                dpg.set_value("status", "Connection timed out. Check the hardware.")
                self.disconnect()
                break

    def get_current_network(self):
        """Checks what network the PC is connected to. If it is not connected to the Adafruit (ESP32) network, it
        checks if that network is available to return the appropriate message to the user."""
        # Show available Wi-Fi networks
        devices_available = subprocess.check_output(['netsh', 'wlan', 'show', 'network'], encoding='utf-8')
        server_available = False
        # Check if the server network is detected at all.
        for result in devices_available.split('\n'):
            result = result.strip()
            # Line starting with SSID will tell us the network the PC is connected to
            if result.startswith('SSID') and not result.startswith('SSID BSSID'):
                current_ssid = result.split(':', 1)[1].strip()
                break
        # Check if the current network is the Adafruit (ESP32) network.
        if current_ssid != self.SERVER_NAME:
            # If not, check if the Adafruit network is detected.
            if self._check_server_detected():
                dpg.set_value("connection_warning", "Please connect to the Adafruit (ESP32) network in the Wi-Fi settings first.")
            else:
                dpg.set_value("connection_warning","Adafruit (ESP32) network not detected. Please make sure that the board is switched on.")
        else:
            dpg.set_value("connection_warning","")

    def _check_server_detected(self):
        """Checks if the server is detected by the PC."""
        networks = subprocess.check_output(['netsh','wlan','show','network']).decode('ascii')
        networks= networks.replace("\r","")
        if self.SERVER_NAME in networks:
            return True
        else:
            return False

    def _update_gui_table(self, line):
        """Adds data read live into the output table."""
        parts = line.strip().split(",")
        dpg.add_table_row(parent="data_log", height=18)
        with dpg.table_row(parent="data_log"):
            dpg.add_text(parts[0])
            dpg.add_text(parts[2])
            dpg.add_text(parts[3])
            dpg.add_text(parts[4])
            dpg.add_text(parts[1])
        dpg.set_y_scroll("data_log", dpg.get_y_scroll_max("data_log"))

    def _update_actual_interval(self):
        """Calculates and updates the actual interval after the recording is started.
        The interval is calculated as the difference between 2nd and 1st timestamp recorded for the same (first active)
        sensor and converted to ms. Based on tests, this is fairly accurate  and there is no significant time difference
         between other sensors or other readings after rewriting the Arduino code to use freeRTOS)."""
        # Check if there is enough recorded data to calculate the interval.
        if len(self.data_manager.active_sensors) >= 1:
            reference_sensor_id = min(self.data_manager.active_sensors)
            timestamps = self.data_manager.data[reference_sensor_id]["timestamp"]
            if len(timestamps) >= 2 and not self.data_manager.params[3]:
                # Calculate the interval
                interval = (timestamps[-1] - timestamps[-2]) * 1000 # Convert to ms to keep consistent with the rest...
                self.data_manager.params[3] = round(interval)
                dpg.set_value("actual_interval_info", self.data_manager.params[3])
                self._check_for_interval_mismatch()

    def _check_for_interval_mismatch(self):
        """Calculates the difference between the expected and actual interval and displays a warning if the mismatch
        is higher than the expected range as this may mean that the sensors are set to a different datarate than
        expected or there is another kind of issue."""
        if self.data_manager.params[3]:
            mismatch = int(self.data_manager.params[2]) - int(self.data_manager.params[3])
            if abs(mismatch) > 10:
                dpg.set_value("interval_mismatch_info",
                                    "WARNING! \nThe difference between the expected and actual interval is greater"
                                    " than 10 ms.\nTry resetting the datarate to update the sensors.")
            else:
                dpg.set_value("interval_mismatch_info", "")

    def send_command(self, command):
        """Sends a command to the ESP32 server."""
        try:
            if self.connected:
                self.socket.sendall(f"{command}\n".encode())
        except (ConnectionResetError, BrokenPipeError):
            print("Connection lost")

    def disconnect(self):
        """Disconnects from the ESP32 server. Stops the receiver thread and closes the connection."""
        if self.connected:
            self.stop_event.set()
            self.socket.close()
            self.connected = False

    def reset_sensors(self):
        """Reset the sensors when the app closes so the hardware parameters are reset to default set in the GUI to
        prevent the mismatch if e.g., the app is restarted."""
        if self.data_manager.params[0] != "1 Hz":
            print("I have been activated")
            dpg.set_value("datarate_choice", self.data_manager.default_params["datarate"])
            self.update_sensor_parameters("SET_DATARATE")
        if self.data_manager.params[1] != self.data_manager.default_params["range"]:
            dpg.set_value("range_choice", self.data_manager.default_params["range"])
            self.update_sensor_parameters("SET_RANGE")

    def stop_recording(self):
        """Stops the recording of sensor data."""
        command = "STOP"
        self.send_command("STOP")
        self.stop_event.set()

    def update_sensor_parameters(self, param_type):
        """Updates the sensor parameters (datarate, range) on the board and updates related values in the GUI."""
        new_value = None
        if param_type == "SET_DATARATE":
            value = dpg.get_value("datarate_choice")
            # If user selects different datarate than the default value set in the board set-up/what is already set:
            if value != self.data_manager.params[0]:
                new_value = value.split()[0]
                # Check and, if needed, pause data recording first if the user wants to change the recording parameters.
                if not self.stop_event.is_set():
                    self.stop_recording()
                    dpg.set_value("status", "Recording was stopped to initialize the new datarate.")
                    dpg.set_value("actual_interval_info", "")
                    self.data_manager.params[3] = ""
                param = "sensor datarate"
                # Store the new datarate so that we don't overwrite the value if the user just clicks on the drop-down
                # menu but doesn't change its value.
                self.data_manager.params[0] = value
                # Update the expected interval value for the new selected datarate
                expected_interval = int(1 / int(self.data_manager.params[0].split()[0]) * 1000)
                self.data_manager.params[2] = expected_interval
                dpg.set_value("expected_interval_info", expected_interval)
        elif param_type == "SET_RANGE":
            value = dpg.get_value("range_choice")
            if value != self.data_manager.params[1]:
                new_value = value.split()[0]
                if not self.stop_event.is_set():
                    self.stop_recording()
                    dpg.set_value("status", "Recording was stopped to initialize the new range.")
                    dpg.set_value("actual_interval_info", "")
                    self.data_manager.params[3] = ""
                param = "sensor range"
                dpg.set_value("status", f"New sensor range was set to: {str(new_value)} G")
                self.data_manager.params[1] = value
        # Communicate the new setting to change it in the hardware
        if new_value is not None:
            message_to_server = (new_value + '\n').encode()
            self.socket.sendall(message_to_server)
            # Update the status bar
            dpg.set_value("status", f"New {param} was set to: {str(new_value)}")
