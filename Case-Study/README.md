# Case Study – Resource Contention Primitives

This directory contains the case-study artifacts used to induce resource contention on shared hardware components. Each subdirectory provides a self-contained primitive that stresses a specific shared resource:

- Last-level cache (LLC)
- Memory bus
- Network interface card (NIC)

These programs are used in the paper’s case studies to demonstrate how attacker-controlled workloads can interfere with victim workloads via shared hardware components.


---

## High-Level Usage

1. **Build (if needed)**  
   If modifing the C sources, recompile the binaries (e.g., `gcc -O2 LLC_contention.c -o LLC_contention`, and similarly for the other components).

2. **Run on a shared platform**  
   Execute the binaries on a platform where the target component (LLC, memory bus, or NIC) is shared between attacker and victim workloads. 

