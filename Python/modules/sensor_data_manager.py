##################################################################################################################
#
# Class SensorDataManager stores the sensor readings and processes them. It also passes the detected sensors to the
# GUI and the data to the DataProcessor for plotting and/or saving.
#
# Version: 2.0 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################


from collections import defaultdict
import dearpygui.dearpygui as dpg
import pandas as pd
from process_accelerometer_data import DataProcessor


class SensorDataManager:
    def __init__(self):
        # {sensor_id: list_of_tuples}. Timestamps are stored in seconds!
        self.data = defaultdict(lambda: {
            "timestamp": [],
            "x-acceleration": [],
            "y-acceleration": [],
            "z-acceleration": []
        })
        self.active_sensors = set()
        self.buffer = ""
        self.default_params = {"datarate": "1 Hz", "range": "2 G"} # Default hardware settings
        self.params = ["1 Hz", "2 G", "1000", ""]  # datarate, range, expected_interval, actual_interval

    def process_line(self, line):
        """Process every line of the data incoming from the Adafruit. One line = one sensor reading."""
        if not line:
            return
        # Split the received data from Adafruit into parts and store accordingly in the data dictionary
        try:
            data_parts = line.split(",")
            sensor_id = int(data_parts[0])
            timestamp = float(data_parts[1]) * 0.001 # Convert timestamp from milliseconds to seconds
            x, y, z = map(float, data_parts[2:5])

            self.data[sensor_id]["timestamp"].append(timestamp)
            self.data[sensor_id]["x-acceleration"].append(x)
            self.data[sensor_id]["y-acceleration"].append(y)
            self.data[sensor_id]["z-acceleration"].append(z)
            # Add sensor to the list of sensors (port numbers) that are connected to the board (or at least
            # those we receive data from).
            if sensor_id not in self.active_sensors:
                self.active_sensors.add(sensor_id)
                self._update_detected_sensors(sensor_id, "Yes")
        # Return error if data could not be processed for any reason (likely due to syntax)
        except (ValueError, IndexError) as e:
            dpg.set_value("status", f"Invalid data: {line}")

    def clear_data(self):
        """Clears the sensor data."""
        self.data.clear()
        self.active_sensors.clear()
        self.buffer = ""
        self.params[3] = ""
        # Overwrite the display with detected sensors
        for i in range(8):
            self._update_detected_sensors(i, "No")
        dpg.set_value("interval_mismatch_info", "")

    def _update_detected_sensors(self, sensor_id, value):
        item = "sensor_detected_cell_" + str(sensor_id)
        dpg.set_value(item, value)

    def process_dataframe(self, directory_path):
        """Processes the sensor data and user input regarding the outputs of interest. Then passes it into the plotting
        function."""
        readings = self._convert_to_dataframe()
        if not readings.empty:
            sensor_choice= dpg.get_value("sensor_choice")
            interval_choice = dpg.get_value("interval_choice")
            # Plot for all active sensors or one sensor
            plot_sensors = self.active_sensors if sensor_choice == "All" else list(sensor_choice)
            # Use actual interval or the idealized value based on the datarate for the data visualization
            if interval_choice == "Actual":
                interval = self.params[3]
            else:
                interval = self.params[2]
            # Encompass all user inputs in a dictionary to pass it to the plotting function.
            settings = { "processing_choice": dpg.get_value("processing_choice"),
                        "interval": interval
                        }
            try:
               self._plot_data(directory_path, readings, plot_sensors, settings)
            except Exception as e:
                dpg.set_value("status", f"Error processing data: {str(e)}")
        else:
            dpg.set_value("status", "No data to process.")

    def _convert_to_dataframe(self):
        """Converts the sensor data to a pandas DataFrame for processing."""
        df = pd.DataFrame()
        for sensor_id in self.active_sensors:
            df_temp = pd.DataFrame(self.data[sensor_id])
            starting_time = df_temp['timestamp'].min()
            # Normalize timestamps by selecting starting recording time = 0 instead of using the value from Arduino as
            # this one is counted from the start of the program/board
            df_temp['normalized_timestamp'] = df_temp['timestamp'] - starting_time
            df_temp['sensor_id'] = sensor_id
            df = pd.concat([df, df_temp])
        return df

    def _plot_data(self, directory_path, readings, plot_sensors, settings):
        """Plots the sensor data and displays information about the progress."""
        data_processor = DataProcessor()
        for (i, sensor) in enumerate(plot_sensors):
            dpg.set_value("status", f"Processing sample "
                                    f"({str(i + 1)}/{str(len(plot_sensors))})... Please wait...")
            single_sensor_data = readings.loc[(readings['sensor_id'] == int(sensor))]
            data_processor.process_data(int(sensor), single_sensor_data,
                                            settings['processing_choice'], settings['interval'], directory_path)
        dpg.set_value("status", "Data has been processed!")
