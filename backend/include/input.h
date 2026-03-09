#ifndef __INPUT_H__
#define __INPUT_H__

#include <string.h>
#include "buffer.h"
#include "shared.h"

/* Parameters for SPI */
#define SPI_DEV 0 /* hardware SPI bus */
#define SPI_CHAN 0 /* the number of the CE connected to - 0/1 */
#define SPI_BAUD 1000000 /* Baud rate for SPI - sets SCLK speed - 1MHz */

/* Library Fucntions */
int io_setup(int *gpio_handle, int *spi_handle);
int get_spi_data(int handle, shared_data_t *shared_data);
int get_hx711_data(int handle, shared_data_t *shared_data);

#endif /* __INPUT_H__ */