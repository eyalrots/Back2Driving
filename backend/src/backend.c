#include "../include/backend.h"

void *spi_thread_func(void *arg)
{
    int spi_handle = *(int *)arg;
    shared_data_t *shared_data = NULL;

    /* Create or connect to shared memory */
    create_or_connect(&shared_data);
    if (!shared_data)
		return NULL;

    /* Get samples in infinite loop */
    printf("Starting sampling Hall-Effect...\n");
    if (get_spi_data(spi_handle, shared_data) == -1)
        return NULL;

    /* destroy shared memory */
    destroy(shared_data);
    printf("Finished sampling Hall-Effect.\n");

    return NULL;
}

void *hx711_thread_func(void *arg)
{
    int hx711_handle = *(int *)arg;
    shared_data_t *shared_data = NULL;

    /* Create or connect to shared memory */
    create_or_connect(&shared_data);
    if (!shared_data)
        return NULL;

    /* Get samples in infinite loop */
    printf("Starting sampling Load-Cell...\n");
    if (get_hx711_data(hx711_handle, shared_data) == -1)
        return NULL;

    /* destroy shared memory */
    destroy(shared_data);
	printf("Finished sampling Load-Cell.\n");
    
    return NULL;
}

// int main(void)
// {
//     /* handles */
//     int gpio_handle = 0;
//     int spi_handle = 0;

//     /* Threads */
//     pthread_t spi_thread;
//     pthread_t hx711_thread;

//     /* Setup GPIO */
//     if (io_setup(&gpio_handle, &spi_handle) < 0) {
// 		printf("Error opening GPIO or SPI.\n");
//     	return 0;
//     }
//     printf("Setup Complete.\n");
    
//     /* Create two threads for spi and hx711 */
//     if (pthread_create(&spi_thread, NULL, spi_thread_func,
//                        (void *)&spi_handle)) {
//         perror("Error: Failed to create SPI thread.\n");
//     }
//     if (pthread_create(&hx711_thread, NULL, hx711_thread_func,
//                        (void *)&gpio_handle)) {
//         perror("Error: Failed to create HX711 thread.\n");
//     }
//     printf("Created Threads Successfuly.\n");

//     /* Join Created threads */
//     if (pthread_join(spi_thread, NULL)) {
//         perror("Error: Failed to joid SPI thread.\n");
//     }
//     if (pthread_join(hx711_thread, NULL)) {
//         perror("Error: Failed to join HX711 thread.\n");
//     }
//     printf("Joined Threads Successfuly.\n");

//     return 0;
// }

int main(void)
{
	buttons_check_operation();
    
    return 0;
}