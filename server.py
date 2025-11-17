from flask import Flask, jsonify, requests
import numpy as np
import time

app = Flask(__name__)

@app.route("/matmul", methods=["GET"])
def matmul():
    # Generate two random 200x200 matrices with integers 500–1000
    a = np.random.randint(500, 1001, size=(200, 200), dtype=np.int32)
    b = np.random.randint(500, 1001, size=(200, 200), dtype=np.int32)

    # Perform matrix multiplication
    result = np.matmul(a, b)

    # Convert to a regular Python list (for JSON serialization)
    result_list = result.tolist()

    # Return as JSON (could be huge!)
    return jsonify({
        "matrix_size": 200,
        "range": [500, 1000],
        "result": result_list,
        "computation_time": round(time.time() - start_time, 4),  # Time taken for computation
    })

if __name__ == "__main__":
    start_time = time.time()
    # Run the Flask app on all network interfaces, port 5000
    app.run(host="0.0.0.0", port=5000)
