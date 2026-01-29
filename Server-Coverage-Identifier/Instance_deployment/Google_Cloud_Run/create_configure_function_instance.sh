#!/usr/bin/env bash
set -euo pipefail


# GCP project and region
PROJECT_ID=""
REGION="us-west1"  # e.g., us-west1, europe-west2

IMAGE="us-west1-docker.pkg.dev/xxx/xxx/xxx"

# Execution environment: gen1 or gen2
EXEC_ENV="gen1"       # "gen1" or "gen2"

# Resource settings per instance
CPU="1"               # e.g., 1, 2, 4
MEMORY="512Mi"        # e.g., 256Mi, 512Mi, 1Gi, 2Gi
CONCURRENCY="80"      # requests per instance
TIMEOUT="60s"         # request timeout

# Allow unauthenticated access (public HTTP)
ALLOW_UNAUTH=true     # set to false for authenticated only

# Number of Cloud Run services (instances) to create
SERVICE_PREFIX="service"
START_INDEX=1
END_INDEX=100         


PLATFORM="managed"

if [ "$ALLOW_UNAUTH" = true ]; then
  AUTH_FLAG="--allow-unauthenticated"
else
  AUTH_FLAG="--no-allow-unauthenticated"
fi


deploy_service() {
  local service_name="$1"

  echo "========================================"
  echo "Deploying Cloud Run service: ${service_name}"
  echo "Project:   ${PROJECT_ID}"
  echo "Region:    ${REGION}"
  echo "Image:     ${IMAGE}"
  echo "Exec env:  ${EXEC_ENV}"
  echo "CPU:       ${CPU}"
  echo "Memory:    ${MEMORY}"
  echo "Concurrency: ${CONCURRENCY}"
  echo "Timeout:   ${TIMEOUT}"
  echo "========================================"

  gcloud run deploy "${service_name}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --platform="${PLATFORM}" \
    --image="${IMAGE}" \
    --execution-environment="${EXEC_ENV}" \
    --cpu="${CPU}" \
    --memory="${MEMORY}" \
    --concurrency="${CONCURRENCY}" \
    --timeout="${TIMEOUT}" \
    ${AUTH_FLAG} \
    --quiet

  echo "Deployed service: ${service_name}"
}

# deploy all services in parallel

pids=()

for i in $(seq "${START_INDEX}" "${END_INDEX}"); do
  service_name="${SERVICE_PREFIX}-${i}"
  # Launch deployment in background
  deploy_service "${service_name}" &
  pids+=($!)
done

# Wait for all background deployments to finish
for pid in "${pids[@]}"; do
  wait "$pid"
done

echo "All Cloud Run services deployed."

