from flask import Flask, render_template

app = Flask(__name__)

@app.route('/matmul')
def index():
    # Renders the HTML template located in the 'templates' folder
    return render_template('index.html')

if __name__ == '__main__':
    # Run the app. This is the server-side code.
    app.run(host="0.0.0.0", port=5000)
