#!/bin/bash

# Set common variables
IMAGE_URI="xxx.dkr.ecr.us-west-2.amazonaws.com/xxx"
ROLE_ARN="arn:aws:iam::xxx:role/LambdaExecutionRole2"
REGION="us-west-2"
TIMEOUT=15
DELAY=1  # Delay in seconds

# Function to create and configure a Lambda function
create_function() {
  FUNCTION_NAME=$1

  # Create the Lambda function
  echo "Creating Lambda function $FUNCTION_NAME..."
  aws lambda create-function \
      --function-name $FUNCTION_NAME \
      --package-type Image \
      --code ImageUri=$IMAGE_URI \
      --role $ROLE_ARN \
      --region $REGION

  if [ $? -ne 0 ]; then
    echo "Failed to create Lambda function $FUNCTION_NAME"
    return
  fi

  # Create the Function URL
  echo "Creating Function URL for $FUNCTION_NAME..."
  FUNCTION_URL=$(aws lambda create-function-url-config \
      --function-name $FUNCTION_NAME \
      --auth-type NONE \
      --region $REGION \
      --query 'FunctionUrl' \
      --output text)

  if [ $? -ne 0 ]; then
    echo "Failed to create Function URL for $FUNCTION_NAME"
    return
  fi

  echo "Function URL created: $FUNCTION_URL"

  # Add a resource-based policy to allow public access
  echo "Adding resource-based policy to allow public access for $FUNCTION_NAME..."
  aws lambda add-permission \
      --function-name $FUNCTION_NAME \
      --principal "*" \
      --action "lambda:InvokeFunctionUrl" \
      --statement-id "FunctionURLAllowPublicAccess" \
      --function-url-auth-type NONE \
      --region $REGION

  if [ $? -ne 0 ]; then
    echo "Failed to add resource-based policy for $FUNCTION_NAME"
    return
  fi

  echo "Function $FUNCTION_NAME created and URL configured successfully."
  sleep $DELAY  # Add a delay to avoid rate limiting
}

# Loop through the function names and create them sequentially with delay
for i in {1501..2500}; do
  FUNCTION_NAME="lambda-$i"
  create_function $FUNCTION_NAME
done

echo "All functions created and URLs configured successfully."

# Sleep to ensure all functions are created before updating their configuration
sleep 20

# Function to update the function timeout
update_timeout() {
  FUNCTION_NAME=$1

  # Update the function configuration to set timeout
  echo "Setting function timeout to $TIMEOUT seconds for $FUNCTION_NAME..."
  aws lambda update-function-configuration \
      --function-name $FUNCTION_NAME \
      --timeout $TIMEOUT \
      --region $REGION

  if [ $? -ne 0 ]; then
    echo "Failed to update timeout for $FUNCTION_NAME"
    return
  fi

  echo "Function $FUNCTION_NAME timeout updated successfully."
  sleep $DELAY  # Add a delay to avoid rate limiting
}

# Loop through the function names and update their timeout sequentially with delay
for i in {1501..2500}; do
  FUNCTION_NAME="lambda-$i"
  update_timeout $FUNCTION_NAME
done

echo "All functions timeout updated successfully."
