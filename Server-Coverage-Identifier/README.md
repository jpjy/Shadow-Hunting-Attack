# Server Coverage Identifier

This directory contains the code and scripts used to implement the **Server Coverage Identifier** described in our paper. It provides:

- Cloud deployment scripts to create large numbers of function instances on major FaaS platforms.
- The lock/check binaries and container image used to induce and measure memory bus contention.
- The iteration script that infers which instances share the same physical server.

---

## Contents

### 1. Instance Deployment

**`Instance_deployment/`**

Cloud-specific scripts for deploying and configuring many function instances:

- **`AWS_Lambda/create_configure_function_instance.sh`**  
  Creates a batch of AWS Lambda functions from a container image, configures functions, and attaches public Function URLs.

- **`Azure_Function_Apps/create_function_instance.sh`**  
  Creates multiple Azure Function Apps for the experiment.

- **`Azure_Function_Apps/configure_function_instance.sh`**  
  Applies post-creation settings to the Azure Function Apps (e.g., app configuration, timeouts).

- **`Google_Cloud_Run/create_configure_function_instance.sh`**  
  Deploys multiple Google Cloud Run services from a container image, and configures functions.

> **Prerequisite:** The corresponding cloud CLI (`aws`, `az`, or `gcloud`) must be installed, authenticated, and authorized to create resources.

---

### 2. Server Coverage Identifier Logic

**`iteration_test.py`**


- Each function instance exposes two endpoints:  
  - `/lock` — triggers a memory-lock operation on that instance.  
  - `/check` — runs a mem-check routine and returns timing-related metrics.

---

### 3. Integrated Lock/Check Container Image

**`lock_check_integrated_image/`**

Source and artifacts for the container image used in the experiments:

- **`lock-3`, `lock-3.c`**  
  Mem-lock binary and source code that induces memory bus contention.

- **`check`, `check.c`**  
  Mem-check binary and source code that measures memory access timing under contention.

- **`cacheutils.h`, `common.h`**  
  Shared helper headers for cache and timing primitives.

- **`flask_app.py`**  
  Flask application exposing HTTP endpoints (including `/lock` and `/check`) that wrap the underlying binaries.

- **`Dockerfile`, `requirements.txt`**  
  Used to build the integrated container image that is deployed across FaaS platforms.

---

### 4. Standalone Lock and Check Components

**`mem-lock/`**

- Contains the standalone mem-lock binary (`lock-3`) and its source (`lock-3.c`), useful for isolated testing or rebuilding.

**`mem-check/`**

- Contains the standalone mem-check binary (`check`) and its source (`check.c`), plus shared headers (`cacheutils.h`, `common.h`).

These directories allow you to rebuild or evaluate the lock/check primitives outside of the integrated container image.

---

## High-Level Usage

1. **Build the container image**  
   From `lock_check_integrated_image/`, build and push the image to your preferred registry (AWS ECR, Azure Container Registry, or Artifact Registry / GCR).

2. **Deploy instances on each platform**  
   Use the scripts in `Instance_deployment/` to create large batches of function instances or services on AWS Lambda, Azure Function Apps, and Google Cloud Run.

3. **Run the Server Coverage Identifier**  
   Configure `iteration_test.py` with the list of instance URLs and your chosen threshold, then run it to infer server-sharing groups as described in the paper.

