#include "../include/butons.h"

/* Temporary Global Variables */
uint64_t press_start_time = 0;
double last_press_duration_ms = 0.0;

void button_callback(int e, lgGpioAlert_p alerts, void *userdata) {
	// Cast the generic userdata pointer back to our ButtonState struct
    ButtonState *btn = (ButtonState *)userdata; 

    for (int i = 0; i < e; i++) {
        int level = alerts[i].report.level;
        uint64_t timestamp = alerts[i].report.timestamp; 

        if (level == 1) {
            // BUTTON PRESSED
            btn->press_start_time = timestamp;
            printf("GPIO %d pressed.\n", btn->pin); // Optional debug

        } else if (level == 0) {
            // BUTTON RELEASED
            if (btn->press_start_time > 0) {
                uint64_t duration_ns = timestamp - btn->press_start_time;
                btn->last_press_duration_ms = (double)duration_ns / 1000000.0;
                
                printf("GPIO %d released! Duration: %.2f ms\n", btn->pin, btn->last_press_duration_ms);
                
                btn->press_start_time = 0; // Reset for next press
                
                // -> Call your system operation function here <-
                // Example: operate_system(btn->pin, btn->last_press_duration_ms);
            }
        }
    }
}

int setup_button(int handle, ButtonState *btn) {
    // Claim the pin
    if (lgGpioClaimAlert(handle, 0, LG_BOTH_EDGES, btn->pin, -1) < 0) {
        printf("Failed to claim GPIO %d\n", btn->pin);
        return -1;
    }
    
    // Set debounce (10ms)
    lgGpioSetDebounce(handle, btn->pin, 10000); 
    
    // Register the callback, passing the specific struct as 'userdata'
    lgGpioSetAlertsFunc(handle, btn->pin, button_callback, btn); 
    
    return 0;
}

int buttons_main_operation() {
    // Initialize our two independent buttons
    ButtonState button_1 = {BUTTON_1, 0, 0.0};
    ButtonState button_2 = {BUTTON_2, 0, 0.0};

    // Open the gpiochip (Use 4 if on Pi 5, or 0 for older Pi's)
    int handle = lgGpiochipOpen(0); 
    if (handle < 0) {
        printf("Failed to open gpiochip. Run with sudo.\n");
        return -1;
    }

    // Pass the buttons to the general setup function
    setup_button(handle, &button_1);
    setup_button(handle, &button_2);

    printf("System ready. Press buttons simultaneously or independently...\n");

    // Main system loop
    while (1) {
        sleep(1);
        
        // Example: The main thread can independently read the latest values at any time
        printf("Current stored durations - B1: %.2fms, B2: %.2fms\n", 
               button_1.last_press_duration_ms, button_2.last_press_duration_ms);
    }

    lgGpiochipClose(handle);
    return 0;
}

void buttons_on_press(int e, lgGpioAlert_p alerts, void *userdata)
{
    for (i = 0; i < e; i++) {
        printf("u=%d t=%" PRIu64 " c=%d g=%d l=%d f=%d (%d of %d)\n", userdata,
               evt[i].report.timestamp, evt[i].report.chip, evt[i].report.gpio,
               evt[i].report.level, evt[i].report.flags, i + 1, e);
    }
}

void buttons_check_operation()
{
    // Open the gpiochip (Use 4 if on Pi 5, or 0 for older Pi's)
    int handle = lgGpiochipOpen(0);
    if (handle < 0) {
        printf("Failed to open gpiochip. Run with sudo.\n");
        return -1;
    }

    // Claim the pin
    if (lgGpioClaimAlert(handle, 0, LG_BOTH_EDGES, BUTTON_1, -1) < 0) {
        printf("Failed to claim GPIO %d\n", BUTTON_1);
        return -1;
    }

    // Set debounce (10ms)
    lgGpioSetDebounce(handle, BUTTON_1, 10000);

    // Register the callback, passing the specific struct as 'userdata'
    lgGpioSetAlertsFunc(handle, BUTTON_1, button_callback);

    // Claim the pin
    if (lgGpioClaimAlert(handle, 0, LG_BOTH_EDGES, BUTTON_2, -1) < 0) {
        printf("Failed to claim GPIO %d\n", BUTTON_2);
        return -1;
    }

    // Set debounce (10ms)
    lgGpioSetDebounce(handle, BUTTON_2, 10000);

    // Register the callback, passing the specific struct as 'userdata'
    lgGpioSetAlertsFunc(handle, BUTTON_2, button_callback);
}

