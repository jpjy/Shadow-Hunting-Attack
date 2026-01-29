#include <stdatomic.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h> // Include this header for uintptr_t
#include <time.h> // Include time.h for measuring elapsed time

int main() {
    const size_t N = 64; // Example size, adjust based on your needs
    char *char_ptr = malloc((N+1) * 8); // Allocate memory, assuming 8 bytes per block
    if (!char_ptr) {
        perror("Failed to allocate memory");
        return EXIT_FAILURE;
    }

    // Ensure the allocated memory block starts with a cache line aligned address
    char *aligned_ptr = (char *)(((uintptr_t)char_ptr + 63) & ~((uintptr_t)63));

    // Move the pointer 2 bytes up to make it unaligned relative to the cache line
    atomic_int *unaligned_addr = (atomic_int *)(aligned_ptr + 2);

    // Get the start time
    time_t start_time = time(NULL);

    while (time(NULL) - start_time < 1) { // Check the elapsed time
        for (size_t i = 0; i < N; ++i) {
            atomic_fetch_add(&unaligned_addr[i], 1); // Increment each atomic_int by 1
        }
    }

    // Free the allocated memory
    free(char_ptr);
    printf("Lock is executed successfully\n");
    return 0;
}
