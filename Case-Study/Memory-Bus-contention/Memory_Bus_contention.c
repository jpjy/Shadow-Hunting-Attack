#include <stdatomic.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h> // For uintptr_t
#include <pthread.h> // For threading
#include <time.h> // For measuring elapsed time

#define THREADS 4  // Number of threads
#define N 64       // Number of locked locations

// Locking function for threads
void *lock_memory(void *arg) {
    atomic_int *unaligned_addr = (atomic_int *)arg;
    time_t start_time = time(NULL);

    // Loop for approximately 30 seconds
    while (time(NULL) - start_time < 30) { // Check elapsed time
        for (size_t i = 0; i < N; ++i) {
            atomic_fetch_add(&unaligned_addr[i], 1); // Atomic increment
        }
    }
    return NULL;
}

int main() {
    char *char_ptr = malloc((N + 1) * 8); // Allocate memory
    if (!char_ptr) {
        perror("Failed to allocate memory");
        return EXIT_FAILURE;
    }

    // Ensure the allocated memory block starts with a cache line aligned address
    char *aligned_ptr = (char *)(((uintptr_t)char_ptr + 63) & ~((uintptr_t)63));

    // Move the pointer 2 bytes up to make it unaligned relative to the cache line
    atomic_int *unaligned_addr = (atomic_int *)(aligned_ptr + 3);

    // Create threads
    pthread_t threads[THREADS];
    for (int i = 0; i < THREADS; i++) {
        if (pthread_create(&threads[i], NULL, lock_memory, (void *)unaligned_addr) != 0) {
            perror("Failed to create thread");
            free(char_ptr);
            return EXIT_FAILURE;
        }
    }

    // Wait for threads to complete
    for (int i = 0; i < THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    // Free the allocated memory
    free(char_ptr);

    return 0;
}

