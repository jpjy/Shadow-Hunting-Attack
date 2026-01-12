#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sched.h>
#include <sys/mman.h>
#include "./cacheutils.h"

int main() {
    char* base;
    char* end;
    size_t count[10] = {0};
    int fd = open("/usr/lib/x86_64-linux-gnu/libcrypto.so", O_RDONLY); // Corrected file path
    if (fd < 0) { // Check if the file was opened successfully
        perror("Failed to open file");
        return -1;
    }
    size_t size = lseek(fd, 0, SEEK_END);
    if (size == (size_t)-1 || size == 0) { // Check for lseek failure or empty file
        perror("Failed to determine file size");
        close(fd);
        exit(-1);
    }
    size_t map_size = size;
    if (map_size & 0xFFF) {
        map_size |= 0xFFF;
        map_size += 1;
    }
    base = (char*) mmap(0, map_size, PROT_READ, MAP_SHARED, fd, 0);
    if (base == MAP_FAILED) { // Check mmap success
        perror("Memory mapping failed");
        close(fd);
        return -1;
    }
    end = base + size;

    FILE* file = fopen("delta_times.txt", "w");
    if (!file) {
        perror("Failed to open file");
        munmap(base, map_size);
        close(fd);
        return -1;
    }

    char* probe = base + 0x16aa00;
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 1000; j++) {
            flush(probe);
            size_t delta = maccess(probe);
            count[i] += delta;
        }
    }
    for (int k = 0; k < 10; k++) {
        printf("count[%d] is %lu\n", k, count[k]); // Corrected variable in printf
    }

    fclose(file);
    munmap(base, map_size);
    close(fd);
    return 0;
}
