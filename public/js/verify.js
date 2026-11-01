const $ = (s) => document.querySelector(s);
buildScene($("#scene")).setSun(1);
const code = new URLSearchParams(location.search).get("token");
function show(title, text, ok) { $("#v-title").textContent = title; $("#v-text").textContent = text; $("#v-go").hidden = false; $("#v-go").textContent = ok ? "Sign in" : "Back to sign in"; }
if (!code) show("This link is incomplete", "Please open the link from your email again.", false);
else fetch("/api/auth/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: code }) })
  .then(async r => { const d = await r.json().catch(() => ({}));
    if (r.ok) show("Email confirmed", "Your drawer is ready. Sign in and write your first letter.", true);
    else show("That link didn't work", typeof d.detail === "string" ? d.detail : "Please try again.", false); })
  .catch(() => show("Can't reach the server", "Is it running? Open the link again once it is.", false));
