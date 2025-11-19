from flask import Flask, request, jsonify, send_from_directory
import smtplib
from email.message import EmailMessage
import os
from flask_cors import CORS
from ai_model import get_ai_reply
from main import create_user, verify_user, update_user, change_password
import os
import json
from datetime import datetime

# path for storing conversations (data/chat_data_user.json in repo root)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(ROOT, 'data', 'chat_data_user.json')


def _load_conversations():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_conversations(items):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _find_conversation(conv_id):
    items = _load_conversations()
    for it in items:
        if it.get('id') == conv_id:
            return it
    return None

app = Flask(__name__)
CORS(app)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "")
    reply = get_ai_reply(user_message)
    # Return key `response` because the frontend expects `data.response`
    return jsonify({"response": reply})


@app.route("/api/chat/init", methods=["POST"])
def init_chat():
    # Minimal init payload for frontend
    return jsonify({"defaultPersonality": "friendly"})


@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    name = data.get('name', '') or username
    email = data.get('email', '')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing username or password'}), 400
    ok, err = create_user(username, password, name, email)
    if not ok:
        return jsonify({'success': False, 'error': err}), 400
    # try to send a welcome email (if SMTP configured via environment variables)
    def send_welcome_email(to_email, to_name, to_username):
        smtp_host = os.environ.get('SMTP_HOST')
        smtp_port = int(os.environ.get('SMTP_PORT', '587')) if os.environ.get('SMTP_PORT') else None
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        smtp_from = os.environ.get('SMTP_FROM') or (smtp_user or 'no-reply@example.com')
        if not smtp_host or not smtp_port or not smtp_user or not smtp_pass:
            app.logger.info('SMTP not configured, skipping welcome email')
            return False
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Welcome to Aizeeno!'
            msg['From'] = smtp_from
            msg['To'] = to_email
            # Compose a friendly email; do NOT include passwords for security
            body = f"Hello {to_name or to_username},\n\n"
            body += "Thanks for signing up to Aizeeno. Here are your account details:\n\n"
            body += f"Username: {to_username}\n"
            body += f"Email: {to_email}\n\n"
            body += "For your security we do not send your password by email. If you need to reset your password, use the app's account settings.\n\n"
            body += "Thanks and welcome!\nAizeeno team\n"
            msg.set_content(body)
            # send via TLS
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            app.logger.info('Sent welcome email to %s', to_email)
            return True
        except Exception as e:
            app.logger.exception('Failed to send welcome email: %s', e)
            return False

    # send welcome email asynchronously would be better; here we attempt synchronously
    if email:
        try:
            send_welcome_email(email, name, username)
        except Exception:
            app.logger.warning('Error while trying to send welcome email')

    return jsonify({'success': True})


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing username or password'}), 400
    user = verify_user(username, password)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    return jsonify({'success': True, 'user': user})


@app.route('/api/auth/update', methods=['POST'])
def api_update_user():
    data = request.get_json() or {}
    username = data.get('username')
    updates = data.get('updates', {})
    if not username:
        return jsonify({'success': False, 'error': 'Missing username'}), 400
    ok, err = update_user(username, updates)
    if not ok:
        return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True})


@app.route('/api/auth/change_password', methods=['POST'])
def api_change_password():
    data = request.get_json() or {}
    username = data.get('username')
    current = data.get('current')
    new = data.get('new')
    if not username or not current or not new:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    ok, err = change_password(username, current, new)
    if not ok:
        return jsonify({'success': False, 'error': err}), 400
    return jsonify({'success': True})


@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    items = _load_conversations()
    return jsonify({'conversations': items})


@app.route('/api/conversations', methods=['POST'])
def add_conversation():
    data = request.get_json() or {}
    user_msg = data.get('user', '')
    ai_msg = data.get('ai', '')
    provided_id = data.get('id')
    title = data.get('title') or (user_msg[:40] + ('...' if len(user_msg) > 40 else ''))
    if not user_msg and not ai_msg:
        return jsonify({'success': False, 'error': 'Empty conversation'}), 400

    items = _load_conversations()
    # use provided id if present (for updates), otherwise generate one based on timestamp
    conv_id = provided_id or (datetime.utcnow().isoformat() + 'Z')
    item = {
        'id': conv_id,
        'title': title,
        'user': user_msg,
        'ai': ai_msg,
        'ts': datetime.utcnow().timestamp()
    }
    # prepend so newest first
    items.insert(0, item)
    _save_conversations(items)
    return jsonify({'success': True, 'item': item})


@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
    # create an empty conversation with a random id and return it
    import secrets
    conv_id = secrets.token_urlsafe(12)
    title = 'New chat'
    item = {
        'id': conv_id,
        'title': title,
        'user': '',
        'ai': '',
        'ts': datetime.utcnow().timestamp()
    }
    items = _load_conversations()
    items.insert(0, item)
    _save_conversations(items)
    return jsonify({'success': True, 'item': item})


@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    item = _find_conversation(conv_id)
    if not item:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'item': item})


@app.route('/c/<conv_id>/<path:slug>')
def serve_chat_with_id(conv_id, slug):
    # Serve the chat.html file for pretty conversation URLs
    return send_from_directory(ROOT, 'chat/chat.html')


if __name__ == "__main__":
    # Bind to localhost; use port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
