#ifndef BOSE_CONNECT_APP_LINUX__MAIN_H
#define BOSE_CONNECT_APP_LINUX__MAIN_H

int get_socket(char *address);

static int do_get_battery_level(char *address);

static int do_get_device_id(char *address);

static int do_get_device_status(char *address);

static int do_get_firmware_version(char *address);

static int do_get_paired_devices(char *address);

static int do_get_serial_number(char *address);

#endif //BOSE_CONNECT_APP_LINUX__MAIN_H
