"""Simple Flask mock server for Slack API."""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/auth.test", methods=["POST"])
def auth_test():
    return jsonify({
        "ok": True,
        "team_id": "T_MOCK_001",
        "user_id": "U_MOCK_BOT",
        "bot_id": "B_MOCK_001"
    })

@app.route("/api/views.open", methods=["POST"])
def views_open():
    return jsonify({
        "ok": True,
        "view": {"id": "V_MOCK_001", "callback_id": "decision_modal"}
    })

@app.route("/api/chat.postMessage", methods=["POST"])
def chat_post():
    return jsonify({
        "ok": True,
        "ts": "1745000000.000001",
        "channel": request.json.get("channel", "U_MOCK_USER") if request.is_json else "U_MOCK_USER"
    })

@app.route("/api/chat.update", methods=["POST"])
def chat_update():
    return jsonify({"ok": True})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)