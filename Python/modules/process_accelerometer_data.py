##################################################################################################################
#
# Class DataProcessor receives data from the SensorDataManager and processes it according to the user's choice.
# It can plot the acceleration vs time, magnitude and rms over time, and the Fast Fourier transform. It can also
# generate a CSV file with raw data and a CSV file with statistical analysis.
#
# Version: Version: 2.4 (July 2025)
# Author: Michael Darcy
# License: MIT
# Copyright (C) 2025 AnalogArnold
#
##################################################################################################################

from os import path, mkdir
import matplotlib.pyplot as plt
import smplotlib
import io
import DearPyGui_ImageController as dpg_img
import dearpygui.dearpygui as dpg
from PIL import Image
import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal import windows
from .global_settings import *

# Global variables defining the style of the figures
AXIS_NAMES = [X_DATA, Y_DATA, Z_DATA]
COLORS = ["#58508d", "#bc5090", "#ff6361"] # Colors for x (and magnitude), y, z plots
FONT_SIZES = {"suptitle": 25, "subtitle": 20, "axis_labels": 22}
FIGURE_SIZE = (12, 10)
RESIZE_PLOT_FACTOR = 50
SUBPLOT_SPACING = 0.3

class DataProcessor:
    def __init__(self):
        self.buf = io.BytesIO() # To save figures to a buffer for GUI display if they're not saved to disk
        self.sensor_id = 9
        self.saving_location = None
        self.single_sensor_data = None
        self.processing_choice = None
        self.save_path = None
        self.interval = None
        self.target_tab = None # Tab to display the plots in
        self.timestamp, self.x_accel, self.y_accel, self.z_accel = [], [], [], []
        # Add texture registry to be able to display plots in the GUI instead of IDE
        dpg_img.set_texture_registry(dpg.add_texture_registry())

        # Variables extracted in initial processing that will be passed to plotting functions

    def process_data(self, sensor_id, single_sensor_data, target_tab, processing_choice="Acceleration vs time", interval=1000, saving_location=None):
        """Function taking the inputs from the user and processing the data accordingly. Serves as the interface between
        GUI and data processor."""
        self.sensor_id = sensor_id
        self.saving_location = saving_location
        self.single_sensor_data = single_sensor_data
        self.processing_choice = processing_choice
        self.target_tab = target_tab
        # Convert ms to seconds to keep it consistent with the timestamp units
        self.interval = int(interval) / 1000.0  # Convert ms to seconds
        try:
            self.timestamp = self.single_sensor_data['normalized_timestamp']
            self.x_accel = self.single_sensor_data['x-acceleration']
            self.y_accel = self.single_sensor_data['y-acceleration']
            self.z_accel = self.single_sensor_data['z-acceleration']
            self._switch_saving()
            self._select_processing_function()
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")

    def _switch_saving(self):
        """Switches on saving if the saving location is provided and creates the directory if it doesn't exist."""
        if self.saving_location is not None:
            self.save_path = str(self.saving_location) + '/S_' + str(self.sensor_id)
            if not path.exists(self.saving_location):
                mkdir(self.saving_location)

    def _select_processing_function(self):
        """Activates the appropriate processing function based on the user choice."""
        if self.processing_choice == "Acceleration vs time":
            self._acceleration_vs_time()
        elif self.processing_choice == "Magnitude of acceleration":
            self._magnitude_of_acceleration()
        elif self.processing_choice == "Fast Fourier transform":
            self._fft_analysis()
        elif self.processing_choice == "CSV export":
            self._export_csv()

    def _export_csv(self):
        """Outputs one CSV with raw data and one with descriptive statistics."""
        suffix = "stat analysis.csv"
        filepath_data = self._create_save_file_path("data.csv")
        filepath_analysis = self._create_save_file_path(suffix)
        stat_analysis = self.single_sensor_data.drop(columns=['timestamp', 'sensor_id']).describe(percentiles=[])
        stat_analysis.to_csv(filepath_analysis, mode="w", index=True, header=True) # CSV file with statistical analysis
        self.single_sensor_data.to_csv(filepath_data, mode="w", index=True, header=True) # CSV file with raw readings

    def _acceleration_vs_time(self):
        """Plots acceleration vs. time for all axes."""
        suptitle_text = f"Acceleration vs time for sensor #{str(self.sensor_id)}"
        axis_labels = ["Time [s]", "Acceleration [m/s^2]"]
        filename_suffix = "acceleration_vs_time.png"
        xs_data = [self.timestamp, self.timestamp, self.timestamp] # List to be able to use the function for plotting
        ys_data = [self.x_accel, self.y_accel, self.z_accel]
        filepath = self._create_save_file_path(filename_suffix)
        self._plot_three_subplots(suptitle_text, ys_data, xs_data, axis_labels, filepath)

    def _fft_analysis(self):
        """Performs Fast Fourier transform on the accelerometer data."""
        sample_count = len(self.x_accel)
        suptitle_text = f"FFT analysis for sensor #{str(self.sensor_id)}"
        suffix = "fft_analysis.png"
        axis_labels = ["Frequency [Hz]", "Magnitude"]
        fft_xs = []
        fft_ys = []
        for axis_data in [self.x_accel, self.y_accel, self.z_accel]:
            # Extract data and remove DC offset (non-zero at rest)
            data = axis_data.values
            data_centered = data - np.mean(data)
            data_windowed = data_centered * windows.hann(sample_count)
            # Compute FFT and frequencies
            magnitudes = rfft(data_windowed)
            frequencies = rfftfreq(sample_count, d=self.interval)  # Frequencies in the center of each bin of the FFT
            fft_xs.append(frequencies)
            fft_ys.append(np.abs(magnitudes))
        filepath = self._create_save_file_path(suffix)
        self._plot_three_subplots(suptitle_text, fft_ys, fft_xs, axis_labels, filepath)

    def _magnitude_of_acceleration(self):
        """Calculates and plots the vector magnitude of acceleration and root mean square error."""
        suffix = "magnitude.png"
        components_squared_sum = self.x_accel ** 2 + self.y_accel ** 2 + self.z_accel ** 2
        magnitude = np.sqrt(components_squared_sum)  # Vector magnitude of acceleration
        rms = np.sqrt(np.mean(components_squared_sum))  # Root mean square
        # Create an array of the same size as the timestamp array with the RMS value to be able to plot it
        rms_xs = np.full(self.timestamp.shape, rms)
        # Plot magnitude
        fig, mag_ax = plt.subplots(figsize=FIGURE_SIZE)  # mag_ax - magnitude axis
        mag_ax.plot(self.timestamp, magnitude, color=COLORS[0], label="Magnitude of acceleration")
        mag_ax.set_title(f"Magnitude of acceleration vs time for sensor #{str(self.sensor_id)}",
                         fontsize=FONT_SIZES["suptitle"])
        mag_ax.set_xlabel("Time [s]")
        mag_ax.set_ylabel("Magnitude of acceleration [m/s^2]", fontsize=FONT_SIZES["axis_labels"])
        mag_ax.grid()
        # Plot RMS on the same figure and give it separate y-axis on the right
        rms_ax = mag_ax.twinx()
        rms_ax.plot(self.timestamp, rms_xs, color=COLORS[1], label="RMS")
        rms_ax.set_ylabel("RMS acceleration [m/s^2]", fontsize=FONT_SIZES["axis_labels"])
        # Change the axis color so it is easy to associate with RMS
        rms_ax.tick_params(axis="y", labelcolor=COLORS[1])
        # Combine legends from both axes
        lines, labels = mag_ax.get_legend_handles_labels()
        lines2, labels2 = rms_ax.get_legend_handles_labels()
        rms_ax.legend(lines + lines2, labels + labels2, loc='upper left')
        # Show and (optionally) save
        filepath = self._create_save_file_path(suffix)
        if filepath is not None:
            fig.savefig(filepath)
        else:
            # Clear the old data before saving to the buffer
            self.buf.seek(0)
            self.buf.truncate(0)
            fig.savefig(self.buf, format="png")
        self._display_plot_in_gui(filepath)

    def _create_save_file_path(self, suffix):
        """Checks if saving is on and returns the path (and filename) to save the figure."""
        if self.save_path is not None:
            filepath = self.save_path + " " + suffix
        else:
            filepath = None
        return filepath

    def _plot_three_subplots(self, suptitle_text, ys_data, xs_data, axis_labels, filepath=None):
        """Plots three subplots in three rows (corresponding to x, y, and z axes on the same figure."""
        fig, axs = plt.subplots(nrows=3, ncols=1, sharex=True, figsize=FIGURE_SIZE)
        plt.subplots_adjust(hspace=SUBPLOT_SPACING)
        fig.suptitle(suptitle_text, fontsize=FONT_SIZES["suptitle"])
        # Process each axis
        for axis_data, x_data, axis_name, figure_axs, color_code in zip(ys_data, xs_data, AXIS_NAMES, axs.ravel(),
                                                                        COLORS):
            # Plot
            figure_axs.plot(x_data, axis_data, color=color_code)
            figure_axs.set_title(axis_name, fontsize=FONT_SIZES["subtitle"])
            figure_axs.grid()
            figure_axs.set_xlabel("")
            if axis_name == 'y-acceleration':
                figure_axs.set_ylabel(axis_labels[1], fontsize=FONT_SIZES["axis_labels"])
            elif axis_name == 'z-acceleration':
                figure_axs.set_xlabel(axis_labels[0], fontsize=FONT_SIZES["axis_labels"])
        if filepath is not None:
            fig.savefig(filepath)
        else:
            # Clear the old data before saving to the buffer
            self.buf.seek(0)
            self.buf.truncate(0)
            fig.savefig(self.buf, format="png")
        self._display_plot_in_gui(filepath)

    def _display_plot_in_gui(self, filepath=None):
        """Displays (scaled) plot in the GUI."""
        # Decide where the plots will be displayed depending on the tab sending the request
        if self.target_tab == "post_processing":
            display_parent = "post_processing_plots"
        else:
            display_parent = "live_processing_plots"
            if dpg.does_alias_exist("live_processing_plots"):
                pass
            else:
                dpg.add_window(tag="live_processing_plots", width=650, height=600, pos=[600, 0],
                               on_close=lambda:self._delete_live_processing_plots())
        # If the user did not save the figure, it was stored in the memory buffer and it can be fetched from there
        if filepath is None:
            filepath = self.buf
        img = Image.open(filepath)
        display_size = tuple([RESIZE_PLOT_FACTOR * x for x in FIGURE_SIZE])
        img = img.resize(display_size)
        dpg_img.add_image(img, parent=display_parent)
        dpg.add_separator(parent=display_parent) # To separate different plots visually

    @staticmethod
    def _delete_live_processing_plots() -> None:
        """Closes the window displaying matplotlib plots in the data acquisition tab, while hiding the errors stemming
        from trying to delete its children (plots) which get hidden, so dpg cannot find them."""
        try:
            dpg.delete_item("live_processing_plots")
        except Exception as e: # Broad on purpose, see above
            pass
