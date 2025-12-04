#!/usr/bin/env python3
"""
High-Performance Flask Server with Matrix Multiplication
Optimized for maximum throughput - NO LIMITS!

Requirements:
    pip3 install flask numpy gunicorn gevent
"""

from flask import Flask, jsonify
import numpy as np
import time
import os
import multiprocessing

app = Flask(__name__)

# Disable Flask debug mode for production
app.config['DEBUG'] = False
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

@app.route("/matmul", methods=["GET"])
def matmul():
    start_time = time.time()
    
    # Generate two random 200x200 matrices with integers 500–1000
    a = np.random.randint(500, 1001, size=(200, 200), dtype=np.int32)
    b = np.random.randint(500, 1001, size=(200, 200), dtype=np.int32)

    # Perform matrix multiplication
    result = np.matmul(a, b)

    # Convert to a regular Python list (for JSON serialization)
    result_list = result.tolist()
    
    computation_time = time.time() - start_time

    # Return as JSON
    return jsonify({
        "matrix_size": 200,
        "range": [500, 1000],
        "result": result_list,
        "computation_time": round(computation_time, 4),
    })

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route("/ping", methods=["GET"])
def ping():
    """Lightweight ping endpoint"""
    return "pong"

if __name__ == "__main__":
    # This should NOT be used in production
    # Use the gunicorn launcher instead
    print("[WARNING] Using Flask development server - NOT RECOMMENDED!")
    print("[INFO] Use: python3 run_server.py for production")
    app.run(host="0.0.0.0", port=5000, threaded=True)