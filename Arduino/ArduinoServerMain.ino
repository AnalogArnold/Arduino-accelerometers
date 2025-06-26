/*******************************************************************************
*
* Code written for Adafruit Feather ESP3 V2 board connected to a PCA9548 channel
* multiplexer, allowing for up to 8 LIS3DH accelerometers to be connected via
* I2C protocol. It then sends data to a Python client using TCP/IP protocol.
*
* IMPORTANT: THIS CODE USES ESP32 BOARD LIBRARY IN VERSION 3.1.3!
* THERE ARE I2C COMMUNICATION ISSUES WITH THE NEVER VERSIONS!
*
* This file has two primary functions:
* 1. Core 0: sensor control and readings:
* - Detects the number of connected sensors;
* - Changes the range and datarate of the sensors;
* - Reads the sensor data in intervals defined by the data rate. Note that this
*   is the fastest version of the code, but there is a still a limit of about
*   8 ms (125 Hz), even though LIS3DH can go faster.
* - Adds data to a queue (50 items), which acts as a thread-safe buffer.
*
* 2. Core 1: Starts a Wi-Fi server (ESP32_AP):
* - Python client can connect to the server. Note that they do not simply
*   connect over the same Wi-Fi as eduroam (for which this was developed) would
*   not let the board connect.
* - Listens to commands from the client and communicates them to the sensor
*   reading task accordingly.
*
* Author: Michael Darcy
* License: MIT
* Copyright (C) 2025 AnalogArnold
*
*******************************************************************************/
#include <WiFi.h>               
#include <Adafruit_LIS3DH.h>    
#include <Adafruit_Sensor.h>    
#include <Adafruit_NeoPixel.h>  
#include <Wire.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

//------------------------------------------------------------------------------
// DEFINITIONS SPLIT BY THEIR PURPOSE

// STEMMA QT: Define the pins necessary to turn on the Stemma port on the board.
#if defined(ADAFRUIT_FEATHER_ESP32_V2) or defined(ARDUINO_ADAFRUIT_ITSYBITSY_ESP32)
#define PIN_NEOPIXEL 0
#define NEOPIXEL_I2C_POWER 2
#endif
#if defined(PIN_NEOPIXEL)
Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
#endif

// TCP SERVER: Wi-Fi constants
const char *ssid = "ESP32_AP";
const char *password = "123456789";  // Min 8 characters
WiFiServer server(8080);

// CORE TASKS: Handles and synchronization
TaskHandle_t wifi_server_handle, sensor_reading_handle;
SemaphoreHandle_t xMutex;  // Controls access to shared resources to prevent accessing shared variables by both cores at the same time, risking data corruption
QueueHandle_t sensor_queue;
TimerHandle_t sensor_timer = NULL;

// SENSORS: I2C multiplexer and sensor set-up
#define max_sensors 8
#define PCA_ADDR 0x70  // Default multiplexer (PCA) address
int pca_active_ports[8] = { 9, 9, 9, 9, 9, 9, 9, 9 };  // Array to store the numbers of the active (connected to the accelerometers) ports. It's filled with 9s as ports are numbered 0-7.
Adafruit_LIS3DH sensors[max_sensors];

// Variables used to adjust sensor parameters from the Python client
int active_sensors = 0;
volatile bool recording_on_flag = false;
volatile bool change_datarate_flag = false;
volatile bool change_range_flag = false;
int new_parameter_value = 9;  // 9 because there is no option for the client to set this value.
unsigned int current_datarate = 1;
unsigned int interval = 0;  // Interval between the readings determined by the data rate

// Struct for the data read from the sensors
struct data_read {
  int id;
  unsigned long time;
  float x, y, z;
};

//------------------------------------------------------------------------------
// FUNCTIONS that need to be defined before set-up

// Timer callback function
void IRAM_ATTR sensor_timer_callback(TimerHandle_t xTimer) {
  xTaskNotifyGive(sensor_reading_handle);  // Wake sensor task
}

// Function for switching between the channels on the multiplexer
void pca_select_channel(uint8_t channel) {
  if (channel > 7) return;  // Wrong channel selected, exceeding what is possible for this multiplexer
  Wire.beginTransmission(PCA_ADDR);
  Wire.write(1 << channel);  // Send a byte to the selected bus
  Wire.endTransmission();
}

// Function to change sensor parameters (range, data rate)
void change_sensor_parameters(uint8_t idx, int requested_change, volatile bool &change_range_flag, volatile bool &change_datarate_flag, unsigned int &current_datarate, Adafruit_LIS3DH *sensors) {  // & to send (and overwrite) the actual variables, not just their values
  // Change sensor range
  if (requested_change == 2) {
    sensors[idx].setRange(LIS3DH_RANGE_2_G);
    change_range_flag = false;
  } else if (requested_change == 4) {
    sensors[idx].setRange(LIS3DH_RANGE_4_G);
    change_range_flag = false;
  } else if (requested_change == 8) {
    sensors[idx].setRange(LIS3DH_RANGE_8_G);
    change_range_flag = false;
  } else if (requested_change == 16) {
    sensors[idx].setRange(LIS3DH_RANGE_16_G);
    change_range_flag = false;
  }
  // Change sensor data rate
  else if (requested_change == 1) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_1_HZ);
    current_datarate = 1;
    change_datarate_flag = false;
  } else if (requested_change == 10) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_10_HZ);
    current_datarate = 10;
    change_datarate_flag = false;
  } else if (requested_change == 25) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_25_HZ);
    current_datarate = 25;
    change_datarate_flag = false;
  } else if (requested_change == 50) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_50_HZ);
    current_datarate = 50;
    change_datarate_flag = false;
  } else if (requested_change == 100) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_100_HZ);
    current_datarate = 100;
    change_datarate_flag = false;
  } else if (requested_change == 200) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_200_HZ);
    current_datarate = 200;
    change_datarate_flag = false;
  } else if (requested_change == 400) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_400_HZ);
    current_datarate = 400;
    change_datarate_flag = false;
  } else if (requested_change == 5376) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_LOWPOWER_5KHZ);
    current_datarate = 5376;
    change_datarate_flag = false;
  } else if (requested_change == 1620) {
    sensors[idx].setDataRate(LIS3DH_DATARATE_LOWPOWER_1K6HZ);
    current_datarate = 1620;
    change_datarate_flag = false;
  }
}

//------------------------------------------------------------------------------
// SET-UP

void setup() {
  Serial.begin(115200); // Can be any baud rate, does not matter here
  // Pause until serial console opens so the communications aren't displayed when user isn't looking
  while (!Serial) delay(100);  

  // STEMMA QT: Pull the Stemma QT into high (this is needed to make this port work and should be done automatically, but from my experience, that is not always the case)
  #if defined(NEOPIXEL_I2C_POWER)
    pinMode(NEOPIXEL_I2C_POWER, OUTPUT);
    digitalWrite(NEOPIXEL_I2C_POWER, HIGH);
  #endif
  // Serial.print("Neopixel_I2C_power status (1- high; 0-low):"); // Uncomment if suspected issues with Stemma QT
  // Serial.println(digitalRead(NEOPIXEL_I2C_POWER));

  // TCP SERVER: Create SoftAP (software enabled access point a.k.a. virtual router) and start it
  WiFi.softAP(ssid, password);
  server.begin();
  Serial.print("Adafruit softAP IP address: ");
  Serial.println(WiFi.softAPIP());  // 192.168.4.1 unless coded otherwise

  // I2C scanner: Inform the user about detected connections
  Wire.begin();  // Start the I2C interface
  // Initialize sensors
  for (uint8_t t = 0; t < max_sensors; t++) {
    pca_select_channel(t);
    Serial.print("PCA Port #");
    Serial.println(t);
    for (uint8_t addr = 0; addr <= 127; addr++) {
      if (addr == PCA_ADDR) continue;
      Wire.beginTransmission(addr);
      if (!Wire.endTransmission()) {
        Serial.print("Found I2C 0x");
        Serial.println(addr, HEX);
        // If there is an I2C bus at port t, replace 9 in the array with its number
        pca_active_ports[t] = int(t);                  
        sensors[t].begin(0x18);  // Key command, otherwise the below doesn't work and causes everything to reboot indefinitely. With it it returns "Bus already started in Master Mode" but at least it all works.
        sensors[t].setRange(LIS3DH_RANGE_2_G);  // 2, 4, 8 or 16 G
        sensors[t].setDataRate(LIS3DH_DATARATE_1_HZ);  // 1, 10, 25, 50, 100, 200, 400 Hz or _powerdown, _lowpower5khz, _lowpower_1k6hz
        active_sensors++;
      }
    }
  }
  interval = int(trunc((1 / float(current_datarate) * 1000)));

  // CORE TASKS: Initialize mutex and queue
  xMutex = xSemaphoreCreateMutex();
  sensor_queue = xQueueCreate(50, sizeof(data_read));

  // Create core tasks
  xTaskCreatePinnedToCore(
    sensor_reading_function,  // Task function
    "sensor_reading",         // Task name
    10000,                    // Stack size (words)
    NULL,                     // Task parameters
    1,                        // Priority (higher = more urgent)
    &sensor_reading_handle,   // Task handle
    0                         // Core 0
  );
  xTaskCreatePinnedToCore(
    wifi_server_function,  
    "wifi_server",         
    10000,                 
    NULL,                  
    1,                     
    &wifi_server_handle,   
    1                      
  );

  // Initialize timer
  sensor_timer = xTimerCreate(
    "sensor_timer",
    pdMS_TO_TICKS(interval),  // Initial interval
    pdTRUE,                   // Auto-reload
    NULL,                     // Timer ID
    sensor_timer_callback     // Callback
  );
  // Start immediately
  xTimerStart(sensor_timer, 0);  

} 

//------------------------------------------------------------------------------
// CORE TASK FUNCTIONS

// WiFi server task (Core 1)
void wifi_server_function(void *pvParameters) {
  for (;;) {
    WiFiClient client = server.available();
    if (client) {
      Serial.println("Client connected");
      while (client.connected()) {
        // Process client commands
        if (client.available()) {
          String command = client.readStringUntil('\n');
          command.trim();

          xSemaphoreTake(xMutex, portMAX_DELAY);
          if (command == "START") {
            recording_on_flag = true;
            Serial.println("Received START");
          } else if (command == "STOP") {
            recording_on_flag = false;
            client.clear();
          } else if (command == "EXIT") {
            client.stop();
            Serial.println("Connection to the PC client ended.");
          } else {
            double num_cmd = command.toInt();
            if (num_cmd == 2 || num_cmd == 4 || num_cmd == 8 || num_cmd == 16) {
              change_range_flag = true;
              new_parameter_value = num_cmd;
            } else {
              change_datarate_flag = true;
              new_parameter_value = num_cmd;
            }
          }
          xSemaphoreGive(xMutex);
        }
        // Send queued sensor data to the Python client
        data_read data;
        while (xQueueReceive(sensor_queue, &data, 0) == pdTRUE) {
          client.printf("%d,%lu,%.2f,%.2f,%.2f\n", data.id, data.time, data.x, data.y, data.z);
        }
        vTaskDelay(1);
      }
    }
    //vTaskDelay(100); // Reduce CPU usage
  }
}

// Sensor reading task (Core 0)
void sensor_reading_function(void *pvParameters) {

  for (;;) {
    // Wait for timer notification
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    // Access shared variables if not used by the server task
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
      bool local_recording = recording_on_flag;
      bool local_change_datarate = change_datarate_flag;
      bool local_change_range = change_range_flag;
      int local_new_parameter_value = new_parameter_value;
      xSemaphoreGive(xMutex);

      // Handle changes in the sensor settings if requested
      if (local_change_datarate || local_change_range) {
        for (uint8_t i = 0; i < max_sensors; i++) {
          if (pca_active_ports[i] == i) {
            pca_select_channel(i);
            change_sensor_parameters(i, local_new_parameter_value, local_change_range, local_change_datarate, current_datarate, sensors);
          }
        }
        // Calculate the interval for the new datarate and update the timer
        interval = int(trunc((1 / float(current_datarate) * 1000)));
        xTimerChangePeriod(sensor_timer, pdMS_TO_TICKS(interval), 0);
        // Serial.print("Current interval [ms]: "); // Uncomment these lines to see if it is working
        // Serial.println(interval);
        // Serial.print("Sensor parameter adjusted to ");
        // Serial.println(new_parameter_value);
        // Change flags after applying the requested changes
        xSemaphoreTake(xMutex, portMAX_DELAY);
        change_datarate_flag = false;
        change_range_flag = false;
        xSemaphoreGive(xMutex);
      }

      // Handle sensor readings
      if (local_recording) {
        // Serial.println("Received command to start recording"); // Troubleshooting line
        for (uint8_t i = 0; i < max_sensors; i++) {
          if (pca_active_ports[i] == i) {
            pca_select_channel(i);
            sensors_event_t event;
            sensors[i].getEvent(&event);
            // Package data for queue
            data_read data = { i, millis(), event.acceleration.x, event.acceleration.y, event.acceleration.z };
            xQueueSend(sensor_queue, &data, 0);
          }
        }
      }
    }
    vTaskDelay(1);  // Yield to other tasks
  }
}

//------------------------------------------------------------------------------
// Loop could be used for low priority code

void loop() {
  vTaskDelay(1000 / portTICK_PERIOD_MS);
}