#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>

#define BUFFER_SIZE (100 * 1024 * 1024) // 100MB buffer
#define CACHE_LINE_SIZE 64              // Typical cache line size
#define NUM_LINES (BUFFER_SIZE / CACHE_LINE_SIZE)

// Fisher-Yates shuffle to randomize access order
void shuffle(size_t *array, size_t n) {
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = rand() % (i + 1);
        size_t temp = array[i];
        array[i] = array[j];
        array[j] = temp;
    }
}

int main() {
    // Allocate a 100MB buffer aligned to cache line size
    char *buffer = aligned_alloc(CACHE_LINE_SIZE, BUFFER_SIZE);
    if (!buffer) {
        perror("Buffer allocation failed");
        return EXIT_FAILURE;
    }

    // Touch the buffer to ensure the pages are allocated
    for (size_t i = 0; i < BUFFER_SIZE; i += CACHE_LINE_SIZE) {
        buffer[i] = 1;
    }

    // Create an array of indices representing offsets into the buffer
    size_t *indices = malloc(NUM_LINES * sizeof(size_t));
    if (!indices) {
        perror("Indices allocation failed");
        free(buffer);
        return EXIT_FAILURE;
    }
    for (size_t i = 0; i < NUM_LINES; i++) {
        indices[i] = i * CACHE_LINE_SIZE;
    }

    // Seed the random number generator
    srand(time(NULL));

    printf("Starting LLC eviction loop. Press Ctrl+C to exit.\n");

    // Infinite loop to continuously access the buffer in random order
    while (1) {
        // Shuffle the indices to randomize the order of accesses
        shuffle(indices, NUM_LINES);
        // Iterate over the entire buffer
        for (size_t i = 0; i < NUM_LINES; i++) {
            // Perform a read-modify-write on each cache line.
            // The use of 'volatile' prevents the compiler from optimizing away the access.
            volatile char value = buffer[indices[i]];
            buffer[indices[i]] = value + 1;
        }
    }

    // Cleanup (unreachable in this infinite loop)
    free(indices);
    free(buffer);
    return 0;
}

