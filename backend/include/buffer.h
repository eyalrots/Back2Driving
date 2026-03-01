#ifndef __BUFFER_H__
#define __BUFFER_H__

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>
#include <sched.h>
#include <lgpio.h>

/* SPI Buffer Macros */

#define BUFFER_SIZE 3
#define ADC_CHANNEL 0x00
/* Tx Buffer locations */
/* Byte 1 */
#define START_BIT 0x04
#define SGL_DIFF 0x02
#define D2 0x01
#define TX_BYTE_1_ZERO 0xF8
/* Byte 2 */
#define D1 0x80
#define D0 0x40
#define TX_BYTE_2_ZERO 0x3F

/* Rx Buffer locations*/
/* Byte 1 */
#define RX_HIGH_4 0x0F
/* Byte 2 */
#define RX_LOW_8 0xFF

/* End of SPI */

/* HX711 Functions */

#define DOUT_PIN 0x06
#define SCK_PIN  0x05

int read_hx711_data(int handle, uint32_t *rx_buffer);

/* End of HX711 */

#endif /* __BUFFER_H__ */