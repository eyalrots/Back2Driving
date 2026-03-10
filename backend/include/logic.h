#ifndef __LOGIC_H__
#define __LOGIC_H__

#include <stdbool.h>
#include "./input.h"

int calculate_break_force(const float *sensor_data, int num_samples,
                          float drop_threshold, float *max_force);

#endif /* __LOGIC_H__ */