// auth.js - handles signup and login and talks to the backend

async function postJson(url, body){
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  return resp.json();
}

// Signup handler (works on unified auth page too)
async function handleSignup(name, username, password, email, errorEl){
  errorEl.textContent = '';
  if (!name || !username || !password || !email) { errorEl.textContent = 'Please fill all fields'; return false; }
  try{
    const data = await postJson('http://127.0.0.1:5000/api/auth/signup', { username, password, name, email });
    if (data.success){
      // auto-login after signup
      localStorage.setItem('aizeeno_user', JSON.stringify({ username: username, name: name, email: email }));
      // Redirect to home page (index) after signup
      setTimeout(()=> { location.href = 'index.html'; }, 350);
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
    const data = await postJson('http://127.0.0.1:5000/api/auth/login', { username, password });
    if (data.success){
      localStorage.setItem('aizeeno_user', JSON.stringify({ username: data.user.username, name: data.user.name }));
      // Redirect to home page (index) after login
      location.href = 'index.html';
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
    setTimeout(()=> location.href = '/auth/login.html', 200);
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
    loginBtn.addEventListener('click', async ()=>{
      const email = document.getElementById('loginEmail')?.value.trim();
      const password = document.getElementById('loginPassword')?.value;
      const errEl = getErrorEl(loginBox);
      errEl.textContent = '';
      loginBtn.disabled = true; loginBtn.textContent = 'Signing in...';
      try{
        await handleLogin(email, password, errEl);
      } finally { loginBtn.disabled = false; loginBtn.textContent = 'Login'; }
    });
    toSignup?.addEventListener('click', ()=> showSignup());
  }
});
