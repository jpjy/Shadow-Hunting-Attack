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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

