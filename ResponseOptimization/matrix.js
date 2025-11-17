/**
 * Generates a square matrix of a given size with random values.
 * @param {number} size - The size (N) of the NxN matrix.
 * @returns {Array<Array<number>>} A 2D array representing the matrix.
 */
function generateRandomMatrix(size) {
    const matrix = new Array(size);
    for (let i = 0; i < size; i++) {
        matrix[i] = new Array(size);
        for (let j = 0; j < size; j++) {
            // Generate a random integer between 500 and 1000 (inclusive)
            matrix[i][j] = Math.floor(Math.random() * (1000 - 500 + 1)) + 500;
        }
    }
    return matrix;
}

/**
 * Multiplies two square matrices.
 * @param {Array<Array<number>>} matrixA
 * @param {Array<Array<number>>} matrixB
 * @returns {Array<Array<number>>|null} The resulting matrix or null if dimensions mismatch.
 */
function multiplyMatrices(matrixA, matrixB) {
    const size = matrixA.length;

    // Check if matrices are square and have the same dimensions
    if (size !== matrixB.length || matrixA[0].length !== size || matrixB[0].length !== size) {
        console.error("Matrices must be square and of the same size for multiplication.");
        return null;
    }

    const resultMatrix = new Array(size);
    for (let i = 0; i < size; i++) {
        resultMatrix[i] = new Array(size).fill(0);
    }

    // Standard matrix multiplication algorithm (O(N^3))
    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            for (let k = 0; k < size; k++) {
                resultMatrix[i][j] += matrixA[i][k] * matrixB[k][j];
            }
        }
    }
    return resultMatrix;
}

/**
 * Main function to run the computation when the button is clicked.
 */
function performComputation() {
    const MATRIX_SIZE = 200;
    const statusDiv = document.getElementById('status');

    statusDiv.textContent = 'Generating 200x200 matrices...';

    const startTime = performance.now();

    const matrixA = generateRandomMatrix(MATRIX_SIZE);
    const matrixB = generateRandomMatrix(MATRIX_SIZE);

    statusDiv.textContent = 'Matrices generated. Starting multiplication (this may take a moment)...';

    // Using setTimeout to allow the UI to update the status text before starting heavy computation
    setTimeout(() => {
        const resultMatrix = multiplyMatrices(matrixA, matrixB);
        const endTime = performance.now();
        const duration = (endTime - startTime).toFixed(2);

        if (resultMatrix) {
            statusDiv.innerHTML = `
                Computation complete in ${duration} milliseconds.<br>
                Matrices generated and multiplied entirely in your browser.<br>
                The resulting 200x200 matrix has been calculated.
            `;
            // Optional: Log a snippet of results to the console for verification
            console.log("Matrix A (top-left 3x3):", matrixA.slice(0, 3).map(row => row.slice(0, 3)));
            console.log("Matrix B (top-left 3x3):", matrixB.slice(0, 3).map(row => row.slice(0, 3)));
            console.log("Result Matrix (top-left 3x3):", resultMatrix.slice(0, 3).map(row => row.slice(0, 3)));
        } else {
            statusDiv.textContent = 'An error occurred during multiplication.';
        }
    }, 10); // A small delay to ensure the UI updates
}
