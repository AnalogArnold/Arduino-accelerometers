# Overview
This repository provides a complete solution for reading accelerometer data using Arduino* (C++) and sending it to a Python client via TCP/IP protocol. The codebase supports both hardware (Arduino/ESP32) and software (Python) components, enabling efficient sensor data acquisition, processing, and visualization.

**Note:** This code was developed for a specific experimental set-up, leading to specific functionalities and choices:
  * The PC had to be positioned away from the microcontroller and sensors $$\implies$$ Wireless connection over Wi-Fi.
  * Using eduroam, which would not allow the Arduino to connect to it $$\implies$$ Hosting a server on the board with its own network for the client to connect to.
  * The need to read multiple accelerometers simultaneously (and the developer (myself) did not have any soldering skills) $$\implies$$ Use of an I2C channel multiplexer and Stemma QT pins and cables.

The schematic of the set-up, including the specific hardware used:
![sketch of the experiment](/Images/schematic.png)

>*An Adafruit board was used in this set-up, but its controls were written in the Arduino IDE. Since most people associate Arduino with microcontrollers anyway, "Arduino" is used throughout this readme file as a simplification.

# Features

* **Wireless sensor data pipeline:** Enables real-time, wireless transmission of accelerometer data from Arduino to a Python client for further analysis and visualization.
* **Multi-sensor support:** Designed to handle data from up to 8 accelerometers simultaneously, making it suitable for complex sensor networks.
* **TCP/IP communication:** Utilizes TCP/IP protocol for robust and reliable data transfer between the Arduino server and Python client. There is a buffer implemented to ensure a smooth transition and no data loss.
* **Python client GUI:** Provides a simple graphical user interface (GUI) for controlling data acquisition, adjusting sensor settings, and visualizing results. The user does not need to be familiar with Arduino IDE (C++) or Python to be able to use it.
    ![GUI view](/Images/gui_view_2.4.png)
* **Data processing and export:** Allows for processing of incoming sensor data and plotting the results, giving the user multiple output options (see below). It can be done either right after data acquisition, or the user can post-process data from a CSV file.
* **Live data plotting:** Supports real-time plotting of sensor data within the Python environment for immediate feedback during acquisition.
   ![live data plotting demo](/Images/demo_live_plotting.gif)
* **Recording data and post-processing  simultaneously:** Users can access the _Data acquisition_ and _Post-processing tabs_ at the same time, offering maximum efficiency.
   ![using both tabs simultaneously demo](/Images/demo_both_tabs_in_use_2.4.gif)
* **Interval mismatch warning:** Automatically compares the expected (based on the sensor data rate) and actual data intervals, warning the user if discrepancies are detected and suggesting corrective actions.
* **No existing Wi-Fi needed:** The board has its own network, so if you cannot connect it to an existing Wi-Fi for any reason, this is not an issue.


## Outputs
1. **CSV export:** raw data and descriptive statistics (mean, standard deviation, etc.).
  
2. **Acceleration over time**
![example of acceleration vs time plot](/Images/S_7_acceleration_vs_time.png)

3. **Fast Fourier Transform analysis**
![example of fast fourier transform analysis plot](/Images/S_7_fft_analysis.png)

4. **Vector magnitude of acceleration and root mean square over time**
![example of magnitude and rms plot](/Images/S_7_magnitude_new.png)

### Data processing overview
1. **Processing options overview:**
  ![showcase of the data processing window and options](/Images/demo_post_processing_2.4.gif)

    * **Sensor selection** - Either "all" or a single sensor from the list of active sensors. In the _Post-processing_ tab, the sensor numbers are inferred automatically from the files in the selected folder.
    * **Processing method** - Select the desired output. In the _Data acquisition_ tab, there is also an option to export to CSV.
    * **Interval used** (FFT only) - Either:
       * Expected (live processing)/custom (post-processing) - Typically what we would expect based on the selected datarate; or
       * Actual - In live processing, this is calculated from the first two timestamps measured for the first detected sensor (this is because live processing already takes significantly longer than post-processing). This is fairly accurate. However, in post-processing, this value is found by taking the average difference between all timestamps for a given sensor.
       * Expected and actual intervals should be identical, but if there is a mismatch, the user can select whether to make assumptions or use the real data for the FFT.
    * **Selecting a save location** (_Data acquisition tab_) - Optional, the user can also process the data without saving it. The only exception is the CSV export, which will return the following pop-up:
      
      ![warning if saving is toggled off](/Images/warning_saving.png)
      
3. **Demo of the live data processing (with saving):**
![showcase of the data processing with plt](/Images/demo_data_processing_plt.gif)

Note: Live data processing with plt takes considerably longer than post-processing, so apart from exporting to CSV, doing it is discouraged. The purpose of keeping it there is to let the user plot, e.g., a single FFT plot, to verify if their results match their expectations during the experiment.

## Other functions
1. **Wi-Fi connection verification:** Checks if the PC is connected to the server network; if it is not, checks if the server network is detected at all. Based on the result, it displays different communications to the user:
  ![warnings displayed if there is no connection to the server](/Images/connection_warnings.png)

2. **Sensor parameter adjustment:** Change the datarate and/or range from the GUI instead of having to update them in the Arduino code and re-uploading it to the board.
  ![showcase of the adjustability of sensor parameters](/Images/demo_toggling_sensor_params_2.4.gif)

3. **Sensor detection:** Automatically updates the list of detected sensors every time the "Start recording" button is pressed.
   ![view of the processing window](/Images/processing_options_2.3.png)

4. **Ability to connect and disconnect without resetting the program:** Particularly useful if the user expects to lose connection with the Arduino. There is also a five-minute timeout implemented that automatically severs the connection if no data is received during this time.
  ![demo showing disconnecting and re-connecting](/Images/demo_connect_disconnect_2.4.gif)

5. **Displaying PLT plots in the GUI:** The plots from matplotlib are displayed directly in the GUI, removing the need to look at the IDE. If the user does not choose to save the figures, they are loaded into a buffer, without creating any files. Otherwise, the software uses the path to the saved figure.
  ![screenshot of data acquisition and post-processing tabs with matplotlib plots displayed in the window](/Images/gui_plt_plots_2.4.png)

# Requirements
## Python
  (Or at least the versions I used while coding it and I cannot guarantee compatibility otherwise)
  * Python 3.12
  * Pandas 2.3.0
  * NumPy 1.26.4
  * SciPy 1.16.0
  * [DearPyGui 2.0.0](https://github.com/hoffstadt/DearPyGui)
  * [DearPyGui-ImageController 1.0.1](https://github.com/IvanNazaruk/DearPyGui-ImageController)
  * Pillow 11.2.1
  * $${\color{red}IMPORTANT!}$$ Matplotlib **3.10.3**
    * Tested it with 3.7.3 and plotting the figures did not work properly. 
  * [SMplotlib 1.0.0](https://github.com/AstroJacobLi/smplotlib)
    * Used to make the graphs look "old-school" (see the linked repository), so if this is not your cup of tea, feel free to remove it. No other changes in code are needed.

To install dependencies, you can use:
```
pip install pandas==2.3.0 numpy==1.26.4 scipy==1.16.0 dearpygui==2.0.0 pillow==11.2.1 matplotlib==3.10.3
pip install git+https://github.com/IvanNazaruk/DearPyGui-ImageController.git@v1.0.1
pip install git+https://github.com/AstroJacobLi/smplotlib.git@v1.0.0
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
1. Setup Arduino: Flash the provided Arduino code to your ESP32 board and ensure all required libraries are installed.
2. Configure Python client: Install the Python dependencies listed above.
3. Connect your PC to the Arduino's network (called *ESP32* by default, with the password 12345678 - can be changed in the Arduino code if higher security is required).
4. Run the Python client: Start the GUI from the _app.py_ file, connect to the server, and begin data acquisition and plotting.

# Limitations and notes
One major limitation is the **inability to use the full potential of the Adafruit LIS3DH accelerometers**, which can go 400 Hz in high resolution mode, and even to 5.3 kHz in low power mode. The maximal cutoff here is slightly above 100 Hz (for 3 sensors), so the GUI does not show options above 100 Hz. This is due to two main reasons:
1. Using an I2C protocol with a channel multiplexer: Switching between the channels and taking a reading takes about 3-4 ms, the shortest time between consecutive readings from two different sensors.
   * For 1-2 sensors, the performance could be improved since there would be no need to use a multiplexer to split the addresses.
   * Another solution could be using an SPI bus - this would allow multiple accelerometers without the need to use the multiplexer. The downside would be soldering (for inexperienced users) and the number of cables needed multiplying quite fast with the number of sensors.
2. Using a Wi-Fi connection and accepting commands from a client: Additional instructions, loops, etc.
   * It would likely be faster to use a direct connection to the PC and the serial monitor from Arduino IDE.
   * This has already been sped up as much as possible by splitting the network transmission and data acquisition into two tasks, each assigned to a separate core and a hard-precision hardware timer.

## Known limitations (to be fixed)
1. The application freezes if the "connect" button is pressed, but the client PC is not connected to the server's network.
   * **v2.3:** This issue is fixed by adding a timeout to the socket. This also allowed for adding the ability to connect/disconnect repeatedly, without reopening the app.
3. Plots are currently displayed in the Python IDE, not as part of the GUI.
   * **v2.1:** Real-time plots are now displayed as a part of the GUI.
   * **v2.4:** Resolved. Matplotlib plots are shown in the GUI instead of the IDE.
4. Matplotlib is a major bottleneck and takes a solid couple of seconds to return the figures, so generating the figures right after the acquisition, especially with all 8 sensors connected, might not be practical if there are time restraints. However, this is currently the only option.
   * **v2.2:** The user can now quickly plot data in real-time, and plot the "proper" figures in matplotlib during post-processing from the CSV files. The function to use matplotlib right after recording was kept to allow more options.
   * **v2.4:** Using matplotlib in the _Post-processing_ tab is significantly faster.
5. If the client connects to the server and changes the hardware setting (e.g., datarate), then exits and connects again, the sensors will still be in the "updated" state, whereas the app will assume the default settings, leading to a mismatch between the expected and actual intervals, and range cannot be verified.
   * ~~Current workaround: The script compares the expected interval between the readings (based on the datarate value in the window) and the actual interval. If it is greater than 10 ms (although in reality, no difference greater than 2 ms has been observed), it displays a warning to the user, prompting them to adjust the datarate in the GUI to fix this mismatch (which works).~~
![datarate mismatch warning](/Images/warning_datarate.png)
   * **v2.3:** The sensors are reset to default when the app terminates.


## Nice-to-have features (may be added)
1. Separation of the data processing:
   * ~~Live data/quick rough plotting after pausing the recording in a separate GUI window.~~
   * Separate tab for opening and processing already saved CSV files in matplotlib for high-quality figures that can be created separately from data acquisition.
2. Autosizing based on the detected screen size instead of using hardcoded sizes in pixels.
3. Cosmetic improvements such as centering the buttons (currently require a lot of manual tinkering in dearpygui such as creating a table).
4. Check for the sensor network availability constantly (potentially a separate thread) rather than just on initialization or when "connect" is pressed.
5. Create a separate file with constants and global variables for clarity and conciseness.

# Updates
* **Version 2.1 (08/07/2025):** There is now an option to plot data in real time using DearPyGUI's built-in functions, which are much faster.
* **Version 2.2 (09/07/2025):** The main window is now split into two separate tabs, one for live data acquisition and processing, and one for post-processing of already recorded data stored in CSV files.
* **Version 2.3 (14/07/2025):** Added "Disconnect" button and fixed the issue with the app freezing if the user presses "Connect" without being connected to the Arduino network. Added handling of sudden interruptions in the connection (e.g., board reset while sending data). The hardware is now reset to the default parameters when the app is closed.
* **Version 2.4 (18/07/2025):** Data processing in both tabs has been made fully functional, and the output matplotlib plots are displayed within the GUI. The code has been further refactored to keep the GUI style  separate from its functional structure, and commonly used string parameters have been turned into global variables, making it easier to adjust the code if needed.

# License
MIT License
Copyright (C) 2025 AnalogArnold (Michael Darcy)

If you use or adapt this code, please cite or acknowledge the author.

Readme for version: 2.4 (latest)
