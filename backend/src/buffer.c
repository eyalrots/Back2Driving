#include "../include/buffer.h"

int setup_and_check(int handle)
{
    struct sched_param param;
    int status = 0;

    /* Elevate thread to Real-Time Priority */
    /* Get the maximum priority allowed for the FIFO real-time scheduler */
    status = sched_get_priority_max(SCHED_FIFO);
    if (status == -1) {
        printf("Error getting max priority: %s\n", strerror(errno));
        goto ret;
    }
    param.sched_priority = status;
    
    /* Apply the rael-time scheduling policy to this thread (0 means current
     * thread) */
    status = sched_setscheduler(0, SCHED_FIFO, &param);
    if (status < 0) {
        printf("Error setting real-time priority (did you use sudo?): %s\n",
               strerror(errno));
        goto ret;
    }

    /* Check read action */
    status = lgGpioRead(handle, DOUT_PIN);
    if (status < 0) {
        printf("Failed to read pin %d: %s\n", DOUT_PIN, lguErrorText(status));
        goto ret;
    }

    status = 0;
ret:
    return status;
}

int read_hx711_data(int handle, uint32_t *rx_buffer)
{
    if (!rx_buffer) {
		printf("Buffer is null on load cell.\n");
        return -1;
	}
    struct sched_param param;
    int status = 0;
    int i = 0;
    *rx_buffer = 0;

    /* Setup priority and GPIO pins */
    if (setup_and_check(handle) < 0) {
		printf("Setup failed on load cell.\n");
        status = -1;
        goto ret;
	}

    /* Wait for ready signal - polling */
    /* The HX711 pulls DOUT low when data is ready */
    while (lgGpioRead(handle, DOUT_PIN) == 1)
        ;

    /* get 24 bits of data */
    for (i = 0; i < 24; i++) {
        /* Pulse clk high */
        status = lgGpioWrite(handle, SCK_PIN, 1);
        if (status < 0) {
            printf("Failed to set pin %d high: %s\n", SCK_PIN, lguErrorText(status));
            goto ret;
		}

        /* Shift the data variable by 1 to make room */
        /* Then read the Dout pin and append it to the rightmost bit */
		int val = lgGpioRead(handle, DOUT_PIN);
		if (val < 0) {
			printf("GPIO READ ERROR CODE: %d\n", val);
			return -1;
		}
        (*rx_buffer) = ((*rx_buffer) << 1) | val;
		// printf("buffer is: 0x%06X on clk number %d\n", *rx_buffer, i);

        /* Pulse clk low */
        status = lgGpioWrite(handle, SCK_PIN, 0);
        if (status < 0) {
            printf("Failed to set pin %d low: %s\n", SCK_PIN,
                   lguErrorText(status));
            goto ret;
		}
    }

    /* Send another pulse to set amplification */
    status = lgGpioWrite(handle, SCK_PIN, 1);
    if(status < 0) {
        printf("Failed to set pin %d high: %s\n", SCK_PIN,
               lguErrorText(status));
        goto ret;
    }
    status = lgGpioWrite(handle, SCK_PIN, 0);
    if (status < 0) {
        printf("Failed to set pin %d low: %s\n", SCK_PIN, lguErrorText(status));
        goto ret;
    }

    /* Restore priority to normal */
    param.sched_priority = 0;
    status = sched_setscheduler(0, SCHED_OTHER, &param);
    if (status < 0) {
        printf("Failed to restore normal priority: %s\n", strerror(errno));
        goto ret;
    }

    /* The HX711 returns a 24-bit Two's Complement signed integer.
     *  If the 24th bit (the sign bit) is a 1, we must fill the top 8 bits of
     * our 32-bit variable with 1s so C understands it is a negative number.
     */
    if (*rx_buffer & 0x800000) {
        *rx_buffer |= 0xFF000000;
	}
        
	status = 0;
ret:
    return status;
}