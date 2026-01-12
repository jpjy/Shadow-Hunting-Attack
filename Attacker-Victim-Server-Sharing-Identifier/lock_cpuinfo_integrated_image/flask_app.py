from flask import Flask, request, jsonify
import subprocess
import time
import re
import os
import uuid
import logging
from datetime import datetime, timezone  

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)


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



cpu_brand, parsed_freq = get_cpu_brand()


@app.route('/info', methods=['GET'])
def get_info():
    """
    Return CPU information for this instance.
    """
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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

