# Shadow Hunting in the Cloud – Open Science Artifacts

This repository contains the core artifacts used in our study of **server coverage identification**, **attacker–victim server sharing**, **attacker instance proliferation**, and **case study** in FaaS/cloud platforms. Each subdirectory corresponds to a major component of the experimental pipeline described in the paper.

---

## 1. `Server-Coverage-Identifier/`

Artifacts for discovering **which attacker instances share the same physical server**.

- Deployment scripts for creating many function instances on:
  - AWS Lambda
  - Azure Function Apps
  - Google Cloud Run
- A container image exposing `/lock` and `/check` endpoints that induce and measure memory-bus contention.
- An iteration script that:
  - Systematically runs mem-lock/mem-check across instances.
  - Infers server-sharing groups (server coverage) among them.
This component provides the server coverage map used by later stages, such as attacker–victim localization.
See the detailed introduction to each file in the README file inside Server-Coverage-Identifier/
---

## 2. `Attacker-Victim-Server-Sharing-Identifier/`

Artifacts for the **Target Victim Locator**: finding which attacker instance shares a server with an uncontrolled victim service.

- Integrated container image with:
  - `/lock` for memory-bus locking,
  - `/info` for CPU brand/frequency,
  - `/instance_id` for per-instance identity.
- Python scripts that:
  1. Group attacker instances by (CPU brand, frequency) and deduplicate by server (one representative per server).
  2. Run a binary-search-style localization:
     - Lock subsets of attacker instances.
     - Probe the victim’s response time.
     - Narrow down to the attacker instance that shares a server with the victim based on an absolute latency threshold.

This directory implements the end-to-end attacker–victim server sharing identification pipeline.
See the detailed introduction to each file in the README file inside Attacker-Victim-Server-Sharing-Identifier/

---

## 3. `Attacker-Instances-Proliferation/`

Artifacts for **scaling out attacker instances** and distinguishing which instance handled each request.

- Container images that:
  - Expose an `/instance_id` endpoint for retrieving platform- or app-level instance identifiers.
  - Integrate memory-lock/check primitives with instance IDs.
- Scripts to group scaled-out instances into server-sharing groups based on timing signals and instance IDs.

Used in the paper to demonstrate attacker instance proliferation.
See the detailed introduction to each file in the README file inside Attacker-Instances-Proliferation/

---

## 4. `Case-Study/`

Low-level **resource contention primitives** used in the case studies:

- Programs to generate contention on:
  - Last-level cache (LLC)
  - Memory bus
  - Network interface card (NIC)
- Each subdirectory contains C source and compiled binaries for stressing a specific shared hardware component (and, for NIC, an auxiliary Python driver).

These primitives are used to illustrate how attacker workloads can interfere with victim performance via shared microarchitectural and I/O resources.
See the detailed introduction to each file in the README file inside Case-Study/



