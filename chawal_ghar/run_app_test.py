from app import app

if __name__ == '__main__':
    print("Starting test server on port 5001...")
    app.run(port=5001, debug=True)
