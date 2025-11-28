# Stripe Subscription Integration - Setup Guide

## ✅ Backend Configuration (main.py)

### 1. Environment Variables Loaded from `.env`
```
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
APP_DOMAIN=http://127.0.0.1:5000
```

### 2. Subscription Prices (Securely Stored in Backend)
```python
SUBSCRIPTION_PRICES = {
    'starter': 'price_1SXuv80LyafCNcpSqb2bzkuV',   # $5/month
    'pro': 'price_1RxTrF0LyafCNcpSe1VplNxT',       # $10/month
    'elite': 'price_1RxTrg0LyafCNcpSUz4TqZLV'      # $29.99/month
}
```

### 3. API Endpoints

#### GET /api/stripe-config
**Purpose:** Returns Stripe publishable key and subscription plans to frontend
**Response:**
```json
{
  "publishableKey": "pk_live_...",
  "prices": {
    "starter": "price_1SXuv80LyafCNcpSqb2bzkuV",
    "pro": "price_1RxTrF0LyafCNcpSe1VplNxT",
    "elite": "price_1RxTrg0LyafCNcpSUz4TqZLV"
  }
}
```

#### POST /api/create-checkout-session
**Purpose:** Creates a Stripe Checkout session for a specific plan
**Request:**
```json
{
  "plan": "starter|pro|elite"
}
```

**Response:**
```json
{
  "sessionId": "cs_live_..."
}
```

**Process:**
1. Frontend sends plan name
2. Backend looks up price ID from SUBSCRIPTION_PRICES
3. Backend creates Stripe Checkout session with that price
4. Returns sessionId to frontend
5. Frontend redirects to Stripe's hosted checkout page

---

## ✅ Frontend Configuration (subscription.html)

### 1. Three Subscription Buttons
```html
<button class="stripe-checkout" data-plan="starter">Subscribe Now</button>
<button class="stripe-checkout" data-plan="pro">Subscribe Now</button>
<button class="stripe-checkout" data-plan="elite">Subscribe Now</button>
```

### 2. JavaScript Flow
1. On page load:
   - Fetch `/api/stripe-config` to get publishable key and prices
   - Initialize Stripe with publishable key
   - Set up click handlers for all buttons

2. On button click:
   - Get plan name from `data-plan` attribute
   - Send POST to `/api/create-checkout-session` with plan
   - Receive sessionId from backend
   - Use Stripe.js to redirect to hosted checkout
   - User completes payment on Stripe's page
   - Returns to success_url or cancel_url

---

## 🔒 Security Features

✅ **Secret Key Protection**: Stripe secret key stored in .env, never exposed to frontend
✅ **Price ID Security**: Price IDs only stored on backend, frontend only sends plan names
✅ **Backend Validation**: Server validates plan names before creating sessions
✅ **HTTPS Ready**: Uses APP_DOMAIN for dynamic URLs
✅ **Error Handling**: Comprehensive error messages for debugging

---

## 🚀 How to Test

1. **Start Server:**
   ```bash
   cd py_system
   python main.py
   ```

2. **Open Subscription Page:**
   ```
   http://127.0.0.1:5000/templates/subscription.html
   ```

3. **Check Browser Console:**
   - Should see: "🔄 Initializing Stripe checkout..."
   - Should see: "✓ Config received: {publishableKey: 'pk_live_...', prices: {...}}"
   - Should see: "✓ Stripe initialized successfully"
   - Should see: "✓ Found 3 checkout button(s)"

4. **Click Subscribe Button:**
   - Should see: "🛒 Checkout initiated for plan: starter"
   - Should see: "📡 Sending checkout request for plan: starter"
   - Should see in server logs: "✓ Plan 'starter' -> Price ID: price_1SXuv..."
   - Should see: "✅ Checkout session created: cs_live_..."
   - Should redirect to Stripe checkout page

---

## 📋 Troubleshooting

### Issue: "Failed to load payment configuration"
**Solution:** Check browser console for specific error. Check server logs for:
- Is .env file being loaded?
- Is STRIPE_PUBLISHABLE_KEY set?
- Is /api/stripe-config returning 200 status?

### Issue: Button doesn't respond to click
**Solution:** Check browser console for errors in button click handler

### Issue: "Invalid subscription plan"
**Solution:** Ensure plan name matches exactly (starter, pro, or elite)

### Issue: Stripe checkout not opening
**Solution:** Check if sessionId is returned correctly from backend

---

## 🔄 Complete Request/Response Flow

```
User clicks Subscribe (Pro tier)
    ↓
Frontend: GET /api/stripe-config
    ↓
Backend: Returns publishableKey + prices
    ↓
Frontend: Initialize Stripe with publishableKey
    ↓
Frontend: Send POST /api/create-checkout-session with {plan: 'pro'}
    ↓
Backend: Look up 'pro' → 'price_1RxTrF0LyafCNcpSe1VplNxT'
    ↓
Backend: Call stripe.checkout.Session.create() with price ID
    ↓
Stripe: Create session and return sessionId
    ↓
Backend: Return {sessionId: 'cs_live_...'}
    ↓
Frontend: Call stripe.redirectToCheckout({sessionId: 'cs_live_...'})
    ↓
User: Redirected to Stripe's hosted checkout page
    ↓
User: Enters card details and completes payment
    ↓
Stripe: Redirect to success_url or cancel_url
```

---

## ✨ Key Points

- **Backend stores secrets**: Secret key, price IDs, and plan mapping
- **Frontend only sends plan names**: No sensitive data passed from frontend
- **Price lookup on backend**: Prevents frontend tampering with prices
- **Stripe handles payment**: We never touch user card data
- **Session-based**: Each checkout attempt creates a new session
- **Secure by default**: All sensitive data protected from client

