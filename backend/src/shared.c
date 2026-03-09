#include "../include/shared.h"

int create_or_connect(shared_data_t **shared_data)
{
    key_t key;
    int shmid;

    key = ftok("/home", 'R');
    if (key == -1) {
        perror("key");
        return -1;
	}
    shmid = shmget(key, 1024, 666 | IPC_CREAT);
    if (shmid == -1) {
        perror("shmget");
        return -1;
    }
    
	*shared_data = shmat(shmid, (void *)0, 0);
	if (*shared_data == MAP_FAILED) {
		perror("shmat");
		return -1;
    }

    memset(*shared_data, 0, sizeof(shared_data_t));

    return 0;
}

int writer_1(shared_data_t *shared_data, sensor_data_t *new_data)
{
    if (!shared_data || !new_data)
		return -1;
    
    shared_data->flags[0] = 1;
    shared_data->turn = 1;

    /* Busy wait */
    while (shared_data->flags[1] && shared_data->turn)
        ;

    /* Enter critical section */
    shared_data->load_cell_sensor = *new_data;
    /* Finish critical section */

    shared_data->flags[0] = 0;

    return 0;
}

int writer_2(shared_data_t *shared_data, sensor_data_t *new_data)
{
    if (!shared_data || !new_data)
        return -1;

    shared_data->flags[1] = 1;
    shared_data->turn = 0;

    /* Busy wait */
    while (shared_data->flags[0] && !shared_data->turn)
        ;

    /* Enter critical section */
    shared_data->hall_effect_sensor = *new_data;
    /* Finish critical section */

    shared_data->flags[1] = 0;

    return 0;
}

int destroy(shared_data_t *shared_data)
{
    if (shmdt(shared_data) == -1) {
        perror("shmdt");
        return -1;
    }
    return 0;
}