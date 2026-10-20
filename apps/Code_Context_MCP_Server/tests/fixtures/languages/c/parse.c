#include "config.h"
#include <stdio.h>

static int read_line(const char *path) {
    return printf("%s", path);
}

/** Parses the file at path. */
int parse_config(const char *path) {
    return read_line(path);
}

int load(void) {
    return parse_config("a.conf");
}

int reload(void) {
    // parse_config() in a comment
    return parse_config("b.conf");
}
