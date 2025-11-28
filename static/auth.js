// auth.js - handles signup and login and talks to the backend

// Default to local backend if a global BACKEND_BASE isn't provided by the page
const API_BASE = (typeof BACKEND_BASE !== 'undefined') ? BACKEND_BASE : 'http://127.0.0.1:5000';

async function postJson(url, body){
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const text = await resp.text();
  const ctype = resp.headers.get('content-type') || '';
  if (!text) {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return {};
  }
  // If response is JSON, parse it. Otherwise return raw text for non-JSON OK responses.
  if (ctype.includes('application/json')){
    const data = JSON.parse(text);
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    return data;
  }
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return { raw: text };
}

// Safe GET that tolerates empty responses and non-JSON bodies
async function getJson(url){
  const resp = await fetch(url, { method: 'GET' });
  const text = await resp.text();
  const ctype = resp.headers.get('content-type') || '';
  if (!text) {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return {};
  }
  if (ctype.includes('application/json')){
    const data = JSON.parse(text);
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    return data;
  }
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return { raw: text };
}

// Signup handler (works on unified auth page too)
async function handleSignup(name, username, password, email, errorEl){
  errorEl.textContent = '';
  if (!name || !username || !password || !email) { errorEl.textContent = 'Please fill all fields'; return false; }
  try{
    const data = await postJson(API_BASE + '/api/auth/signup', { username, password, name, email });
    if (data.success){
      // auto-login after signup
      localStorage.setItem('aizeeno_user', JSON.stringify({ username: username, name: name, email: email }));
      // Redirect to home page (index) after signup
      setTimeout(()=> { location.href = '/templates/index.html'; }, 350);
      return true;
    } else {
      errorEl.textContent = data.error || 'Signup failed';
      return false;
    }
  } catch (err){
    errorEl.textContent = 'Network error';
    return false;
  }
}

// Login handler (works on unified auth page too)
async function handleLogin(username, password, errorEl){
  errorEl.textContent = '';
  if (!username || !password){ errorEl.textContent = 'Please fill both fields'; return false; }
  try{
    const data = await postJson(API_BASE + '/api/auth/login', { username, password });
    if (data.success){
      localStorage.setItem('aizeeno_user', JSON.stringify({ username: data.user.username, name: data.user.name }));
      // Redirect to home page (index) after login
      location.href = '/templates/index.html';
      return true;
    } else {
      errorEl.textContent = data.error || 'Login failed';
      return false;
    }
  } catch (err){
    errorEl.textContent = 'Network error';
    return false;
  }
}

// Optional: protect chat.html by checking sessionStorage on load
// Protect chat.html by checking localStorage for a persisted login on page load
// Protect chat.html by checking localStorage for a persisted login on page load
if (location.pathname.endsWith('chat.html')){
  const u = localStorage.getItem('aizeeno_user');
  if (!u){
    setTimeout(()=> location.href = '/templates/login.html', 200);
  }
}

// Expose helpers to the unified auth page (if loaded)
window.authHelpers = { handleLogin, handleSignup };

// UI bindings for unified auth pages (if present)
document.addEventListener('DOMContentLoaded', ()=>{
  const signupBox = document.getElementById('signupBox');
  const loginBox = document.getElementById('loginBox');

  function showSignup(){ if (signupBox) signupBox.classList.remove('hidden'); if (loginBox) loginBox.classList.add('hidden'); }
  function showLogin(){ if (loginBox) loginBox.classList.remove('hidden'); if (signupBox) signupBox.classList.add('hidden'); }

  function getErrorEl(container){
    if (!container) return { textContent: '' };
    let el = container.querySelector('.auth-error');
    if (!el){ el = document.createElement('div'); el.className = 'auth-error'; el.style.color = '#b00020'; el.style.marginTop = '10px'; container.appendChild(el); }
    return el;
  }

  if (signupBox){
    const btn = document.getElementById('signupBtn');
    const terms = document.getElementById('terms');
    const toLogin = document.getElementById('toLogin');
    btn.addEventListener('click', async ()=>{
      const first = document.getElementById('firstName')?.value.trim();
      const last = document.getElementById('lastName')?.value.trim();
      const username = document.getElementById('username')?.value.trim();
      const email = document.getElementById('email')?.value.trim();
      const password = document.getElementById('password')?.value;
      const errEl = getErrorEl(signupBox);
      errEl.textContent = '';
      if (!terms || !terms.checked){ errEl.textContent = 'You must accept the Terms & Policy to continue.'; return; }
      if (!first || !username || !email || !password){ errEl.textContent = 'Please fill all required fields.'; return; }
      btn.disabled = true; btn.textContent = 'Creating...';
      try{
        const name = first + (last ? (' ' + last) : '');
        await handleSignup(name, username, password, email, errEl);
      } finally { btn.disabled = false; btn.textContent = 'Create Account'; }
    });
    toLogin?.addEventListener('click', ()=> showLogin());
  }

  if (loginBox){
    const loginBtn = document.getElementById('loginBtn');
    const toSignup = document.getElementById('toSignup');
    const googleSigninBtn = document.getElementById('googleSigninBtn');
    loginBtn.addEventListener('click', async ()=>{
      const email = document.getElementById('loginEmail')?.value.trim();
      const password = document.getElementById('loginPassword')?.value;
      const errEl = getErrorEl(loginBox);
      errEl.textContent = '';
      loginBtn.disabled = true; loginBtn.textContent = 'Signing in...';
      try{
        await handleLogin(email, password, errEl);
      } finally { loginBtn.disabled = false; loginBtn.textContent = 'Sign In'; }
    });
    toSignup?.addEventListener('click', ()=> showSignup());
    
    // Google Sign-In button
    if (googleSigninBtn){
      googleSigninBtn.addEventListener('click', async ()=>{
        try {
          const oauthConfig = await getJson(API_BASE + '/api/oauth-config');
          if (!oauthConfig.google || !oauthConfig.google.clientId) {
            getErrorEl(loginBox).textContent = 'Google Sign-In not configured';
            return;
          }
          // Initialize Google Sign-In
          initGoogleSignIn(oauthConfig.google.clientId, loginBox);
        } catch (err) {
          getErrorEl(loginBox).textContent = 'Failed to load Google Sign-In: ' + err.message;
        }
      });
    }
  }
});

// Google Sign-In integration
function initGoogleSignIn(clientId, loginBox) {
  // Load Google Identity Services library
  if (!window.google) {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      window.google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCallback });
      window.google.accounts.id.prompt();
    };
    document.head.appendChild(script);
  } else {
    window.google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCallback });
    window.google.accounts.id.prompt();
  }
}

async function handleGoogleCallback(response) {
  // response.credential is the JWT token
  const token = response.credential;
  console.log('Google Sign-In token received');
  
  try {
    // Send token to backend for verification and user creation/login
    const data = await postJson(API_BASE + '/api/auth/google', { token });
    if (data.success) {
      localStorage.setItem('aizeeno_user', JSON.stringify({ username: data.user.username, name: data.user.name, email: data.user.email }));
      alert('Welcome! Signing you in...');
      setTimeout(() => { location.href = '/templates/index.html'; }, 500);
    } else {
      alert('Google Sign-In failed: ' + (data.error || 'Unknown error'));
    }
  } catch (err) {
    alert('Error processing Google Sign-In: ' + err.message);
  }
}
