from flask import Flask, request, jsonify
import subprocess
import time
import re
import os
import uuid
import logging
from datetime import datetime, timezone  # kept in case you later log timestamps etc.

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Fallback UUID for platforms that do not expose an instance ID via environment variables
FALLBACK_INSTANCE_UUID = str(uuid.uuid4())


def get_cpu_brand():
    """Return (cpu_brand_string, frequency_in_Hz_or_None)."""

    # --- Try cpuid first ---
    try:
        result = subprocess.run(['cpuid', '-1'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.strip().startswith("brand ="):
                    brand = line.split('=')[1].strip().strip('"').strip()

                    # Look for "X.YGHz" inside the brand string
                    parsed_freq = re.findall(r'(\d+\.\d+)GHz', brand)
                    if parsed_freq:
                        return brand, float(parsed_freq[0]) * 1e9

                    return brand, None  # CPU brand, but no GHz field found
    except FileNotFoundError:
        # cpuid command not available
        pass

    # --- Fall back to /proc/cpuinfo ---
    try:
        with open('/proc/cpuinfo', 'r') as file:
            for line in file:
                if "model name" in line:
                    model_line = line.split(":")[1].strip()

                    parsed_freq = re.findall(r'(\d+\.\d+)GHz', model_line)
                    if parsed_freq:
                        return model_line, float(parsed_freq[0]) * 1e9

                    return model_line, None  # CPU brand found but no frequency
    except FileNotFoundError:
        # /proc/cpuinfo not found
        pass

    return "Unknown CPU Brand", None


def get_instance_identifier():
    """
    Returns a unique identifier for the current instance.
    Priority:
      1. Use environment variable 'INSTANCE_ID' if set.
      2. Otherwise use environment variable 'WEBSITE_INSTANCE_ID' if set.
      3. Otherwise use a fallback UUID generated at startup.
    """
    env_id = os.getenv("INSTANCE_ID") or os.getenv("WEBSITE_INSTANCE_ID")
    if env_id:
        return env_id
    return FALLBACK_INSTANCE_UUID


cpu_brand, parsed_freq = get_cpu_brand()


@app.route('/info', methods=['GET'])
def get_info():
    """
    Return CPU information for this instance.
    Instance identity is provided separately by the /instance_id endpoint.
    """
    time.sleep(5)
    return jsonify({
        'cpu_brand': cpu_brand,
        'parsed_freq': parsed_freq
    })


@app.route('/execute', methods=['GET'])
def run_command_endpoint():
    """
    Execute a command passed via the 'cmd' query parameter.
    Intended for controlled experiments only.
    Example:
      /execute?cmd=ls
    """
    try:
        command = request.args.get('cmd')
        if not command:
            return "No command provided.", 400

        command_parts = command.split()
        output = subprocess.check_output(command_parts, stderr=subprocess.STDOUT)
        return output.decode(), 200
    except subprocess.CalledProcessError as e:
        return e.output.decode(), 400


@app.route('/lock')
def lock_3():
    """
    Invoke the memory-locking binary ./lock-3 and return its output.
    This endpoint is used to induce memory bus contention.
    """
    try:
        output = subprocess.check_output(["./lock-3"]).decode("utf-8")
        return output, 200
    except subprocess.CalledProcessError as e:
        return e.output.decode(), 400


@app.route('/check')
def check():
    """
    Invoke the memory-check binary ./check and return its output.
    This endpoint is used to measure memory access latency under contention.
    """
    try:
        output = subprocess.check_output(["./check"]).decode("utf-8")
        return output, 200
    except subprocess.CalledProcessError as e:
        return e.output.decode(), 400


@app.route('/instance_id', methods=['GET'])
def instance_id_endpoint():
    """
    Return a per-instance identifier as JSON, using environment variables
    when available, or a fallback UUID otherwise.
    """
    instance_id = get_instance_identifier()
    return jsonify({'instance_id': instance_id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

