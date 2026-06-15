#include <string.h>
void handle(const char *input) {
    char buf[16];
    snprintf(buf, sizeof(buf), "%s", input);  /* bounded, NUL-terminated — SAFE */
}
