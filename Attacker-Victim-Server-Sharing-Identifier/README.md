# Attacker–Victim Server Sharing Identifier (Open Science Artifact)

This directory contains the artifacts used to **identify which attacker instance shares a physical server with an uncontrolled victim service**. It combines:

1. A container image that exposes a mem-lock endpoint and CPU information endpoint for attacker instances.
2. Scripts that:
   - Group attacker instances by CPU architecture and server group.
   - Run the Target Victim Locator using a binary-search strategy over attacker instances.

---

## 1. `lock_cpuinfo_integrated_image/`

This directory defines the container image used for attacker instances in the Target Victim Locator.

1. Build and push the container image to your preferred registry (e.g., AWS ECR, Azure Container Registry, or Artifact Registry / GCR).
2. Deploy instances of this image as attacker functions/services (e.g., Lambda, Function Apps, Cloud Run).
3. Use the `/info` endpoint to characterize each attacker instance’s CPU architecture.
4. Use the `/lock` endpoint to induce contention during victim probing.

---

## 2. `target_victim_localization/`

This directory contains the scripts that implement the Target Victim Locator workflow.

### 2.1 `prepare_attacker_sets.py`
Prepares the attacker instance sets used in the localization step.

### 2.2 `target_victim_locator.py`
Implements the Target Victim Locator algorithm using a binary search over attacker instances.

