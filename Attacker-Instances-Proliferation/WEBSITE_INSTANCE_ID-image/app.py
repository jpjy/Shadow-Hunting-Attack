from flask import Flask, jsonify
import os
import uuid

app = Flask(__name__)

# Generate a fallback UUID for platforms that do not expose a built-in instance ID
FALLBACK_UUID = str(uuid.uuid4())

def get_instance_identifier():
    """
    Returns a unique identifier for the current instance.

    Priority:
    1. Use any existing environment variable named 'INSTANCE_ID'
       or 'WEBSITE_INSTANCE_ID' (if provided by the platform).
    2. If no such identifier exists, use a persistent UUID generated
       at startup to uniquely identify this instance.
    """
    # Check for common environment-based instance identifiers
    env_id = os.getenv("INSTANCE_ID") or os.getenv("WEBSITE_INSTANCE_ID")
    if env_id:
        return env_id

    # Fallback for platforms that do not expose instance IDs
    return FALLBACK_UUID


@app.route('/instance_id', methods=['GET'])
def instance_id_endpoint():
    instance_id = get_instance_identifier()
    return jsonify({"instance_id": instance_id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

