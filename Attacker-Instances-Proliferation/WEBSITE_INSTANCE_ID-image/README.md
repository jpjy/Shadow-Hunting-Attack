# Instance Identifier Container Image

This folder provides a small container image that exposes a single HTTP endpoint, `/instance_id`, for extracting a unique identifier of the running instance. This image is intended to support experiments that need to distinguish between different function or container instances (e.g., when studying instance proliferation or grouping behavior on serverless platforms).

The identifier is determined as follows:

1. If the execution environment provides an instance-level identifier via an environment variable  
   (`INSTANCE_ID` or `WEBSITE_INSTANCE_ID`), the endpoint returns that value.
2. Otherwise, the container generates a fallback UUID at startup, which remains constant for the lifetime of the instance.

---

## Files

- `Dockerfile` — Build instructions for the container image.  
- `app.py` — Flask application exposing the `/instance_id` endpoint.  
- `requirements.txt` — Python dependencies.  
- `request.py` — A script that concurrently queries a list of deployed instances and saves each response to `index_<n>.txt`.

---

## Build the Container

```bash
docker build -t instance-id-service .

