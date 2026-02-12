import json

def handler(request, context=None):
    path = request.get("path", "/api")
    method = request.get("method", "GET")

    # Route handling
    if path == "/api" or path == "/api/":
        body = {"status": "running", "message": "Social Media Dashboard API"}
    elif path == "/api/health":
        body = {"status": "healthy"}
    else:
        body = {"error": "Not found", "path": path}

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        },
        "body": json.dumps(body)
    }
