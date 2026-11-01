const $ = (s) => document.querySelector(s);
buildScene($("#scene")).setSun(1);
const code = new URLSearchParams(location.search).get("token");
(code ? $("#set") : $("#ask")).hidden = false;

async function post(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { res, data: await res.json().catch(() => ({})) };
}
const errText = (d, fb) => typeof d.detail === "string" ? d.detail : fb;
function done(title, text, dev) {
  $("#ask").hidden = true; $("#set").hidden = true; $("#done").hidden = false;
  $("#done-title").textContent = title; $("#done-text").textContent = text; $("#done-dev").hidden = !dev;
}
$("#peek").onclick = () => { const p = $("#pw1"), s = p.type === "password"; p.type = $("#pw2").type = s ? "text" : "password"; $("#peek").textContent = s ? "Hide" : "Show"; };

$("#ask").onsubmit = async (e) => {
  e.preventDefault(); const msg = $("#ask-msg"), btn = $("#ask-btn"); msg.textContent = ""; btn.disabled = true;
  try {
    const { res, data } = await post("/api/auth/forgot", { email: $("#email").value.trim() });
    if (res.ok) done("Check your inbox", "If that email has a drawer, a link to choose a new password is on its way. It works for one hour.", data.mail === "console");
    else msg.textContent = errText(data, "Something went wrong. Please try again.");
  } catch { msg.textContent = "Can't reach the server. Is it running?"; }
  finally { btn.disabled = false; }
};
$("#set").onsubmit = async (e) => {
  e.preventDefault(); const msg = $("#set-msg"), btn = $("#set-btn"); msg.textContent = "";
  if ($("#pw1").value !== $("#pw2").value) { msg.textContent = "Those two don't match yet."; return; }
  btn.disabled = true;
  try {
    const { res, data } = await post("/api/auth/reset", { token: code, password: $("#pw1").value });
    if (res.ok) done("Password changed", "You can sign in with your new password now. Any device that was signed in has been signed out.", false);
    else { msg.textContent = errText(data, "Something went wrong. Please try again."); $("#again").hidden = false; }
  } catch { msg.textContent = "Can't reach the server. Is it running?"; }
  finally { btn.disabled = false; }
};
