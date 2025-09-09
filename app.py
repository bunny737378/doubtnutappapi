from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'success': True,
        'message': 'Simple API test is working',
        'status': 'OK'
    })

@app.route('/test')
def test():
    return jsonify({
        'success': True,
        'message': 'Test endpoint working',
        'data': 'Hello from Vercel!'
    })

# For Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)