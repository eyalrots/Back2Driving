#ifndef __SHARED_H__
#define __SHARED_H__

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <semaphore.h>
#include <time.h>

typedef struct sensor_data {
    uint32_t sample;
    uint32_t time_stump;
} sensor_data_t;

typedef struct shared_data {
    sensor_data_t load_cell_sensor;
    sensor_data_t hall_effect_sensor;
    /* Semaphores for synchronization */
    int flags[2];
    int turn;
} shared_data_t;

/* Functions */
int create_or_connect(shared_data_t **shared_data);
int writer_1(shared_data_t *shared_data, sensor_data_t *new_data);
int writer_2(shared_data_t *shared_data, sensor_data_t *new_data);
int destroy(shared_data_t *shared_data);

#endif /* __SHARED_H__ */