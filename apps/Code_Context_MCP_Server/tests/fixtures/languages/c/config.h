/* Configuration loading. */
#ifndef CONFIG_H
#define CONFIG_H

struct config {
    int port;
};

typedef struct config config_t;

/// Parses a configuration file.
int parse_config(const char *path);

#endif
