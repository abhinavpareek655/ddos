from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import numpy as np
import time

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per minute"],  # Limit to 10 requests per minute per IP
)

@app.route("/matmul", methods=["GET"])
@limiter.limit("10 per minute")  # Apply rate limit to this route
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
