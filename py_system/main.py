import os
import json
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import stripe
from google.auth.transport import requests
from google.oauth2 import id_token

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ai_model import get_ai_reply

# ==================== CONFIG & PATHS ====================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'someone.json')
CHAT_DATA_FILE = os.path.join(BASE_DIR, 'data', 'chat_data_user.json')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Load environment variables with multiple path fallbacks
env_candidates = [
    os.path.join(BASE_DIR, '.env'),
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.join(os.getcwd(), '.env')
]
loaded_env = False
loaded_from = None
for p in env_candidates:
    if p and os.path.exists(p):
        load_dotenv(p)
        loaded_env = True
        loaded_from = p
        break

if not loaded_env:
    # Try load default (no path) — may still work if env already set in environment
    load_dotenv()

print(f"Attempted .env locations: {env_candidates}")
print(f"Loaded .env from: {loaded_from or 'default environment/none'}")

STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
APP_DOMAIN = os.getenv("APP_DOMAIN", "http://127.0.0.1:5000")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Normalize APP_DOMAIN (no trailing slash)
if APP_DOMAIN.endswith('/'):
    APP_DOMAIN = APP_DOMAIN[:-1]

print(f"STRIPE_PUBLISHABLE_KEY: {STRIPE_PUBLISHABLE_KEY[:20] + '...' if STRIPE_PUBLISHABLE_KEY else 'NOT SET'}")
print(f"STRIPE_SECRET_KEY: {'SET' if STRIPE_SECRET_KEY else 'NOT SET'}")
print(f"APP_DOMAIN: {APP_DOMAIN}")
print(f"STRIPE_WEBHOOK_SECRET: {'SET' if STRIPE_WEBHOOK_SECRET else 'NOT SET'}")
print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID[:20] + '...' if GOOGLE_CLIENT_ID else 'NOT SET'}")
print(f"GOOGLE_CLIENT_SECRET: {'SET' if GOOGLE_CLIENT_SECRET else 'NOT SET'}")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✓ Stripe secret key loaded.")
else:
    print("✗ ERROR: Stripe secret key missing in .env!")

SUBSCRIPTION_PRICES = {
    'starter': 'price_1SXuv80LyafCNcpSqb2bzkuV',   # $5/month
    'pro': 'price_1RxTrF0LyafCNcpSe1VplNxT',       # $10/month
    'elite': 'price_1RxTrg0LyafCNcpSUz4TqZLV'      # $29.99/month
}


# Validate price IDs with Stripe at startup (best-effort)
def validate_price_ids():
    if not STRIPE_SECRET_KEY:
        print('⚠️ Skipping Stripe price validation (secret key missing).')
        return
    print('🔎 Validating subscription price IDs with Stripe...')
    for name, pid in SUBSCRIPTION_PRICES.items():
        try:
            price = stripe.Price.retrieve(pid)
            active = getattr(price, 'active', None)
            product = getattr(price, 'product', None)
            print(f"  - {name}: {pid} -> active={active}, product={product}")
        except Exception as e:
            print(f"  - {name}: {pid} -> ERROR retrieving price: {e}")


validate_price_ids()

# ==================== FLASK APP SETUP ====================
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='/static')
CORS(app)

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
        # Verify webhook signature if secret available
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        event = None

        if STRIPE_WEBHOOK_SECRET:
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
                print('🔔 Webhook verified with signature')
            except Exception as e:
                print(f'❌ Webhook signature verification failed: {e}')
                return jsonify({'error': 'Webhook signature verification failed'}), 400
        else:
            # No webhook secret configured; attempt to parse event without verification (not recommended)
            try:
                event = json.loads(payload)
                print('⚠️ Webhook secret not configured; processing without signature verification')
            except Exception as e:
                print(f'❌ Failed to parse webhook payload: {e}')
                return jsonify({'error': 'Invalid payload'}), 400

        # Handle the event
        etype = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
        print(f'🔔 Received event: {etype}')

        if etype == 'checkout.session.completed':
            session = event['data']['object'] if isinstance(event, dict) else event['data']['object']
            # session should contain customer and subscription (for subscription mode)
            session_id = session.get('id') if isinstance(session, dict) else getattr(session, 'id', None)
            username = None
            # Try metadata first
            if isinstance(session, dict):
                username = session.get('metadata', {}).get('username') or session.get('client_reference_id')
            else:
                username = getattr(session, 'metadata', {}).get('username') if getattr(session, 'metadata', None) else None

            print(f" checkout.session.completed for session {session_id}, username={username}")

            # Retrieve expanded session from Stripe to get subscription id reliably
            try:
                full = stripe.checkout.Session.retrieve(session_id, expand=['subscription'])
                subs_id = getattr(full, 'subscription', None)
                cust_id = getattr(full, 'customer', None)
                print(f"    expanded session: customer={cust_id}, subscription={subs_id}")
            except Exception as e:
                print(f"    failed to retrieve full session: {e}")
                subs_id = None
                cust_id = None

            # Update user only if username is provided
            if username:
                try:
                    ok, err = update_user(username, {
                        'payment': True,
                        'subscription': session.get('metadata', {}).get('plan') if isinstance(session, dict) else None,
                        'stripe_customer_id': cust_id,
                        'stripe_subscription_id': subs_id
                    })
                    if ok:
                        print(f" Updated user {username} as paid (subscription={subs_id})")
                    else:
                        print(f" Failed to update user {username}: {err}")
                except Exception as e:
                    print(f" Exception updating user {username}: {e}")
            else:
                print(' No username in session metadata; cannot update user record')

        # Return 200 to acknowledge receipt
        return jsonify({'received': True})


# ==================== USER MANAGEMENT (IN-MEMORY) ====================
# Use an in-memory store to avoid filesystem permission/path issues during testing.
# This keeps existing API and helper functions working but removes persistence.
IN_MEMORY_DATA = {"users": []}


def _load():
    # Return the in-memory data structure
    return IN_MEMORY_DATA


def _save(data):
    # Replace the entire in-memory data structure
    global IN_MEMORY_DATA
    IN_MEMORY_DATA = data
    return


def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    # Use PBKDF2-HMAC-SHA256 with per-user random salt
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return dk.hex(), salt


def find_user(username: str) -> Optional[dict]:
    data = _load()
    for u in data.get('users', []):
        if u.get('username') == username:
            return u
    return None


def create_user(username: str, password: str, name: str, email: str = '') -> Tuple[bool, str]:
    data = _load()
    if find_user(username):
        return False, 'Username already exists'
    pwd_hash, salt = _hash_password(password)
    user = {
        "username": username,
        "password": pwd_hash,
        "salt": salt,
        "name": name,
        "email": email,
        "subscription": "free",
        "payment": False,
        "stripe_customer_id": None,
        "stripe_subscription_id": None
    }
    data.setdefault('users', []).append(user)
    _save(data)
    return True, ''


def verify_user(username: str, password: str) -> Optional[dict]:
    u = find_user(username)
    if not u:
        return None
    salt = u.get('salt')
    if not salt:
        # legacy fallback: stored password may be plain sha1 hex
        legacy = hashlib.sha1(password.encode('utf-8')).hexdigest()
        if u.get('password') == legacy:
            return {"username": u.get('username'), "name": u.get('name'), "email": u.get('email', '')}
        return None
    pwd_hash, _ = _hash_password(password, salt)
    if u.get('password') == pwd_hash:
        return {"username": u.get('username'), "name": u.get('name'), "email": u.get('email', '')}
    return None


def update_user(username: str, updates: dict) -> Tuple[bool, str]:
    data = _load()
    users = data.setdefault('users', [])
    for u in users:
        if u.get('username') == username:
            # allowed updates: name, email, subscription, payment, stripe ids
            if 'name' in updates:
                u['name'] = updates['name']
            if 'email' in updates:
                u['email'] = updates['email']
            if 'subscription' in updates:
                u['subscription'] = updates['subscription']
            if 'payment' in updates:
                u['payment'] = updates['payment']
            if 'stripe_customer_id' in updates:
                u['stripe_customer_id'] = updates['stripe_customer_id']
            if 'stripe_subscription_id' in updates:
                u['stripe_subscription_id'] = updates['stripe_subscription_id']
            _save(data)
            return True, ''
    return False, 'User not found'


def change_password(username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
    u = find_user(username)
    if not u:
        return False, 'User not found'
    salt = u.get('salt')
    if not salt:
        return False, 'Invalid user record'
    current_hash, _ = _hash_password(current_password, salt)
    if current_hash != u.get('password'):
        return False, 'Current password incorrect'
    new_hash, new_salt = _hash_password(new_password)
    u['password'] = new_hash
    u['salt'] = new_salt
    data = _load()
    _save(data)
    return True, ''

# ==================== CONVERSATION MANAGEMENT ====================
# Conversations in-memory store
IN_MEMORY_CONVERSATIONS = []


def _load_conversations():
    return IN_MEMORY_CONVERSATIONS


def _save_conversations(items):
    global IN_MEMORY_CONVERSATIONS
    IN_MEMORY_CONVERSATIONS = items


def _find_conversation(conv_id):
    for it in IN_MEMORY_CONVERSATIONS:
        if it.get('id') == conv_id:
            return it
    return None

# Note: static/template routes are registered after API routes to avoid
# accidental catch-all conflicts that can cause `/api/*` routes to return 404.

# ==================== FLASK ROUTES: API ====================
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "")
    reply = get_ai_reply(user_message)
    return jsonify({"response": reply})


@app.route("/api/chat/init", methods=["POST"])
def init_chat():
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
            body = f"Hello {to_name or to_username},\n\n"
            body += "Thanks for signing up to Aizeeno. Here are your account details:\n\n"
            body += f"Username: {to_username}\n"
            body += f"Email: {to_email}\n\n"
            body += "For your security we do not send your password by email. If you need to reset your password, use the app's account settings.\n\n"
            body += "Thanks and welcome!\nAizeeno team\n"
            msg.set_content(body)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            app.logger.info('Sent welcome email to %s', to_email)
            return True
        except Exception as e:
            app.logger.exception('Failed to send welcome email: %s', e)
            return False

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


@app.route('/api/auth/google', methods=['POST'])
def api_google_login():
    """Handle Google Sign-In: verify token and create/login user"""
    data = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({'success': False, 'error': 'Missing token'}), 400
    
    if not GOOGLE_CLIENT_ID:
        return jsonify({'success': False, 'error': 'Google not configured'}), 500
    
    try:
        # Verify the Google JWT token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo.get('email')
        name = idinfo.get('name', email)
        
        print(f"✓ Google token verified for {email}")
        
        # Check if user exists; if not, create one with username derived from email
        existing_user = find_user(email)
        if existing_user:
            print(f"  User {email} already exists, logging in")
            return jsonify({'success': True, 'user': {
                'username': existing_user.get('username'),
                'name': existing_user.get('name'),
                'email': existing_user.get('email')
            }})
        
        # Create new user with email as username
        username = email.split('@')[0] + '_' + secrets.token_hex(4)  # Avoid username conflicts
        ok, err = create_user(username, secrets.token_urlsafe(32), name, email)
        if not ok:
            print(f"  Failed to create user: {err}")
            return jsonify({'success': False, 'error': err}), 400
        
        print(f"  Created new user {username} from Google sign-in")
        return jsonify({'success': True, 'user': {
            'username': username,
            'name': name,
            'email': email
        }})
    except ValueError as e:
        print(f"✗ Google token verification failed: {e}")
        return jsonify({'success': False, 'error': 'Invalid Google token'}), 401
    except Exception as e:
        print(f"✗ Google auth error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
    conv_id = provided_id or (datetime.utcnow().isoformat() + 'Z')
    item = {
        'id': conv_id,
        'title': title,
        'user': user_msg,
        'ai': ai_msg,
        'ts': datetime.utcnow().timestamp()
    }
    items.insert(0, item)
    _save_conversations(items)
    return jsonify({'success': True, 'item': item})


@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
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

# ==================== FLASK ROUTES: OAUTH & AUTH CONFIG ====================
@app.route('/api/oauth-config', methods=['GET'])
def oauth_config():
    """Return OAuth configuration (Google, etc.) to frontend"""
    print(f"📡 /api/oauth-config called")
    response = {}
    if GOOGLE_CLIENT_ID:
        response['google'] = {'clientId': GOOGLE_CLIENT_ID}
        print(f"   Google Client ID: {GOOGLE_CLIENT_ID[:20]}...")
    return jsonify(response)


# ==================== FLASK ROUTES: STRIPE ====================
@app.route('/api/stripe-config', methods=['GET'])
def stripe_config():
    print(f"📡 /api/stripe-config called")
    print(f"   STRIPE_PUBLISHABLE_KEY: {STRIPE_PUBLISHABLE_KEY[:20] if STRIPE_PUBLISHABLE_KEY else 'MISSING'}...")
    print(f"   SUBSCRIPTION_PRICES: {SUBSCRIPTION_PRICES}")
    
    if not STRIPE_PUBLISHABLE_KEY:
        print("❌ ERROR: STRIPE_PUBLISHABLE_KEY is missing!")
        return jsonify({'error': 'Stripe publishable key not configured'}), 500
    
    response = {
        'publishableKey': STRIPE_PUBLISHABLE_KEY,
        'prices': SUBSCRIPTION_PRICES
    }
    print(f"✓ Returning config response")
    return jsonify(response)


def check_key_mode_mismatch():
    # Check if publishable/secret key types (test/live) match and log warnings
    if not STRIPE_PUBLISHABLE_KEY or not STRIPE_SECRET_KEY:
        return
    pk_live = STRIPE_PUBLISHABLE_KEY.startswith('pk_live')
    sk_live = STRIPE_SECRET_KEY.startswith('sk_live')
    pk_test = STRIPE_PUBLISHABLE_KEY.startswith('pk_test')
    sk_test = STRIPE_SECRET_KEY.startswith('sk_test')
    if (pk_live and sk_test) or (pk_test and sk_live):
        print('⚠️ Stripe key mode mismatch: publishable and secret keys appear to be for different modes (test vs live).')


check_key_mode_mismatch()


@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json() or {}
    plan = data.get('plan')

    print(f"📝 Checkout request received for plan: {plan}")

    if not plan:
        print("❌ ERROR: No plan specified")
        return jsonify({'error': 'Plan is required'}), 400

    if plan not in SUBSCRIPTION_PRICES:
        print(f"❌ ERROR: Invalid plan '{plan}'. Available: {list(SUBSCRIPTION_PRICES.keys())}")
        return jsonify({'error': f'Invalid subscription plan. Available: {list(SUBSCRIPTION_PRICES.keys())}'}), 400

    if not STRIPE_SECRET_KEY:
        print("❌ ERROR: Stripe secret key not configured")
        return jsonify({'error': 'Stripe secret key not configured'}), 500

    price_id = SUBSCRIPTION_PRICES[plan]
    print(f"✓ Plan '{plan}' -> Price ID: {price_id}")

    try:
        print(f"🔄 Creating Stripe checkout session...")
        # Use public-facing routes (not templates path) for return URLs
        success_url = f"{APP_DOMAIN}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}&plan={plan}"
        cancel_url = f"{APP_DOMAIN}/subscription/canceled?plan={plan}"

        session = stripe.checkout.Session.create(
            success_url=success_url,
            cancel_url=cancel_url,
            mode='subscription',
            payment_method_types=["card"],
            line_items=[{
                'price': price_id,
                'quantity': 1
            }],
            metadata={'plan': plan, 'username': data.get('username')} if data.get('username') else {'plan': plan},
        )

        print(f"✅ Checkout session created: {session.id}")
        return jsonify({'sessionId': session.id})

    except Exception as e:
        print(f"❌ Stripe error creating session: {str(e)}")
        app.logger.exception("Stripe checkout error")
        return jsonify({'error': str(e)}), 500


@app.route('/api/payment-status', methods=['POST'])
def payment_status():
    """Check and update payment status from Stripe session"""
    data = request.get_json() or {}
    username = data.get('username')
    session_id = data.get('session_id')
    plan = data.get('plan')
    
    if not username or not session_id or not plan:
        return jsonify({'error': 'Missing username, session_id, or plan'}), 400
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id, expand=['subscription'])

        print(f"📋 Payment status check for {username}: payment_status={getattr(session, 'payment_status', None)}")
        print(f"    session.customer={getattr(session, 'customer', None)}, subscription={getattr(session, 'subscription', None)}")

        # If there is a subscription object expand further and log
        sub_id = getattr(session, 'subscription', None)
        if sub_id:
            try:
                sub = stripe.Subscription.retrieve(sub_id)
                print(f"    subscription.id={sub.id}, status={sub.status}, current_period_end={getattr(sub, 'current_period_end', None)}")
            except Exception as e:
                print(f"    could not retrieve subscription {sub_id}: {e}")

        # Check if payment was successful
        if getattr(session, 'payment_status', None) == 'paid':
            print(f"✅ Payment confirmed for {username} - Plan: {plan}")

            # Update user with subscription info
            updates = {
                'payment': True,
                'subscription': plan,
                'stripe_customer_id': session.customer,
                'stripe_subscription_id': session.subscription
            }

            ok, err = update_user(username, updates)
            if ok:
                return jsonify({
                    'success': True,
                    'payment': True,
                    'subscription': plan,
                    'message': f'Payment successful! Welcome to {plan.upper()} plan'
                })
            else:
                return jsonify({'error': 'Failed to update user subscription'}), 500
        else:
            print(f"⏳ Payment pending for {username}")
            return jsonify({
                'success': True,
                'payment': False,
                'payment_status': getattr(session, 'payment_status', None),
                'message': 'Payment is pending'
            })
    
    except Exception as e:
        print(f"❌ Error checking payment status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user-subscription/<username>', methods=['GET'])
def user_subscription(username):
    """Get user's subscription and payment status"""
    user = find_user(username)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'username': user.get('username'),
        'subscription': user.get('subscription', 'free'),
        'payment': user.get('payment', False),
        'stripe_customer_id': user.get('stripe_customer_id'),
        'stripe_subscription_id': user.get('stripe_subscription_id')
    })


@app.route('/c/<conv_id>/<path:slug>')
def serve_chat_with_id(conv_id, slug):
    """Serve chat page for conversation URLs"""
    return send_from_directory(TEMPLATES_DIR, 'chat.html')

# ==================== FLASK ROUTES: STATIC & TEMPLATES ====================
@app.route('/')
def index_page():
    return send_from_directory(TEMPLATES_DIR, 'index.html')


@app.route('/<path:page>')
def serve_template_page(page):
    allowed_ext = ('.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.json')
    if any(page.endswith(ext) for ext in allowed_ext):
        safe_page = page.replace('..', '')
        return send_from_directory(TEMPLATES_DIR, safe_page)
    return send_from_directory(TEMPLATES_DIR, 'index.html')


@app.route('/templates/<path:page>')
def serve_templates_dir(page):
    safe_page = page.replace('..', '')
    return send_from_directory(TEMPLATES_DIR, safe_page)


# Serve subscription page at a friendly route
@app.route('/subscription')
def subscription_page():
    return send_from_directory(TEMPLATES_DIR, 'subscription.html')


# Friendly success/cancel routes used by Stripe
@app.route('/subscription/success')
def subscription_success():
    # The frontend reads session_id and plan from the querystring and verifies
    return send_from_directory(TEMPLATES_DIR, 'subscription.html')


@app.route('/subscription/canceled')
def subscription_canceled():
    return send_from_directory(TEMPLATES_DIR, 'subscription.html')


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
