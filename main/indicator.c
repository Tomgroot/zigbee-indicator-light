/*
 * Zigbee Indicator Light (Multicolor LED)
 * Based on Espressif Zigbee SDK
 */

#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "led_strip.h"
#include "esp_zigbee_core.h"
#include "esp_zigbee_cluster.h"
#include "zcl/esp_zigbee_zcl_common.h"
#include "zcl/esp_zigbee_zcl_on_off.h"
#include "zcl/esp_zigbee_zcl_level.h"
#include "zcl/esp_zigbee_zcl_color_control.h"

// Configuration
#define LED_STRIP_GPIO      GPIO_NUM_8   // Built-in RGB LED on many ESP32-C6/H2 boards
#define LED_STRIP_LEDS      1
#define BOOT_BUTTON_PIN     GPIO_NUM_9
#define BUTTON_HOLD_TIME_MS 3000

#define HA_ENDPOINT         1
#define ESP_MANUFACTURER_NAME "ZigbeeHive"
#define ESP_MODEL_IDENTIFIER  "IndicatorLight"

static const char *TAG = "ZIGBEE_LIGHT";

// Global LED state
static led_strip_handle_t led_strip;
static bool g_on_off = false;
static uint8_t g_level = 254; // 0-254
static uint8_t g_hue = 0;     // 0-254 representing 0-360 deg
static uint8_t g_sat = 0;     // 0-254

// Helper to update LED based on global state
static void update_led(void) {
    if (!led_strip) {
        return;
    }

    if (!g_on_off) {
        led_strip_clear(led_strip);
        return;
    }

    // Convert Zigbee Hue (0-254) to degrees (0-360)
    // Hue: 0-254 -> 0-360 approx (val * 360 / 254)
    uint32_t hue_deg = (uint32_t)g_hue * 360 / 254;
    
    // Convert Zigbee Saturation (0-254) to 0-255
    uint32_t sat_val = (uint32_t)g_sat; // approx map 1:1

    // Brightness combines Level and global intensity
    // Level is 0-254
    uint32_t val_val = (uint32_t)g_level;

    // Use led_strip helper (assuming latest driver has hsv support, otherwise simple hsv2rgb)
    // led_strip 3.x has set_pixel_hsv
    led_strip_set_pixel_hsv(led_strip, 0, hue_deg, sat_val, val_val);
    led_strip_refresh(led_strip);
}

// Zigbee Attribute Callback
static esp_err_t zb_attribute_handler(const esp_zb_zcl_set_attr_value_message_t *message) {
    esp_err_t ret = ESP_OK;
    
    if (!message) return ESP_FAIL;
    if (message->info.dst_endpoint != HA_ENDPOINT) return ESP_OK;

    bool update = false;

    if (message->info.cluster == ESP_ZB_ZCL_CLUSTER_ID_ON_OFF) {
        if (message->attribute.id == ESP_ZB_ZCL_ATTR_ON_OFF_ON_OFF_ID &&
            message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_BOOL) {
            g_on_off = message->attribute.data.value ? *(bool *)message->attribute.data.value : false;
            ESP_LOGI(TAG, "On/Off set to %d", g_on_off);
            update = true;
        }
    } 
    else if (message->info.cluster == ESP_ZB_ZCL_CLUSTER_ID_LEVEL_CONTROL) {
        if (message->attribute.id == ESP_ZB_ZCL_ATTR_LEVEL_CONTROL_CURRENT_LEVEL_ID &&
            message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_U8) {
            g_level = message->attribute.data.value ? *(uint8_t *)message->attribute.data.value : 0;
            ESP_LOGI(TAG, "Level set to %d", g_level);
            update = true;
        }
    }
    else if (message->info.cluster == ESP_ZB_ZCL_CLUSTER_ID_COLOR_CONTROL) {
        if (message->attribute.id == ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_HUE_ID &&
            message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_U8) {
            g_hue = message->attribute.data.value ? *(uint8_t *)message->attribute.data.value : 0;
            ESP_LOGI(TAG, "Hue set to %d", g_hue);
            update = true;
        }
        else if (message->attribute.id == ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_SATURATION_ID &&
                 message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_U8) {
            g_sat = message->attribute.data.value ? *(uint8_t *)message->attribute.data.value : 0;
            ESP_LOGI(TAG, "Saturation set to %d", g_sat);
            update = true;
        }
    }

    if (update) {
        update_led();
    }

    return ret;
}

static esp_err_t zb_action_handler(esp_zb_core_action_callback_id_t callback_id, const void *message) {
    switch (callback_id) {
    case ESP_ZB_CORE_SET_ATTR_VALUE_CB_ID:
        return zb_attribute_handler((const esp_zb_zcl_set_attr_value_message_t *)message);
    default:
        ESP_LOGW(TAG, "Receive Zigbee action(0x%x) callback", callback_id);
        break;
    }
    return ESP_OK;
}

void esp_zb_app_signal_handler(esp_zb_app_signal_t *signal_struct) {
    uint32_t *p_sg_p = signal_struct->p_app_signal;
    esp_err_t err_status = signal_struct->esp_err_status;
    esp_zb_app_signal_type_t sig_type = *p_sg_p;

    switch (sig_type) {
    case ESP_ZB_ZDO_SIGNAL_SKIP_STARTUP:
        ESP_LOGI(TAG, "Zigbee Stack Initialized. Starting Commissioning...");
        esp_zb_bdb_start_top_level_commissioning(ESP_ZB_BDB_MODE_INITIALIZATION);
        break;
    case ESP_ZB_BDB_SIGNAL_DEVICE_FIRST_START:
    case ESP_ZB_BDB_SIGNAL_DEVICE_REBOOT:
        if (err_status != ESP_OK) {
            ESP_LOGW(TAG, "Stack start failed: %s", esp_err_to_name(err_status));
            return;
        }
        if (esp_zb_bdb_is_factory_new()) {
            ESP_LOGI(TAG, "Factory New Device. Steering...");
            esp_zb_bdb_start_top_level_commissioning(ESP_ZB_BDB_MODE_NETWORK_STEERING);
            // Blink blue to indicate pairing mode
            if (led_strip) {
                led_strip_set_pixel_hsv(led_strip, 0, 240, 255, 50); // Blue
                led_strip_refresh(led_strip);
            }
        } else {
            ESP_LOGI(TAG, "Device Rebooted.");
            // Restore state would go here if saved to NVS, 
            // for now, default off or green to show alive
            if (led_strip) {
                led_strip_set_pixel_hsv(led_strip, 0, 120, 255, 20); // Green pulse
                led_strip_refresh(led_strip);
                vTaskDelay(pdMS_TO_TICKS(500));
                update_led(); // Restore attribute state
            }
        }
        break;
    case ESP_ZB_BDB_SIGNAL_STEERING:
        if (err_status == ESP_OK) {
            ESP_LOGI(TAG, "Joined network successfully!");
            // Quick green flash
             if (led_strip) {
                led_strip_set_pixel_hsv(led_strip, 0, 120, 255, 100);
                led_strip_refresh(led_strip);
                vTaskDelay(pdMS_TO_TICKS(1000));
                update_led();
            }
        } else {
            ESP_LOGW(TAG, "Network steering failed, retrying...");
            esp_zb_scheduler_alarm((esp_zb_callback_t)esp_zb_bdb_start_top_level_commissioning, ESP_ZB_BDB_MODE_NETWORK_STEERING, 1000);
        }
        break;
    default:
        ESP_LOGI(TAG, "ZDO signal: %s (0x%x)", esp_zb_zdo_signal_to_string(sig_type), sig_type);
        break;
    }
}

static void esp_zb_task(void *pvParameters) {
    esp_zb_cfg_t zb_nwk_cfg = {
        .esp_zb_role = ESP_ZB_DEVICE_TYPE_ROUTER,
        .install_code_policy = false,
        .nwk_cfg = {
            .zed_cfg = {
                .ed_timeout = ESP_ZB_ED_AGING_TIMEOUT_64MIN,
                .keep_alive = 3000,
            },
        },
    };
    esp_zb_init(&zb_nwk_cfg);
    
    // --- On/Off Cluster ---
    esp_zb_on_off_cluster_cfg_t on_off_cfg = { .on_off = g_on_off };
    esp_zb_attribute_list_t *on_off_attr_list = esp_zb_on_off_cluster_create(&on_off_cfg);

    // --- Level Control Cluster ---
    esp_zb_level_cluster_cfg_t level_cfg = { .current_level = g_level };
    esp_zb_attribute_list_t *level_attr_list = esp_zb_level_cluster_create(&level_cfg);

    // --- Color Control Cluster ---
    // Manually create attribute list since helper might be missing/different
    esp_zb_attribute_list_t *color_attr_list = esp_zb_zcl_attr_list_create(ESP_ZB_ZCL_CLUSTER_ID_COLOR_CONTROL);
    
    // Add Hue (0x0000)
    esp_zb_cluster_add_attr(color_attr_list, ESP_ZB_ZCL_CLUSTER_ID_COLOR_CONTROL, 
                            ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_HUE_ID, 
                            ESP_ZB_ZCL_ATTR_TYPE_U8, ESP_ZB_ZCL_ATTR_ACCESS_READ_WRITE | ESP_ZB_ZCL_ATTR_ACCESS_REPORTING, 
                            &g_hue);
    
    // Add Saturation (0x0001)
    esp_zb_cluster_add_attr(color_attr_list, ESP_ZB_ZCL_CLUSTER_ID_COLOR_CONTROL, 
                            ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_SATURATION_ID, 
                            ESP_ZB_ZCL_ATTR_TYPE_U8, ESP_ZB_ZCL_ATTR_ACCESS_READ_WRITE | ESP_ZB_ZCL_ATTR_ACCESS_REPORTING, 
                            &g_sat);

    // Add Color Mode (0x0008) - Read Only
    uint8_t color_mode = 0x00; // Hue and Saturation
    esp_zb_cluster_add_attr(color_attr_list, ESP_ZB_ZCL_CLUSTER_ID_COLOR_CONTROL, 
                            ESP_ZB_ZCL_ATTR_COLOR_CONTROL_COLOR_MODE_ID, 
                            ESP_ZB_ZCL_ATTR_TYPE_8BIT_ENUM, ESP_ZB_ZCL_ATTR_ACCESS_READ_ONLY, 
                            &color_mode);

    
    // Add missing attributes if create doesn't add them by default (sometimes SDK needs explicit add)
    // For standard HA color light, these are usually sufficient.

    // --- Cluster List ---
    esp_zb_cluster_list_t *cluster_list = esp_zb_zcl_cluster_list_create();
    esp_zb_cluster_list_add_on_off_cluster(cluster_list, on_off_attr_list, ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);
    esp_zb_cluster_list_add_level_cluster(cluster_list, level_attr_list, ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);
    esp_zb_cluster_list_add_color_control_cluster(cluster_list, color_attr_list, ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);
    
    // --- Basic & Identify ---
    esp_zb_basic_cluster_cfg_t basic_cfg = { .zcl_version = 0x03, .power_source = ESP_ZB_ZCL_BASIC_POWER_SOURCE_MAINS_SINGLE_PHASE };
    esp_zb_attribute_list_t *basic_attr_list = esp_zb_basic_cluster_create(&basic_cfg);
    esp_zb_basic_cluster_add_attr(basic_attr_list, ESP_ZB_ZCL_ATTR_BASIC_MANUFACTURER_NAME_ID, (void *)"\x0A" ESP_MANUFACTURER_NAME);
    esp_zb_basic_cluster_add_attr(basic_attr_list, ESP_ZB_ZCL_ATTR_BASIC_MODEL_IDENTIFIER_ID, (void *)"\x0A" ESP_MODEL_IDENTIFIER);
    esp_zb_cluster_list_add_basic_cluster(cluster_list, basic_attr_list, ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);

    esp_zb_identify_cluster_cfg_t identify_cfg = { .identify_time = 0 };
    esp_zb_attribute_list_t *identify_attr_list = esp_zb_identify_cluster_create(&identify_cfg);
    esp_zb_cluster_list_add_identify_cluster(cluster_list, identify_attr_list, ESP_ZB_ZCL_CLUSTER_SERVER_ROLE);

    // --- Endpoint ---
    esp_zb_ep_list_t *ep_list = esp_zb_ep_list_create();
    esp_zb_endpoint_config_t endpoint_config = {
        .endpoint = HA_ENDPOINT,
        .app_profile_id = ESP_ZB_AF_HA_PROFILE_ID,
        .app_device_id = ESP_ZB_HA_COLOR_DIMMABLE_LIGHT_DEVICE_ID, // 0x0102
        .app_device_version = 0
    };
    esp_zb_ep_list_add_ep(ep_list, cluster_list, endpoint_config);

    // Register
    esp_zb_device_register(ep_list);

    // Set Action Callback for attribute updates
    esp_zb_core_action_handler_register(zb_action_handler);

    esp_zb_start(false); 
    esp_zb_stack_main_loop();
}

static void reset_button_task(void *pvParameters) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << BOOT_BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf);

    ESP_LOGI(TAG, "Button task started. Hold BOOT (GPIO9) for 3s to reset Zigbee.");

    while (1) {
        if (gpio_get_level(BOOT_BUTTON_PIN) == 0) {
            ESP_LOGW(TAG, "Button pressed, hold to reset...");
            int hold_count = 0;
            while (gpio_get_level(BOOT_BUTTON_PIN) == 0) {
                vTaskDelay(pdMS_TO_TICKS(100));
                hold_count += 100;
                if (hold_count >= BUTTON_HOLD_TIME_MS) {
                    ESP_LOGW(TAG, "Factory Reset Triggered! Rebooting...");
                    if (led_strip) {
                        led_strip_set_pixel_hsv(led_strip, 0, 0, 255, 100); // Red
                        led_strip_refresh(led_strip);
                    }
                    esp_zb_factory_reset(); 
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void app_main(void) {
    // 1. Init LED Strip
    ESP_LOGI(TAG, "Initializing LED Strip on GPIO %d...", LED_STRIP_GPIO);
    led_strip_config_t strip_config = {
        .strip_gpio_num = LED_STRIP_GPIO,
        .max_leds = LED_STRIP_LEDS, 
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB, // Common for WS2812
        .led_model = LED_MODEL_WS2812,
        .flags.invert_out = false,
    };
    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000, // 10MHz
        .flags.with_dma = false,
    };
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip));
    
    // Clear LED
    led_strip_clear(led_strip);

    // 2. Zigbee Platform Config
    esp_zb_platform_config_t config = {
        .radio_config = { .radio_mode = ZB_RADIO_MODE_NATIVE },
        .host_config = { .host_connection_mode = ZB_HOST_CONNECTION_MODE_NONE },
    };
    ESP_ERROR_CHECK(esp_zb_platform_config(&config));

    // 3. Start Tasks
    xTaskCreate(reset_button_task, "reset_button", 2048, NULL, 10, NULL);
    xTaskCreate(esp_zb_task, "Zigbee_main", 4096, NULL, 5, NULL);
}
