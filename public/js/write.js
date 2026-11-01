buildScene($("#scene")).setSun(1);
initAccount();
$("#schedule").min = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
$("#content").oninput = e => $("#count").textContent = e.target.value.length;

$("#form").onsubmit = async (e) => {
  e.preventDefault();
  const btn = $("#send"), status = $("#status"), when = $("#schedule").value;
  btn.disabled = true; status.textContent = "Reading it over…";
  try {
    const res = await fetch("/api/letters", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: $("#content").value, recipient: $("#recipient").value,
        scheduled_date: when || null, author_token: token }) });
    const data = await res.json();
    if (res.status === 422 && data.approved === false) { status.textContent = ""; $("#gentle").showModal(); return; }
    if (!res.ok) { status.textContent = typeof data.detail === "string" ? data.detail : "Something went wrong. Try again."; return; }
    status.textContent = when ? "Sealed until " + when + "." : "Pinned.";
    setTimeout(() => { location.href = when ? "wall.html#mine" : "wall.html#wall"; }, 700);
  } catch { status.textContent = "Can't reach the server. Is it running?"; }
  finally { btn.disabled = false; }
};
$("#gentle-ok").onclick = () => { $("#gentle").close(); const c = $("#content"); c.value = ""; $("#count").textContent = 0; c.placeholder = "Think of a small moment that made you smile…"; c.focus(); };
$("#gentle-close").onclick = () => { $("#gentle").close(); $("#content").focus(); };
