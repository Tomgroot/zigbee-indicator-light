idf_component_register(
    SRCS "indicator.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES nvs_flash esp_driver_uart ieee802154 esp_timer led_strip
)
