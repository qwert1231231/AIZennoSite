// Refactored subscription JS: robust fetch wrapper, Stripe init, checkout flow

async function fetchJson(url, options = {}) {
  // If a relative path is provided, prefix the backend base URL so frontend (port 5500)
  // can access the Flask backend on port 5000.
  if (!/^https?:\/\//i.test(url)) {
    url = BACKEND_BASE + url;
  }
  try {
    const res = await fetch(url, options);
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { raw: text }; }
    if (!res.ok) {
      const err = (data && data.error) ? data.error : `HTTP ${res.status}`;
      throw new Error(err);
    }
    return data;
  } catch (err) {
    throw err;
  }
}

// Fetch with retries + exponential backoff and origin fallback
async function fetchWithRetries(path, options = {}, attempts = 4, initialDelay = 400) {
  let lastErr = null;
  const originUrl = (typeof location !== 'undefined' && location.origin) ? location.origin + path : null;
  for (let i = 0; i < attempts; i++) {
    try {
      const urlToUse = (i === attempts - 1 && originUrl) ? originUrl : path;
      if (i > 0) console.log(`[subscription] Retry ${i}/${attempts} fetching ${urlToUse}`);
      const data = await fetchJson(urlToUse, options);
      return data;
    } catch (err) {
      lastErr = err;
      const delay = initialDelay * Math.pow(2, i);
      // brief sleep
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw lastErr;
}

// Verify completed payments when returning from Stripe
async function handleReturnFromStripe() {
  const urlParams = new URLSearchParams(window.location.search);
  const sessionId = urlParams.get('session_id');
  const plan = urlParams.get('plan');
  if (!sessionId) return;

  console.log('[subscription] Found session_id in URL:', sessionId);

  const userStr = localStorage.getItem('aizeeno_user');
  if (!userStr) {
    console.warn('[subscription] No local user found; cannot verify payment.');
    alert('Please log in to verify your payment.');
    return;
  }
  const user = JSON.parse(userStr);

  try {
    const payload = { username: user.username, session_id: sessionId, plan };
    const result = await fetchJson('/api/payment-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    console.log('[subscription] payment-status response', result);

    if (result.success && result.payment) {
      user.subscription = result.subscription || plan || user.subscription || 'starter';
      user.payment = true;
      localStorage.setItem('aizeeno_user', JSON.stringify(user));
      alert(result.message || 'Payment confirmed. Thank you!');
      setTimeout(() => { window.location.href = '/templates/chat.html'; }, 800);
      return;
    }

    if (result.success && !result.payment) {
      alert('Payment not confirmed yet. Please wait a few moments and refresh.');
      return;
    }

    throw new Error(result.error || 'Unknown payment verification response');
  } catch (err) {
    console.error('[subscription] Error verifying payment:', err);
    alert('Unable to verify payment: ' + (err.message || err));
  }
}

// Main init function
async function initSubscription() {
  console.log('[subscription] Initializing subscription flow');

  // Load Stripe config from backend (with retries and origin fallback)
  let config;
  try {
    config = await fetchWithRetries('/api/stripe-config', {}, 5, 300);
  } catch (err) {
    console.error('[subscription] Failed to load Stripe config after retries:', err);
    // Give user details and quick troubleshooting steps
    const msg = 'Failed to load payment configuration.\n\n' +
      'Possible causes:\n' +
      '- Server is not running (start the Flask app).\n' +
      '- Network/firewall blocking localhost requests.\n' +
      const BACKEND_BASE = 'http://127.0.0.1:5000';
      '- Server returned an error (check server logs).\n\n' +
      'Technical details: ' + (err && err.message ? err.message : String(err));
    alert(msg);
    return;
  }

  const publishableKey = config.publishableKey;
  const prices = config.prices || {};
  if (!publishableKey) {
    console.error('[subscription] Missing publishableKey in config');
    alert('Payment system not configured. Contact support.');
    return;
  }

  // Initialize Stripe once
  let stripe;
  try {
    stripe = Stripe(publishableKey);
      async function fetchWithRetries(path, options = {}, attempts = 4, initialDelay = 400) {
        let lastErr = null;
        // Ensure absolute URL: if path already absolute, use it; otherwise prefix BACKEND_BASE
        const makeUrl = (p) => (/^https?:\/\//i.test(p) ? p : BACKEND_BASE + p);
        for (let i = 0; i < attempts; i++) {
          try {
            const urlToUse = makeUrl(path);
            if (i > 0) console.log(`[subscription] Retry ${i}/${attempts} fetching ${urlToUse}`);
            const data = await fetchJson(urlToUse, options);
            return data;
          } catch (err) {
            lastErr = err;
            const delay = initialDelay * Math.pow(2, i);
            // brief sleep
            await new Promise(r => setTimeout(r, delay));
          }
        }
        throw lastErr;
      }
        window.location.href = '/templates/login.html';
        return;
      }

      btn.disabled = true;
      const orig = btn.textContent;
      btn.textContent = 'Processing...';

      try {
        // Create Checkout session (use retries for transient errors)
        const payload = { plan };
        const resp = await fetchWithRetries('/api/create-checkout-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }, 3, 300);

        const sessionId = resp.sessionId || resp.id || resp.session_id;
        if (!sessionId) throw new Error('No session id returned from server');

        // Redirect to checkout
        const { error } = await stripe.redirectToCheckout({ sessionId });
        if (error) throw error;
      } catch (err) {
        console.error('[subscription] Checkout error:', err);
        alert('Unable to start checkout: ' + (err.message || err));
      } finally {
        btn.disabled = false;
        btn.textContent = orig;
      }
    });
  });

  console.log('[subscription] Handlers attached for', buttons.length, 'buttons.');

  // If we were returned from Stripe, try to verify
  handleReturnFromStripe();
}

// Kick it off when DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSubscription);
} else {
  initSubscription();
}
