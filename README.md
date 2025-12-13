# ESP32 Zigbee Indicator Light

This project implements a Zigbee Color Dimmable Light using ESP32-C6/H2 and an addressable LED (WS2812).

## Features
- Zigbee 3.0 Router
- On/Off, Level (Brightness), and Color (Hue/Saturation) control
- Compatible with Home Assistant (ZHA, Zigbee2MQTT)
- Factory Reset via Boot Button (Hold for 3s)

## Hardware
- **ESP32-C6 or ESP32-H2** (e.g., DevKitM-1)
- **LED**: WS2812/NeoPixel on **GPIO 8** (Default for onboard LED on many devkits)
- **Button**: Boot button on **GPIO 9** (for factory reset)

## Usage
1. Build and Flash:
   ```bash
   idf.py build flash monitor
   ```
2. Hold BOOT button for 3 seconds to reset/pairing mode if needed.
3. Join your Zigbee network.
4. Control via Home Assistant (Light entity).

## Dependencies
- `espressif/esp-zigbee-lib`
- `espressif/led_strip`
