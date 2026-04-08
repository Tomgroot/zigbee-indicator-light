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
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "led_strip.h"
#include "esp_zigbee_core.h"
#include "esp_zigbee_cluster.h"
#include "zcl/esp_zigbee_zcl_common.h"
#include "zcl/esp_zigbee_zcl_on_off.h"
#include "zcl/esp_zigbee_zcl_level.h"
#include "zcl/esp_zigbee_zcl_color_control.h"

// Configuration
#define LED_STRIP_GPIO      GPIO_NUM_4   // WS2812B DIN connected to pin 4
#define LED_STRIP_LEDS      1
#define ONBOARD_LED_GPIO    GPIO_NUM_8   // ESP32-H2 DevKit onboard WS2812B
#define BOOT_BUTTON_PIN     GPIO_NUM_9
#define BUTTON_HOLD_TIME_MS 5000

#define HA_ENDPOINT         1
#define ESP_MANUFACTURER_NAME "ZigbeeHive"
#define ESP_MODEL_IDENTIFIER  "IndicatorLight"

static const char *TAG = "ZIGBEE_LIGHT";

// Global LED state
static led_strip_handle_t led_strip;
static SemaphoreHandle_t  g_led_mutex = NULL;
static bool g_on_off = false;
static uint8_t g_level = 254;                                       // 0-254
static uint16_t g_x = ESP_ZB_ZCL_COLOR_CONTROL_CURRENT_X_DEF_VALUE; // CIE XY, 0x0000-0xFEFF
static uint16_t g_y = ESP_ZB_ZCL_COLOR_CONTROL_CURRENT_Y_DEF_VALUE;

static void led_set_hsv(uint8_t h, uint8_t s, uint8_t v) {
    if (!led_strip || !g_led_mutex) return;
    xSemaphoreTake(g_led_mutex, portMAX_DELAY);
    led_strip_set_pixel_hsv(led_strip, 0, h, s, v);
    led_strip_refresh(led_strip);
    xSemaphoreGive(g_led_mutex);
}

static void led_set_rgb(uint8_t r, uint8_t g, uint8_t b) {
    if (!led_strip || !g_led_mutex) return;
    xSemaphoreTake(g_led_mutex, portMAX_DELAY);
    led_strip_set_pixel(led_strip, 0, r, g, b);
    led_strip_refresh(led_strip);
    xSemaphoreGive(g_led_mutex);
}

static void led_off(void) {
    if (!led_strip || !g_led_mutex) return;
    xSemaphoreTake(g_led_mutex, portMAX_DELAY);
    led_strip_clear(led_strip);
    xSemaphoreGive(g_led_mutex);
}

typedef enum {
    EFFECT_PULSE_SLOW = 0,  // blue, ~1.6s period — network searching
    EFFECT_PULSE_FAST = 1,  // blue, ~320ms period — reset pending
} effect_type_t;

// Effect state
static TaskHandle_t           g_effect_task    = NULL;
static volatile bool          g_effect_active  = false;
static volatile effect_type_t g_effect_current = EFFECT_PULSE_SLOW;

static void stop_effect(void) {
    if (!g_effect_task) return;
    g_effect_active = false;
    // Wait for the task to finish its current led_set_hsv call and exit (max step is 20ms)
    vTaskDelay(pdMS_TO_TICKS(40));
    if (g_effect_task) {
        vTaskDelete(g_effect_task);
        g_effect_task = NULL;
    }
}

static void effect_task(void *pvParameters) {
    int16_t bri = 0, dir = 1;

    while (g_effect_active) {
        effect_type_t type = g_effect_current;
        int step_ms = (type == EFFECT_PULSE_FAST) ? 8  : 20;
        int step    = (type == EFFECT_PULSE_FAST) ? 8  : 2;

        led_set_hsv(240, 255, (uint8_t)bri);
        bri += dir * step;
        if (bri >= 80)     { bri = 80; dir = -1; }
        else if (bri <= 0) { bri = 0;  dir =  1; }
        vTaskDelay(pdMS_TO_TICKS(step_ms));
    }
    g_effect_task = NULL;
    vTaskDelete(NULL);
}

static void start_effect(effect_type_t type) {
    // Don't let a slow pulse override an already-running fast pulse
    if (g_effect_task && type == EFFECT_PULSE_SLOW && g_effect_current == EFFECT_PULSE_FAST) return;
    if (g_effect_task) {
        // Task already running — just change speed, no restart needed
        g_effect_current = type;
        return;
    }
    g_effect_current = type;
    g_effect_active  = true;
    xTaskCreate(effect_task, "led_effect", 2048, NULL, 6, &g_effect_task);
}

// Helper to update LED based on global state.
// Color is stored as CIE 1931 XY (Zigbee format) and converted to RGB.
static void update_led(void) {
    if (!g_on_off) {
        led_off();
        return;
    }

    // Convert Zigbee CIE XY (0x0000-0xFFFF → 0.0-1.0) to wide-gamut RGB.
    float x = (float)g_x / 65535.0f;
    float y = (float)g_y / 65535.0f;
    float z = 1.0f - x - y;

    // Y (luminance) from brightness level 0-254
    float Y = (float)g_level / 254.0f;
    float X = (y > 0.001f) ? (Y / y) * x : 0.0f;
    float Z = (y > 0.001f) ? (Y / y) * z : 0.0f;

    // Wide gamut D65 matrix
    float r =  X * 1.656f - Y * 0.355f - Z * 0.255f;
    float g = -X * 0.707f + Y * 1.655f + Z * 0.036f;
    float b =  X * 0.052f - Y * 0.121f + Z * 1.012f;

    // Clamp negatives
    if (r < 0.0f) r = 0.0f;
    if (g < 0.0f) g = 0.0f;
    if (b < 0.0f) b = 0.0f;

    // Normalize if any channel exceeds 1.0
    float max = r > g ? r : g;
    if (b > max) max = b;
    if (max > 1.0f) { r /= max; g /= max; b /= max; }

    led_set_rgb((uint8_t)(r * 255.0f), (uint8_t)(g * 255.0f), (uint8_t)(b * 255.0f));
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
        if (message->attribute.id == ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_X_ID &&
            message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_U16) {
            g_x = message->attribute.data.value ? *(uint16_t *)message->attribute.data.value : 0;
            ESP_LOGI(TAG, "Color X set to %d", g_x);
            update = true;
        }
        else if (message->attribute.id == ESP_ZB_ZCL_ATTR_COLOR_CONTROL_CURRENT_Y_ID &&
                 message->attribute.data.type == ESP_ZB_ZCL_ATTR_TYPE_U16) {
            g_y = message->attribute.data.value ? *(uint16_t *)message->attribute.data.value : 0;
            ESP_LOGI(TAG, "Color Y set to %d", g_y);
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
            start_effect(EFFECT_PULSE_SLOW); // slow blue pulse while searching
        } else {
            ESP_LOGI(TAG, "Device Rebooted.");
            stop_effect();
            led_set_hsv(120, 255, 20); // brief green
            vTaskDelay(pdMS_TO_TICKS(500));
            update_led();
        }
        break;
    case ESP_ZB_BDB_SIGNAL_STEERING:
        if (err_status == ESP_OK) {
            ESP_LOGI(TAG, "Joined network successfully!");
            stop_effect();
            led_set_hsv(120, 255, 100); // solid green
            vTaskDelay(pdMS_TO_TICKS(1000));
            update_led();
        } else {
            ESP_LOGW(TAG, "Network steering failed, retrying...");
            start_effect(EFFECT_PULSE_SLOW); // keep slow blue pulse while retrying
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
        .nwk_cfg.zczr_cfg.max_children = 10,
    };
    esp_zb_init(&zb_nwk_cfg);

    // --- On/Off Cluster ---
    esp_zb_on_off_cluster_cfg_t on_off_cfg = { .on_off = g_on_off };
    esp_zb_attribute_list_t *on_off_attr_list = esp_zb_on_off_cluster_create(&on_off_cfg);

    // --- Level Control Cluster ---
    esp_zb_level_cluster_cfg_t level_cfg = { .current_level = g_level };
    esp_zb_attribute_list_t *level_attr_list = esp_zb_level_cluster_create(&level_cfg);

    // --- Color Control Cluster (XY mode) ---
    // XY mode is what the ZBOSS stack natively handles: when HA sends MoveToColor
    // commands, ZBOSS updates CurrentX/CurrentY and fires ESP_ZB_CORE_SET_ATTR_VALUE_CB_ID.
    esp_zb_color_cluster_cfg_t color_cfg = {
        .current_x           = g_x,
        .current_y           = g_y,
        .color_mode          = 0x01,   // XY mode
        .options             = 0x00,
        .enhanced_color_mode = 0x01,   // XY mode
        .color_capabilities  = 0x0008, // XY supported (matches SDK standard template)
    };
    esp_zb_attribute_list_t *color_attr_list = esp_zb_color_control_cluster_create(&color_cfg);

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
            start_effect(EFFECT_PULSE_FAST);
            int hold_count = 0;
            while (gpio_get_level(BOOT_BUTTON_PIN) == 0) {
                vTaskDelay(pdMS_TO_TICKS(100));
                hold_count += 100;
                if (hold_count >= BUTTON_HOLD_TIME_MS) {
                    ESP_LOGW(TAG, "Factory Reset Triggered! Rebooting...");
                    esp_zb_factory_reset(); // device reboots, effect task dies with it
                }
            }
            // Released before threshold — restore normal state
            stop_effect();
            update_led();
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
    g_led_mutex = xSemaphoreCreateMutex();

    // Clear LED
    led_strip_clear(led_strip);

    // Silence the onboard RGB LED (GPIO 8): send zeros via RMT then hold the
    // data line low permanently so no accidental signal can update the LED.
    {
        led_strip_handle_t onboard_led;
        led_strip_config_t onboard_cfg = {
            .strip_gpio_num = ONBOARD_LED_GPIO,
            .max_leds = 1,
            .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
            .led_model = LED_MODEL_WS2812,
            .flags.invert_out = false,
        };
        led_strip_rmt_config_t onboard_rmt = {
            .clk_src = RMT_CLK_SRC_DEFAULT,
            .resolution_hz = 10 * 1000 * 1000,
            .flags.with_dma = false,
        };
        if (led_strip_new_rmt_device(&onboard_cfg, &onboard_rmt, &onboard_led) == ESP_OK) {
            led_strip_clear(onboard_led);
            led_strip_del(onboard_led);
        }
        gpio_config_t onboard_gpio = {
            .pin_bit_mask = (1ULL << ONBOARD_LED_GPIO),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&onboard_gpio);
        gpio_set_level(ONBOARD_LED_GPIO, 0);
    }

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
