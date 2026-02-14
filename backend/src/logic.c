#include "../include/logic.h"

int calculate_break_force(const float *sensor_data, int num_samples,
                          float drop_threshold, float* max_force)
{
    if (sensor_data == NULL || num_samples <= 0) {
        goto bad_ret;
    }

    float local_max_force = 0;
    float current_force = 0;
    float current_drop_level = 0;
    bool break_detected = false;
	int i = 0;

    for (i = 0; i < num_samples; i++) {
        current_force = sensor_data[i];

        /* Track the highest force seen so far */
        if (current_force > local_max_force) {
            local_max_force = current_force;
        }

        /*  Detect a drop within theshold of break */
        if (local_max_force > 0) {
            current_drop_level = local_max_force * (1 - drop_threshold);
            if (current_force < current_drop_level) {
                break_detected = true;
                break;
			}
        }
    }

    if (break_detected) {
        *max_force = local_max_force;
        goto good_ret;
    } else {
        *max_force = -1;
        goto bad_ret;
	}
bad_ret:
    return 1;
good_ret:
    return 0;
}