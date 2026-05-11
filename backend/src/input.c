#include "../include/input.h"

int io_setup(int *gpio_handle, int *spi_handle)
{
    int status = 0;
    if (!gpio_handle || !spi_handle) {
        printf("One of the handles is NULL.\n");
        status = -1;
        goto ret;
    }

    /* Open GPIO chip */
    status = lgGpiochipOpen(0);
    if (status < 0) {
        printf("Failed to open GPIO chip: %s\n", lguErrorText(status));
        goto ret;
    }
    *gpio_handle = status;

    /* Claim SCK_PIN as output */
    status = lgGpioClaimOutput(*gpio_handle, 0, SCK_PIN, 0);
    if (status < 0) {
        printf("Failed to claim pin %d as output: %s\n", SCK_PIN,
               lguErrorText(status));
        return status;
    }

    /* Claim DOUT_PIN as input */
    status = lgGpioClaimInput(*gpio_handle, 0, DOUT_PIN);
    if (status < 0) {
        printf("Failed to claim pin %d as input: %s\n", DOUT_PIN,
               lguErrorText(status));
        goto ret;
    }

    /* Open SPI component */
    status = lgSpiOpen(SPI_DEV, SPI_CHAN, SPI_BAUD, 0);
    if (status < 0) {
        printf("Failed to open SPI connection (error: %d): %s\n", status, lguErrorText(status));
        goto ret;
    }
    *spi_handle = status;

    status = 0;
ret:
    return status;
}

int inner_loop_spi(uint8_t *tx_buf, uint8_t *rx_buf, int handle)
{
    /* The function returns status < 0 for error and data read form SPI
     * otherwise */

    if (!tx_buf || !rx_buf) {
        printf("Buffers are not defined.\n");
        goto ret;
    }

    int status = 0;
    int sample_val = 0;

    /* set Tx buffer value:
     * byte 1: 0x04 is the start bit (bit 2). Shift SGL_DIFF to bit 1, extract
     * D2 into bit 0
     */
    tx_buf[0] = START_BIT | SGL_DIFF | ((ADC_CHANNEL >> 2) & D2);

    /* byte 2: Extract D1 and D0 (the lowest 2 bits of the channel), shift left
     * to bits 7 and 6
     */
    tx_buf[1] = (ADC_CHANNEL & D1_0) << 6;

    /* byte 3: all zero (don't care bits) */
    tx_buf[2] = 0x00;

    /* Transfer 3 bytes simultaneously */
    status = lgSpiXfer(handle, (const char *)tx_buf, (char *)rx_buf, 3);
    if (status < 0) {
        printf("Error transfering data on SPI (handle-%d): %s\n", handle, lguErrorText(status));
        goto ret;
    }

    /*
     * Reconstruct 12-bit sample from rx_buf.
     * Ensure we treat rx_buf as unsigned to prevent sign-extension errors.
     */
    sample_val = ((uint8_t)rx_buf[1] & RX_HIGH_4);
    sample_val = (sample_val << 8) + ((uint8_t)rx_buf[2] & RX_LOW_8);
ret:
    return sample_val;
}

int get_spi_data(int handle, shared_data_t *shared_data)
{
    if (!shared_data) {
        return -1;
    }

    uint8_t tx_buf[3] = {0, 0, 0};
    uint8_t rx_buf[3] = {0, 0, 0};
    sensor_data_t hall_effect_data;
    memset(&hall_effect_data, 0, sizeof(hall_effect_data));

    while (1) {
        hall_effect_data.sample = inner_loop_spi(tx_buf, rx_buf, handle);
        if ((int)hall_effect_data.sample == -1)
            return -1;
        /* NOTE: take time stump */
        writer_2(shared_data, &hall_effect_data);
		printf("hall: %d :: ", shared_data->hall_effect_sensor.sample);
		sleep(1);
	}
}

int get_hx711_data(int handle, shared_data_t *shared_data)
{
    if (!shared_data) {
        return -1;
	}

    sensor_data_t load_cell_data;
    memset(&load_cell_data, 0, sizeof(load_cell_data));
    while (1) {
        if (read_hx711_data(handle, &(load_cell_data.sample)) == -1)
            return -1;
        /* NOTE: take time stump */
        writer_1(shared_data, &load_cell_data);
		printf("Laod: %d\n", load_cell_data.sample);
		sleep(1);
    }

    return 0;
}

// int get_button_data(shared_data_t *shared_data, ButtonState *btn_1, ButtonState *btn_2) {
// 	while (1) {
// 		register_press(shared_data, btn_1, btn_2);
// 		printf("registered press.\n");
// 		sleep(1);
// 		printf("Button 1: %d :: Button 2: %d\n", shared_data->load_cell_sensor.sample, shared_data->hall_effect_sensor.sample);
// 	}
// 	return 0;
// }
