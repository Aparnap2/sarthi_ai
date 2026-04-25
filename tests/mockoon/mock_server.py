"""Mock Slack server that records all requests for E2E verification."""
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

requests_log = []

@app.route("/api/auth.test", methods=["POST"])
def auth_test():
    requests_log.append({"endpoint": "auth.test", "body": request.json})
    return jsonify({"ok": True, "team_id": "T_MOCK_001"})

@app.route("/api/views.open", methods=["POST"])
def views_open():
    data = request.json
    requests_log.append({"endpoint": "views.open", "body": data})
    return jsonify({"ok": True, "view": {"id": "V_MOCK_001"}})

@app.route("/api/chat.postMessage", methods=["POST"])
def chat_post():
    data = request.json
    requests_log.append({
        "endpoint": "chat.postMessage", 
        "body": data,
        "timestamp": data.get("ts", "new")
    })
    return jsonify({"ok": True, "ts": "1745000000.000001", "channel": data.get("channel", "C000")})

@app.route("/api/chat.update", methods=["POST"])
def chat_update():
    requests_log.append({"endpoint": "chat.update", "body": request.json})
    return jsonify({"ok": True})

@app.route("/requests", methods=["GET"])
def get_requests():
    return jsonify(requests_log)

@app.route("/reset", methods=["POST"])
def reset():
    global requests_log
    requests_log = []
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)