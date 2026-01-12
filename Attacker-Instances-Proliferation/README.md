# Attacker Instances Proliferation (Open Science Artifact)

This directory contains the artifacts used to **deploy, identify, and group large numbers of attacker instances** in a Function-as-a-Service (FaaS) environment. It focuses on:

- Spinning up many identical instances behind a shared URL.
- Exposing a simple endpoint to read out the underlying platform’s instance identifier.
- Using memory-lock and memory-check operations plus instance IDs to infer **server-sharing relationships** among scaled-out instances.

---

## 1. `WEBSITE_INSTANCE_ID-image/`

A small, self-contained container image that exposes a single endpoint for retrieving an instance identifier.

---

## 2. `lock_check_instanceid_integrated_image/`

An integrated container image combining:

- Memory-lock and memory-check primitives.
- Instance ID reporting.


This enables fine-grained analysis of **server sharing among scaled-out instances**, using both timing behavior and instance identity.

---

## 3. `scaled-out-instances-group.py`

Python script that uses the **lock/check/instance_id** endpoints to infer **server-sharing relationships** among many scaled-out attacker instances that sit behind a shared service URL.

### High-Level Behavior

- Scaled-out attacker instances have been deployed using the integrated image and that they can be triggered via HTTP endpoints (e.g., `/lock`, `/check`, `/instance_id`).
- In each iteration, the script:

  1. **Selects one instance** as the “lock” instance by sending a request to `/lock` (and reading `/instance_id` to see which instance responded).
  2. **Simultaneously triggers `/check` on all other instances**, recording their reported timing metrics and instance IDs.
  3. Compares each check result against a **user-chosen threshold** to determine which instances experienced elevated memory-access latency.
  4. Groups the lock instance together with any instances whose check metric exceeds the threshold, treating them as **sharing the same physical server**.
  5. Removes all instances in the newly formed group from the remaining pool and repeats the process until all instances have been assigned to a group.


Together, these artifacts support the **Attacker Instances Proliferation** experiments by providing concrete code to deploy, identify, and structurally group attacker instances in large-scale cloud environments.

