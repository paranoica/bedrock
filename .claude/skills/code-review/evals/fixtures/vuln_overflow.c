#include <string.h>
void handle(const char *input) {
    char buf[16];
    strcpy(buf, input);   /* unbounded copy -> stack buffer overflow [VULN: overflow] */
}
