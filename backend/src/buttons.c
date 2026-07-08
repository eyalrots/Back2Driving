#include "../include/buttons.h"

/* Temporary Global Variables */
uint64_t press_start_time = 0;
double last_press_duration_ms = 0.0;

void button_callback(int e, lgGpioAlert_p alerts, void *userdata) {
	// Cast the generic userdata pointer back to our ButtonState struct
    ButtonState *btn = (ButtonState *)userdata; 

	sensor_data_t btn_data = {};

    for (int i = 0; i < e; i++) {
        int level = alerts[i].report.level;
        uint64_t timestamp = alerts[i].report.timestamp; 

        if (level == 1) {
            // BUTTON PRESSED
            btn->press_start_time = timestamp;
			register_press(btn, 1);
            //printf("GPIO %d pressed.\n", btn->pin); // Optional debug

        } else if (level == 0) {
            // BUTTON RELEASED
            if (btn->press_start_time > 0) {
                uint64_t duration_ns = timestamp - btn->press_start_time;
                btn->last_press_duration_ms = (double)duration_ns / 1000000.0;
                
                //printf("GPIO %d released! Duration: %.2f ms\n", btn->pin, btn->last_press_duration_ms);
                
                btn->press_start_time = 0; // Reset for next press
                
                // -> Call your system operation function here <-
                // Example: operate_system(btn->pin, btn->last_press_duration_ms);
				register_press(btn, 0);
            }
        }
    }
}

int register_press(ButtonState *btn, int dir) {
	if (!btn)
		return -1;

	//printf("registering press...\n");

	shared_data_t *shared_data = NULL;

    /* Create or connect to shared memory */
    create_or_connect(&shared_data);
    if (!shared_data)
        return -1;

	// sensor_data_t btn_data = {};

	// btn_data.sample = btn->last_press_duration_ms;
	// btn_data.time_stump = btn->press_start_time;

	// if (btn->pin == BUTTON_1) {
	// 	printf("registering on button 1.\n");
	// 	writer_1(shared_data, &btn_data);
	// } else if (btn->pin == BUTTON_2) {
	// 	writer_2(shared_data, &btn_data);
	// 	printf("registering on button 2.\n");
	// }

	if (btn->pin == BUTTON_1) {
		shared_data->flags[0] = dir;
	} else if (btn->pin == BUTTON_2) {
		shared_data->flags[1] = dir;
	}

	//printf("Press registered: %d.\n", shared_data->flags[0]);
	//printf("Button 1: %d :: Button 2: %d.\n", shared_data->load_cell_sensor.sample, shared_data->hall_effect_sensor.sample);

	return 0;
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

    //printf("System ready. Press buttons simultaneously or independently...\n");

    // Main system loop
    while (1) {
        sleep(1);
        
        // Example: The main thread can independently read the latest values at any time
        //printf("Current stored durations - B1: %.2fms, B2: %.2fms\n", 
               button_1.last_press_duration_ms, button_2.last_press_duration_ms);
    }

    lgGpiochipClose(handle);
    return 0;
}

void buttons_on_press(int e, lgGpioAlert_p evt, void *userdata)
{
    int i = 0;
    for (i = 0; i < e; i++) {
        // printf("t=%" PRIu64 " c=%d g=%d l=%d f=%d (%d of %d)\n",
        //        evt[i].report.timestamp, evt[i].report.chip, evt[i].report.gpio,
        //        evt[i].report.level, evt[i].report.flags, i + 1, e);
    }
}

void buttons_check_operation()
{
    // Open the gpiochip (Use 4 if on Pi 5, or 0 for older Pi's)
    int handle = lgGpiochipOpen(0);
    if (handle < 0) {
        printf("Failed to open gpiochip. Run with sudo.\n");
        return;
    }

    // Claim the pin
    if (lgGpioClaimAlert(handle, 0, LG_BOTH_EDGES, BUTTON_1, -1) < 0) {
        printf("Failed to claim GPIO %d\n", BUTTON_1);
        return;
    }

    // Set debounce (10ms)
    lgGpioSetDebounce(handle, BUTTON_1, 10000);

    // Register the callback, passing the specific struct as 'userdata'
    lgGpioSetAlertsFunc(handle, BUTTON_1, buttons_on_press, NULL);

    // Claim the pin
    if (lgGpioClaimAlert(handle, 0, LG_BOTH_EDGES, BUTTON_2, -1) < 0) {
        printf("Failed to claim GPIO %d\n", BUTTON_2);
        return;
    }

    // Set debounce (10ms)
    lgGpioSetDebounce(handle, BUTTON_2, 10000);

    // Register the callback, passing the specific struct as 'userdata'
    lgGpioSetAlertsFunc(handle, BUTTON_2, buttons_on_press, NULL);

	while (1) {
		sleep(1);
	}

	lgGpiochipClose(handle);
}

