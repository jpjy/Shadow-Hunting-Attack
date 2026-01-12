#!/bin/bash

create_function_app() {
  local app_name=$1
  az functionapp create \
    --resource-group S3-Group1 \
    --consumption-plan-location westus \
    --runtime python \
    --functions-version 4 \
    --name "$app_name" \
    --storage-account appstorage \
    --os-type Linux
}

export -f create_function_app

seq 1 100 | xargs -I {} -P 20 bash -c 'create_function_app "function-{}"'

