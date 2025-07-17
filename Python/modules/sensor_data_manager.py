##################################################################################################################
#
# Class SensorDataManager stores the sensor readings and processes them. It also passes the detected sensors to the
# GUI and the data to the DataProcessor for plotting and/or saving.
#
# Version: Version: 2.4 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################


from collections import defaultdict
import dearpygui.dearpygui as dpg
import pandas as pd
from .process_accelerometer_data import DataProcessor
from .global_settings import *


def plot_data(directory_path, readings, plot_sensors, settings):
    """Plots the sensor data and displays information about the progress."""
    data_processor = DataProcessor()
    for (i, sensor) in enumerate(plot_sensors):
        dpg.set_value(STATUS, f"Processing sample "
                                f"({str(i + 1)}/{str(len(plot_sensors))})... Please wait...")
        single_sensor_data = readings.loc[(readings['sensor_id'] == int(sensor))]
        data_processor.process_data(int(sensor), single_sensor_data, settings["target_tab"],
                                        settings["processing_choice"], settings["interval"], directory_path)
    dpg.set_value(STATUS, "Data has been processed!")

def post_process_dataframe(open_directory_path, sensors):
    """Processes the sensor data in the post-processing window."""
    # Open CSV files with data for selected sensors
    readings = pd.DataFrame()
    # Either assign a save path or not, depending on the user input
    if dpg.get_value("saving_choice_post"):
        save_path = open_directory_path
    else:
        save_path = None
    for sensor in sensors:
        filename = f"S_{sensor} data.csv"
        filepath = f"{open_directory_path}/{filename}"
        temp_df = pd.read_csv(filepath)
        readings = pd.concat([readings, temp_df])
    if not readings.empty:
        # Assign the interval value - either custom from the user or calculate from the data
        if dpg.get_value("custom_interval_choice"):
            interval = dpg.get_value("custom_interval_value")
        else:
            # Find the interval by finding the intervals between readings and averaging them
            mean_interval = readings.diff()[NORMALIZED_TIMESTAMP].mean()
            interval = mean_interval * 1000
        # Plot for all active sensors or one sensor
        plot_sensors = sensors
        # Encompass all user inputs in a dictionary to pass it to the plotting function.
        settings = { "processing_choice": dpg.get_value("processing_choice_post"),
                    "interval": interval,
                    "target_tab": "post_processing" }
        try:
            plot_data(save_path, readings, plot_sensors, settings)
        except Exception as e:
            dpg.set_value(STATUS, f"Error processing data: {str(e)}")
    else:
        dpg.set_value(STATUS, "No data to process.")


class SensorDataManager:
    def __init__(self):
        # {sensor_id: list_of_tuples}. Timestamps are stored in seconds!
        self.data = defaultdict(lambda: {
            TIMESTAMP: [],
            X_DATA: [],
            Y_DATA: [],
            Z_DATA: [],
            NORMALIZED_TIMESTAMP: []
        })
        self.active_sensors = set()
        self.buffer = ""
        self.default_params = {"datarate": "1 Hz", "range": "2 G"} # Default hardware settings
        self.params = ["1 Hz", "2 G", "1000", ""]  # datarate, range, expected_interval, actual_interval
        self.starting_time = [0 for i in range(8)] # Starting time for every sensor detected

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
            self.data[sensor_id][TIMESTAMP].append(timestamp)
            self.data[sensor_id][X_DATA].append(x)
            self.data[sensor_id][Y_DATA].append(y)
            self.data[sensor_id][Z_DATA].append(z)
            self.data[sensor_id][NORMALIZED_TIMESTAMP].append(self._normalize_timestamp(timestamp, sensor_id))
            # Add sensor to the list of sensors (port numbers) that are connected to the board (or at least
            # those we receive data from).
            if sensor_id not in self.active_sensors:
                self.active_sensors.add(sensor_id)
                self._update_detected_sensors(sensor_id, True)
        # Return error if data could not be processed for any reason (likely due to syntax)
        except (ValueError, IndexError) as e:
            dpg.set_value(STATUS, f"Invalid data: {line}")

    def clear_data(self):
        """Clears the sensor data."""
        self.data.clear()
        self.active_sensors.clear()
        self.buffer = ""
        self.params[3] = ""
        # Overwrite the display with detected sensors
        for i in range(8):
            self._update_detected_sensors(i, False)
        dpg.set_value("interval_mismatch_info", "")

    def process_dataframe(self, directory_path):
        """Processes the sensor data and user input regarding the outputs of interest. Then passes it into the plotting
        function."""
        readings = self._convert_to_dataframe()
        if not readings.empty:
            sensor_choice= dpg.get_value("sensor_choice")
            interval_choice = dpg.get_value("interval_choice")
            # Plot for all active sensors or one sensor
            plot_sensors = self.active_sensors if sensor_choice == "All" else list(sensor_choice)
            # Use the actual interval or the idealized value based on the datarate for the data visualization
            if interval_choice == "Actual":
                interval = self.params[3]
            else:
                interval = self.params[2]
            # Encompass all user inputs in a dictionary to pass it to the plotting function.
            settings = { "processing_choice": dpg.get_value("processing_choice"),
                        "interval": interval,
                        "target_tab": "data_acquisition"
                        }
            try:
               plot_data(directory_path, readings, plot_sensors, settings)
            except Exception as e:
                dpg.set_value(STATUS, f"Error processing data: {str(e)}")
        else:
            dpg.set_value(STATUS, "No data to process.")

    def _convert_to_dataframe(self):
        """Converts the sensor data to a pandas DataFrame for processing."""
        df = pd.DataFrame()
        for sensor_id in self.active_sensors:
            df_temp = pd.DataFrame(self.data[sensor_id])
            df_temp["sensor_id"] = sensor_id
            df = pd.concat([df, df_temp])
        return df

    def _normalize_timestamp(self, timestamp, sensor_id):
        """Normalize timestamps by selecting starting recording time = 0 instead of using the value from Arduino as
           this one is counted from the start of the program/board."""
        if self.starting_time[sensor_id] == 0:
            self.starting_time[sensor_id] = min(self.data[sensor_id][TIMESTAMP])
        normalized_timestamp = timestamp - self.starting_time[sensor_id]
        return normalized_timestamp

    @staticmethod
    def _update_detected_sensors(sensor_id, value):
        item = "sensor_detected_cell_" + str(sensor_id)
        dpg.set_value(item, value)
