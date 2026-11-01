const $ = (s) => document.querySelector(s);
buildScene($("#scene")).setSun(1);
let mode = "login", lastEmail = "";
const LEAD = { login: "Welcome back. Your drawer kept everything safe.", register: "A drawer keeps your letters with you, on any device." };

async function post(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { res, data: await res.json().catch(() => ({})) };
}
const errText = (d, fallback) => typeof d.detail === "string" ? d.detail : fallback;

function setMode(m) {
  mode = m;
  document.querySelectorAll("[data-mode]").forEach(b => b.setAttribute("aria-selected", b.dataset.mode === m));
  $("#lead").textContent = LEAD[m];
  $("#nameRow").hidden = m !== "register";
  $("#forgot-row").hidden = m !== "login";
  $("#submit").textContent = m === "login" ? "Sign in" : "Create my drawer";
  $("#password").autocomplete = m === "login" ? "current-password" : "new-password";
  $("#password").placeholder = m === "register" ? "at least 8 characters" : "";
  $("#msg").textContent = ""; $("#resend").hidden = true;
  $("#fields").hidden = false; $("#sent").hidden = true;
}
document.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => setMode(b.dataset.mode));
if (location.hash === "#register") setMode("register");
$("#peek").onclick = () => { const p = $("#password"), show = p.type === "password"; p.type = show ? "text" : "password"; $("#peek").textContent = show ? "Hide" : "Show"; };

// already signed in? carry on
fetch("/api/auth/me").then(r => r.json()).then(d => { if (d.user) location.replace("app.html"); }).catch(() => {});

function showSent(email, mail) {
  lastEmail = email;
  $("#lead").textContent = "One more step.";
  $("#fields").hidden = true; $("#sent").hidden = false;
  $("#sent-email").textContent = email; $("#sent-dev").hidden = mail !== "console"; $("#sent-msg").textContent = "";
}
async function resend(out) {
  const email = $("#email").value.trim() || lastEmail;
  out.textContent = "Sending…";
  try {
    const { res, data } = await post("/api/auth/resend", { email });
    out.textContent = res.ok ? "A fresh link is on its way." : errText(data, "Couldn't send it just now.");
  } catch { out.textContent = "Can't reach the server. Is it running?"; }
}
$("#resend").onclick = () => resend($("#msg"));
$("#resend2").onclick = () => resend($("#sent-msg"));

$("#auth").onsubmit = async (e) => {
  e.preventDefault();
  const msg = $("#msg"), btn = $("#submit"), email = $("#email").value.trim();
  msg.textContent = ""; $("#resend").hidden = true; btn.disabled = true;
  try {
    const { res, data } = await post("/api/auth/" + mode, { email, password: $("#password").value,
      display_name: $("#name").value, claim_token: localStorage.getItem("token") || "" });
    if (res.ok && data.needs_verification) { showSent(email, data.mail); return; }
    if (res.ok) { location.href = "app.html"; return; }
    msg.textContent = errText(data, "Please check your email and password.");
    if (data.needs_verification) $("#resend").hidden = false;
  } catch { msg.textContent = "Can't reach the server. Is it running?"; }
  finally { btn.disabled = false; }
};
