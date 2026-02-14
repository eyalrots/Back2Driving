#include "../include/input.h"

void print_func(void)
{
    printf("Hello World!\n");
}

int test_gpio(void)
{
    int h;
    int status;
    lgChipInfo_t chip_info;
    lgLineInfo_t lInfo;

    h = lgGpiochipOpen(0);
    if (h < 0) {
        goto ret;
    }
    status = lgGpioGetChipInfo(h, &chip_info);

    if (status == LG_OKAY) {
        printf("lines=%d name=%s label=%s\n", chip_info.lines, chip_info.name,
               chip_info.label);
    }

    status = lgGpioGetLineInfo(h, 5, &lInfo);

    if (status == LG_OKAY) {
        printf("lFlags=%d name=%s user=%s\n", lInfo.lFlags, lInfo.name,
               lInfo.user);
    }
ret:
    return h;
}