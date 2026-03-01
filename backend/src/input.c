#include "../include/input.h"

int setup(int * gpio_handle, int * spi_handle)
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
        printf("Failed to open SPI connection: %s\n", lguErrorText(status));
        goto ret;
    }
    *spi_handle = status;
    
	status = 0;
ret:
    return status;
}

int get_spi_data(uint8_t *tx_buf, uint8_t *rx_buf, int handle)
{
    /* The function returns status < 0 for error and data read form SPI otherwise */
    
    int status = 0;
    if (!tx_buf || !rx_buf) {
        printf("Buffers are not defined.\n");
        goto ret;
    }

    /* set Tx buffer value -> move for calling function later! */
    /* assuming space is allocated for buffer */
    /* byte 1: start bit - bit 2, diff - bit 1, d2 - bit 0 => 0000010_D2 */
    tx_buf[0] =
        (~TX_BYTE_1_ZERO & START_BIT) | ~SGL_DIFF | (D2 & (ADC_CHANNEL >> 2));
    /* byte 2: D1 - bit 7, D0 - bit 6 => D1_D0_000000 */
    tx_buf[1] = (D1 | D0) & ~TX_BYTE_2_ZERO;
    /* byte 3: all zero */
    tx_buf[2] = 0x00;

    status = lgSpiXfer(handle, (const char *)tx_buf, (char *)rx_buf, 3);
    if (status < 0) {
        printf("Error transfering data on SPI: %s\n", lguErrorText(status));
        goto ret;
    }

    /* set return value to spi data */
    status = rx_buf[1] & RX_HIGH_4;
    status = (status << 8) + (rx_buf[2] & RX_LOW_8);

ret:
    return status;
}
