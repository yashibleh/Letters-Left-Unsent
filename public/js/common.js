const $ = (s) => document.querySelector(s);
const token = localStorage.getItem("token") || (() => { const t = crypto.randomUUID(); localStorage.setItem("token", t); return t; })();

// shows "Hi, name" + Sign out when signed in, "Sign in" otherwise
function initAccount(onUser) {
  fetch("/api/auth/me").then(r => r.json()).then(({ user }) => {
    if (onUser) onUser(user);
    if (!user) return;
    const s = $("#signin"), o = $("#signout"), w = $("#who");
    if (s) s.hidden = true;
    if (o) o.hidden = false;
    if (w) { w.hidden = false; w.textContent = "Hi, " + (user.display_name || user.email.split("@")[0]); }
  }).catch(() => {});
  const out = $("#signout");
  if (out) out.onclick = async () => { await fetch("/api/auth/logout", { method: "POST" }); location.reload(); };
}
