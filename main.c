#include <bluetooth/bluetooth.h>
#include <bluetooth/rfcomm.h>
#include <getopt.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "main.h"
#include "library/based.h"
#include "library/bluetooth.h"
#include "library/util.h"

static void usage() {
    const char *message =
            "Usage: %s [options] <address>\n"

            "\t-h, --help\n"
            "\t\tPrint the help message.\n"

            "\t-i, --info\n"
            "\t\tPrint all the device information.\n"

            "\t-d, --device-status\n"
            "\t\tPrint the device status information. This includes its name,"
            " language,\n"
            "\t\tvoice-prompts, auto-off and noise cancelling settings.\n"

            "\t-f, --firmware-version\n"
            "\t\tPrint the firmware version on the device.\n"

            "\t-s, --serial-number\n"
            "\t\tPrint the serial number of the device.\n"

            "\t-b, --battery-level\n"
            "\t\tPrint the battery level of the device as a percent.\n"

            "\t-a, --paired-devices\n"
            "\t\tPrint the devices currently connected to the device.\n"
            "\t\t!: indicates the current device\n"
            "\t\t*: indicates other connected devices\n"

            "\t--device-id\n"
            "\t\tPrint the device id followed by the index revision.\n"

            "\t-n <name>, --name=<name>\n"
            "\t\tChange the name of the device.\n"

            "\t-o <minutes>, --auto-off=<minutes>\n"
            "\t\tChange the auto-off time.\n"
            "\t\tminutes: never, 5, 20, 40, 60, 180\n"

            "\t-c <level>, --noise-cancelling=<level>\n"
            "\t\tChange the noise cancelling level.\n"
            "\t\tlevel: high, low, off\n"

            "\t-l <language>, --prompt-language=<language>\n"
            "\t\tChange the voice-prompt language.\n"
            "\t\tlanguage: en, fr, it, de, es, pt, zh, ko, nl, ja, sv\n"

            "\t-v <switch>, --voice-prompts=<switch>\n"
            "\t\tChange whether voice-prompts are on or off.\n"
            "\t\tswitch: on, off\n"

            "\t-p <status>, --pairing=<status>\n"
            "\t\tChange whether the device is pairing.\n"
            "\t\tstatus: on, off\n"

            "\t-e, --self-voice=<level>\n"
            "\t\tChange the self voice level.\n"
            "\t\tlevel: high, medium, low, off\n"

            "\t--connect-device=<address>\n"
            "\t\tAttempt to connect to the device at address.\n"

            "\t--disconnect-device=<address>\n"
            "\t\tDisconnect the device at address.\n"

            "\t--remove-device=<address>\n"
            "\t\tRemove the device at address from the pairing list.\n";

    printf(message, PROGRAM_NAME);
}

int do_get_information(char *address) {
    while (do_get_device_id(address)) { sleep(4); }
    while (do_get_serial_number(address)) { sleep(4); }
    while (do_get_firmware_version(address)) { sleep(4); }
    while (do_get_battery_level(address)) { sleep(4); }
    while (do_get_device_status(address)) { sleep(4); }
    while (do_get_paired_devices(address)) { sleep(4); }

    return 0;
}

static int do_set_name(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    char name_buffer[MAX_NAME_LEN + 1] = {0};
    int status;

    if (strlen(arg) > MAX_NAME_LEN) {
        fprintf(stderr, "Name exceeds %d character maximum. Truncating.\n",
                MAX_NAME_LEN);
        status = 1;
    } else {
        strncpy(name_buffer, arg, MAX_NAME_LEN);
        status = set_name(sock, name_buffer);
    }

    close(sock);
    return status;
}

static int do_set_prompt_language(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    enum PromptLanguage pl;

    if (strcmp(arg, "en") == 0) {
        pl = PL_EN;
    } else if (strcmp(arg, "fr") == 0) {
        pl = PL_FR;
    } else if (strcmp(arg, "it") == 0) {
        pl = PL_IT;
    } else if (strcmp(arg, "de") == 0) {
        pl = PL_DE;
    } else if (strcmp(arg, "es") == 0) {
        pl = PL_ES;
    } else if (strcmp(arg, "pt") == 0) {
        pl = PL_PT;
    } else if (strcmp(arg, "zh") == 0) {
        pl = PL_ZH;
    } else if (strcmp(arg, "ko") == 0) {
        pl = PL_KO;
    } else if (strcmp(arg, "pl") == 0) {
        pl = PL_PL;
    } else if (strcmp(arg, "ru") == 0) {
        pl = PL_RU;
    } else if (strcmp(arg, "nl") == 0) {
        pl = PL_NL;
    } else if (strcmp(arg, "ja") == 0) {
        pl = PL_JA;
    } else if (strcmp(arg, "sv") == 0) {
        pl = PL_SV;
    } else {
        fprintf(stderr, "Invalid prompt language argument: %s\n", arg);
        usage();
        return 1;
    }

    close(sock);
    return set_prompt_language(sock, pl);
}

static int do_set_voice_prompts(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    int on;

    if (strcmp(arg, "on") == 0) {
        on = 1;
    } else if (strcmp(arg, "off") == 0) {
        on = 0;
    } else {
        fprintf(stderr, "Invalid voice prompt argument: %s\n", arg);
        usage();
        return 1;
    }

    close(sock);
    return set_voice_prompts(sock, on);
}

static int do_set_auto_off(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    enum AutoOff ao;

    int parsed = atoi(arg);

    switch (parsed) {
        case AO_5_MIN:
        case AO_20_MIN:
        case AO_40_MIN:
        case AO_60_MIN:
        case AO_180_MIN:
            ao = parsed;
            break;
        default:
            if (strcmp(arg, "never") == 0) {
                ao = AO_NEVER;
            } else {
                fprintf(stderr, "Invalid auto-off argument: %s\n", arg);
                usage();
                return 1;
            }
    }

    close(sock);
    return set_auto_off(sock, ao);
}

static int do_set_noise_cancelling(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    enum NoiseCancelling nc;

    if (strcmp(arg, "high") == 0) {
        nc = NC_HIGH;
    } else if (strcmp(arg, "low") == 0) {
        nc = NC_LOW;
    } else if (strcmp(arg, "off") == 0) {
        nc = NC_OFF;
    } else {
        fprintf(stderr, "Invalid noise cancelling argument: %s\n", arg);
        usage();
        return 1;
    }

    unsigned int device_id;
    unsigned int index;
    int status = get_device_id(sock, &device_id, &index);
    if (status) {
        return status;
    }

    if (!has_noise_cancelling(device_id)) {
        fprintf(stderr, "This device does not have noise cancelling.\n");
        usage();
        return 1;
    }

    close(sock);
    return set_noise_cancelling(sock, nc);
}

static int do_get_device_status(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Status:\n");
    char name[MAX_NAME_LEN + 1];
    enum PromptLanguage promptLanguage;
    enum AutoOff autoOff;
    enum NoiseCancelling noiseCancelling;

    int status = get_device_status(sock, name, &promptLanguage, &autoOff,
                                   &noiseCancelling);
    if (status) {
        return status;
    }
    printf("\tName: %s\n", name);

    char *language = NULL;
    char unknown_language[15];
    switch (promptLanguage & VP_MASK) {
        case PL_EN:
            language = "en";
            break;
        case PL_FR:
            language = "fr";
            break;
        case PL_IT:
            language = "it";
            break;
        case PL_DE:
            language = "de";
            break;
        case PL_ES:
            language = "es";
            break;
        case PL_PT:
            language = "pt";
            break;
        case PL_ZH:
            language = "zh";
            break;
        case PL_KO:
            language = "ko";
            break;
        case PL_NL:
            language = "nl";
            break;
        case PL_JA:
            language = "ja";
            break;
        case PL_SV:
            language = "sv";
            break;
        case PL_RU:
            language = "ru";
            break;
        case PL_PL:
            language = "pl";
            break;
        default:
            sprintf(unknown_language, "Unknown [0x%02X]", promptLanguage);
            language = unknown_language;
            break;
    }
    printf("\tLanguage: %s\n", language);
    printf("\tVoice Prompts: %s\n", promptLanguage & VP_MASK ? "on" : "off");

    printf("\tAuto-Off: ");
    if (autoOff) {
        printf("%d", autoOff);
    } else {
        printf("never");
    }
    printf("\n");

    char *cancellingLevel;
    if (noiseCancelling != NC_DNE) {
        switch (noiseCancelling) {
            case NC_HIGH:
                cancellingLevel = "high";
                break;
            case NC_LOW:
                cancellingLevel = "low";
                break;
            case NC_OFF:
                cancellingLevel = "off";
                break;
            default:
                return 1;
        }
        printf("\tNoise Cancelling: %s\n", cancellingLevel);
    }

    close(sock);
    return 0;
}

static int do_set_pairing(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    enum Pairing p;

    if (strcmp(arg, "on") == 0) {
        p = P_ON;
    } else if (strcmp(arg, "off") == 0) {
        p = P_OFF;
    } else {
        fprintf(stderr, "Invalid pairing argument: %s\n", arg);
        usage();
        return 1;
    }

    close(sock);
    return set_pairing(sock, p);
}

static int do_set_self_voice(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    enum SelfVoice p;

    if (strcmp(arg, "high") == 0) {
        p = SV_HIGH;
    } else if (strcmp(arg, "medium") == 0) {
        p = SV_MEDIUM;
    } else if (strcmp(arg, "low") == 0) {
        p = SV_LOW;
    } else if (strcmp(arg, "off") == 0) {
        p = SV_OFF;
    } else {
        fprintf(stderr, "Invalid self voice argument: %s\n", arg);
        usage();
        return 1;
    }

    close(sock);
    return set_self_voice(sock, p);
}

static int do_get_firmware_version(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Firmware version: ");
    char version[VER_STR_LEN];
    int status = get_firmware_version(sock, version);

    if (status) {
        return status;
    }

    printf("%s\n", version);

    close(sock);
    return 0;
}

static int do_get_serial_number(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Serial number: ");
    char serial[0x100];
    int status = get_serial_number(sock, serial);

    if (status) {
        return status;
    }

    printf("%s\n", serial);

    close(sock);
    return 0;
}

static int do_get_battery_level(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Battery level: ");
    unsigned int level;
    int status = get_battery_level(sock, &level);

    if (status) {
        return status;
    }

    printf("%d\n", level);

    close(sock);
    return 0;
}

static int do_get_paired_devices(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Paired devices: ");
    bdaddr_t devices[MAX_NUM_DEVICES];
    size_t num_devices;
    enum DevicesConnected connected;

    int status = get_paired_devices(sock, devices, &num_devices, &connected);
    if (status) {
        return status;
    }

    unsigned int num_connected;
    switch (connected) {
        case DC_ONE:
            num_connected = 1;
            break;
        case DC_TWO:
            num_connected = 2;
            break;
        default:
            printf("\n\t"
                   "Error: 0x%02X connected devices. Outside of the range "
                   "(0x01 and 0x03)."
                   "\n",
                   connected);
            return 1;
    }
    printf("%lu\n", num_devices);
    printf("\tConnected: %d\n", num_connected);

    size_t i;
    for (i = 0; i < num_devices; ++i) {
        struct Device device;
        status = get_device_info(sock, devices[i], &device);
        if (status) {
            return status;
        }

        char address_converted[18];
        reverse_ba2str(&device.address, address_converted);

        char status_symbol;
        switch (device.status) {
            case DS_THIS:
                status_symbol = '!';
                break;
            case DS_CONNECTED:
                status_symbol = '*';
                break;
            case DS_DISCONNECTED:
                status_symbol = ' ';
                break;
            default:
                return 1;
        }

        printf("\tDevice: %c | %s | %s\n", status_symbol,
               address_converted,
               device.name);
    }
    printf("\t[!] Indicates the current device.\n");
    printf("\t[*] Indicates other connected devices.\n");

    close(sock);
    return 0;
}

static int do_connect_device(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    bdaddr_t bd_address;
    reverse_str2ba(arg, &bd_address);
    int connection = connect_device(sock, bd_address);

    close(sock);
    return connection;
}

static int do_disconnect_device(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    bdaddr_t bd_address;
    reverse_str2ba(arg, &bd_address);
    int disconnection = disconnect_device(sock, bd_address);

    close(sock);
    return disconnection;
}

static int do_remove_device(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    bdaddr_t bd_address;
    reverse_str2ba(arg, &bd_address);
    int removed = remove_device(sock, bd_address);

    close(sock);
    return removed;
}

static int do_get_device_id(char *address) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    printf("Device ID: ");
    unsigned int device_id;
    unsigned int index;
    int status = get_device_id(sock, &device_id, &index);

    if (status) {
        return status;
    }

    printf("0x%04x | Index: %d\n", device_id, index);

    close(sock);
    return 0;
}

static int do_send_packet(char *address, const char *arg) {
    int sock = get_socket(address);
    if (sock == -1) {
        return 1;
    }
    uint8_t send[sizeof(arg) / 2];
    size_t i;
    for (i = 0; arg[i * 2]; ++i) {
        if (str_to_byte(&arg[i * 2], &send[i]) != 0) {
            return 1;
        }
    }

    uint8_t received[MAX_BT_PACK_LEN];
    int received_n = send_packet(sock, send, sizeof(send), received);
    if (received_n < 0) {
        return received_n;
    }

    printf("Received package:\n\t");
    for (i = 0; i < received_n; ++i) {
        printf("%02x ", received[i]);
    }
    printf("\n");

    close(sock);
    return 0;
}

int get_socket(char *address) {
    static const struct timeval send_timeout = {5, 0};
    static const struct timeval receive_timeout = {1, 0};
    int sock = socket(AF_BLUETOOTH, SOCK_STREAM, BTPROTO_RFCOMM);

    if (setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &send_timeout,
                   sizeof(send_timeout)) < 0) {
        perror("Could not set socket send timeout");
        return -1;
    }

    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &receive_timeout,
                   sizeof(receive_timeout)) < 0) {
        perror("Could not set socket receive timeout");
        return -1;
    }

    struct sockaddr_rc sock_address;
    sock_address.rc_family = AF_BLUETOOTH;
    sock_address.rc_channel = BOSE_CHANNEL;
    if (str2ba(address, &sock_address.rc_bdaddr) != 0) {
        fprintf(stderr, "Invalid bluetooth sock_address: %s\n", address);
        return -1;
    }
    if (connect(sock, (struct sockaddr *) &sock_address,
                sizeof(sock_address)) != 0) {
        perror("Could not connect to Bluetooth device");
        return -1;
    }

    int connection = init_connection(sock);
    if (connection) {
        close(sock);
        return -1;
    }

    return sock;
}

int main(int argc, char *argv[]) {
    static const char *short_opt = "hidfsban:n:o:c:l:v:p:e:";
    static const struct option long_opt[] = {
            {"help",              no_argument,       NULL, 'h'},
            {"info",              no_argument,       NULL, 'i'},
            {"device-status",     no_argument,       NULL, 'd'},
            {"firmware-version",  no_argument,       NULL, 'f'},
            {"serial-number",     no_argument,       NULL, 's'},
            {"battery-level",     no_argument,       NULL, 'b'},
            {"paired-devices",    no_argument,       NULL, 'a'},
            {"device-id",         no_argument,       NULL, 5},
            {"name",              required_argument, NULL, 'n'},
            {"auto-off",          required_argument, NULL, 'o'},
            {"noise-cancelling",  required_argument, NULL, 'c'},
            {"prompt-language",   required_argument, NULL, 'l'},
            {"voice-prompts",     required_argument, NULL, 'v'},
            {"pairing",           required_argument, NULL, 'p'},
            {"self-voice",        required_argument, NULL, 'e'},
            {"connect-device",    required_argument, NULL, 2},
            {"disconnect-device", required_argument, NULL, 3},
            {"remove-device",     required_argument, NULL, 4},
            {"send-packet",       required_argument, NULL, 1},
            {0,                   no_argument,       NULL, 0}
    };

    // Find connection address and verify options
    int opt;
    int opt_index = 0;
    while ((opt = getopt_long(argc, argv, short_opt, long_opt, &opt_index)) >
           0) {
        switch (opt) {
            case 'h':
                usage();
                return 0;
            case '?':
                usage();
                return 1;
            default:
                break;
        }
    }

    if (argc - 1 != optind) {
        fprintf(stderr, argc <= optind
                        ? "An address argument must be given.\n"
                        : "Only one address argument may be given.\n");
        usage();
        return 1;
    }

    char *address = argv[optind];
    int status = 0;
    opt_index = 0;
    optind = 1;
    while ((opt = getopt_long(argc, argv, short_opt, long_opt, &opt_index)) >
           0) {
        if (status) {
            break;
        }

        switch (opt) {
            case 'i':
                status = do_get_information(address);
                break;
            case 'd':
                status = do_get_device_status(address);
                break;
            case 'f':
                status = do_get_firmware_version(address);
                break;
            case 's':
                status = do_get_serial_number(address);
                break;
            case 'b':
                status = do_get_battery_level(address);
                break;
            case 'a':
                status = do_get_paired_devices(address);
                break;
            case 5:
                status = do_get_device_id(address);
                break;
            case 'n':
                status = do_set_name(address, optarg);
                break;
            case 'o':
                status = do_set_auto_off(address, optarg);
                break;
            case 'c':
                status = do_set_noise_cancelling(address, optarg);
                break;
            case 'l':
                status = do_set_prompt_language(address, optarg);
                break;
            case 'v':
                status = do_set_voice_prompts(address, optarg);
                break;
            case 'p':
                status = do_set_pairing(address, optarg);
                break;
            case 2:
                status = do_connect_device(address, optarg);
                break;
            case 3:
                status = do_disconnect_device(address, optarg);
                break;
            case 4:
                status = do_remove_device(address, optarg);
                break;
            case 'e':
                status = do_set_self_voice(address, optarg);
                break;
            case 1:
                status = do_send_packet(address, optarg);
                break;
            default:
                status = 1;
        }
    }

    if (status < 0) {
        perror("Error trying to change setting");
    }

    return status;
}
