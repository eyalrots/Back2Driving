#ifndef __BUTTONS_H__
#define __BUTTONS_H__

#include <stdio.h>
#include <unistd.h>
#include <stdint.h>
#include <lgpio.h>
#include "shared.h"

typedef struct {
    int pin;
    uint64_t press_start_time;
    double last_press_duration_ms;
} ButtonState;

/* Byttons */
#define BUTTON_1 17
#define BUTTON_2 27

int buttons_main_operation();
void buttons_check_operation();
int setup_button(int handle, ButtonState *btn);
int register_press(ButtonState *btn);

#endif
