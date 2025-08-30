from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import re
import json
from datetime import datetime

app = Flask(__name__)

FAQ_FILE = os.path.join(app.root_path, 'data', 'faq.json')
LOG_FILE = os.path.join(app.root_path, 'logs', 'chat.log')

PII_PATTERNS = [
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    re.compile(r"\b\d{10,16}\b"),
]


def mask_pii(text):
    masked = text
    for p in PII_PATTERNS:
        masked = p.sub('[REDACTED]', masked)
    return masked


def ensure_dirs():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(FAQ_FILE), exist_ok=True)


def load_faq():
    if not os.path.exists(FAQ_FILE):
        return {}
    with open(FAQ_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def log_message(user_msg, bot_msg):
    ensure_dirs()
    entry = {
        'ts': datetime.utcnow().isoformat() + 'Z',
        'user': mask_pii(user_msg),
        'bot': mask_pii(bot_msg)
    }
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    return 'ok'


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'empty message'}), 400

    faq = load_faq()
    # simple rule-based match: exact or keyword
    reply = None
    for q, a in faq.items():
        if message.lower() == q.lower() or q.lower() in message.lower():
            reply = a
            break

    if not reply:
        # fallback echo + escalation hint
        reply = "I'm sorry, I don't know the exact answer. I've escalated this to human support."

    log_message(message, reply)
    return jsonify({'reply': reply})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
