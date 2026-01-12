#!/bin/bash

deploy_function_app() {
  local app_name=$1
  cd /mnt/e/Research/function-app || exit
  func azure functionapp publish "$app_name"
}

export -f deploy_function_app

seq 1 100 | xargs -I {} -P 10 bash -c 'deploy_function_app "function-{}"'

