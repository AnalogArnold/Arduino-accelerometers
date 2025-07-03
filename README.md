# Overview
This repository provides Python and Arduino (C++) code files that are supposed to work together to create a wireless sensor data pipeline. 

# Features
## For the user
![warnings displayed if there is no connection to the server](/Images/connection_warnings.png)
![GUI view](/Images/gui_view.png)
![view of the processing window](/Images/processing_options.png)

![warning if saving is toggled off](/Images/warning_saving.png)
![showcase of the clear data function](/Images/demo_clear_data.gif)
![showcase of the data processing with plt](/Images/demo_data_processing_plt.gif)
![showcase of the data processing window and options](/Images/demo_processing_window.gif)
![showcase of the adjustability of sensor parameters](/Images/demo_toggling_sensor_params.gif)

## Outputs
![example of acceleration vs time plot](/Images/S_7_acceleration_vs_time.png)
![example of magnitude and rms plot](/Images/S_7_magnitude.png)
![example of fast fourier transform analysis plot](/Images/S_7_fft_analysis.png)

## Technical improvements

# Requirements
## Python
  (Or at least the versions I used while coding it and I cannot guarantee compatibility otherwise)
  * Python 3.12
  * pandas 2.3.0
  * numpy 1.26.4
  * scipy 1.16.0
  * [dearpygui 2.0.0](https://github.com/hoffstadt/DearPyGui)
  * $${\color{red}IMPORTANT!}$$ matplotlib **3.10.3**
    * Tested it with 3.7.3 and plotting the figures did not work properly. 
  * [smplotlib 1.0.0](https://github.com/AstroJacobLi/smplotlib)
    * Used to make the graphs look "old-school" (see the linked repository), so if this is not your cup of tea, feel free to remove it. No other changes in code are needed.

To install dependencies, you can use:
```
pip install matplotlib==3.10.3 smplotlib pandas numpy dearpygui scipy 
```

## Arduino IDE
* Arduino IDE 2.3.6
* $${\color{red}IMPORTANT!}$$ Board manager: esp32 by Espressif Systems **3.1.3**
    * The I2C communication does not work with the newer versions as of today (3 July 2025) and it returns an issue with Wire. This has nothing to do with the code as many people experienced the same issues.
* Adafruit LIS3DH 1.3.0
* Adafruit Unified Sensor 1.1.15
* Adafruit Neopixel 1.15.1
* Adafruit BusIO 1.17.1

# Usage

# Limitations and notes
One major limitation is the inability
## Known limitations (to be fixed)
1. The application freezes if the "connect" button is pressed, but the client PC is not connected to the server's network.
2. Plots are currently displayed in the Python IDE, not as part of the GUI.
3. Matplotlib is a major bottleneck and takes a solid couple of seconds to return the figures, so generating the figures right after the acquisition, especially with all 8 sensors connected, might not be practical if there are time restraints. However, this is currently the only option.
4. If the client connects to the server and changes the hardware setting (e.g., datarate), then exits and connects again, the sensors will still be in the "updated" state, whereas the app will assume the default settings, leading to a mismatch between the expected and actual intervals, and range cannot be verified.
   * Current progress: Wrote a function sending a command to the server to reset the sensors to the default settings, but it does not want to work on closing the GUI window, even though it worked well when used as a test button callback.
   * Current workaround: The script compares the expected interval between the readings (based on the datarate value in the window) and the actual interval. If it is greater than 10 ms (although in reality, no difference greater than 2 ms has been observed), it displays a warning to the user, prompting them to adjust the datarate in the GUI to fix this mismatch (which works).
![datarate mismatch warning](/Images/warning_datarate.png)

## Nice-to-have features (may be added)
1. Separation of the data processing:
   * Live data/quick rough plotting after pausing the recording in a separate GUI window.
   * Separate tab for opening and processing already saved CSV files in matplotlib for high-quality figures that can be created separately from data acquisition.
2. Autosizing based on the detected screen size instead of using hardcoded sizes in pixels.
3. Cosmetic improvements such as centering the buttons (currently require a lot of manual tinkering in dearpygui such as creating a table).
4. Check for the sensor network availability constantly (potentially a separate thread) rather than just on initialization or when "connect" is pressed.

# License
MIT License
Copyright (C) 2025 AnalogArnold (Michael Darcy)

If you use or adapt this code, please cite or acknowledge the author.
