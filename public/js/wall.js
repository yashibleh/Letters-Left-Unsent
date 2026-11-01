initAccount();
const echoed = new Set(JSON.parse(localStorage.getItem("echoed") || "[]"));
const SUBS = { wall: "Warm words, left for anyone who needs them.", mine: "Everything you've left unsent." };
const EMPTY = { wall: "The wall is bare. Be the first to pin something up.", mine: "Your drawer is empty. Write the first one." };
const view = () => location.hash === "#mine" ? "mine" : "wall";
let seq = 0;

function render() {
  const v = view();
  $("#viewtitle").textContent = v === "mine" ? "My drawer" : "The wall";
  $("#viewsub").textContent = SUBS[v];
  document.querySelectorAll("[data-view]").forEach(a => a.dataset.view === v ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  $("#feed").replaceChildren(); loadFeed(v);
}
addEventListener("hashchange", render); render();

let retryTimer = 0;
async function loadFeed(v, tries = 0) {
  const my = ++seq; clearTimeout(retryTimer);
  const empty = $("#empty"); empty.hidden = true;
  try {
    const res = await fetch("/api/letters" + (v === "mine" ? "?mine=" + encodeURIComponent(token) : ""), { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const letters = await res.json(); if (my !== seq) return;
    const feed = $("#feed"); feed.replaceChildren();
    empty.textContent = EMPTY[v]; empty.hidden = letters.length > 0;
    letters.forEach(l => feed.appendChild(card(l)));
  } catch (e) {
    if (my !== seq) return;
    empty.hidden = false;
    if (tries < 4) {
      empty.textContent = "Couldn't reach the letters just now. Trying again…";
      retryTimer = setTimeout(() => loadFeed(v, tries + 1), 2000 * (tries + 1));
    } else {
      empty.textContent = "Couldn't load the letters. Check that the server is running, then refresh the page.";
    }
  }
}
function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text) n.textContent = text; return n; }
function card(l) {
  const wrap = el("article", "frame"); wrap.style.transform = `rotate(${((l.id * 7) % 5 - 2) * .7}deg)`;
  const sheet = el("div", "sheet pt-5 pb-3"); wrap.appendChild(sheet);
  sheet.appendChild(el("span", "tape"));
  const d = new Date(l.timestamp.replace(" ", "T") + "Z");
  sheet.appendChild(el("div", "postmark", d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "2-digit" })));
  sheet.appendChild(el("p", "hand text-xl pl-16 pr-20", l.recipient ? "Dear " + l.recipient + "," : "To whom it may concern,"));
  sheet.appendChild(el("div", "letter-body", l.locked ? "Sealed. Opens " + l.scheduled_date + "." : l.content));
  const foot = el("div", "flex items-center justify-end px-5 pt-1 text-sm font-medium"); sheet.appendChild(foot);
  if (!l.locked) {
    const e = el("button", "stamp" + (echoed.has(l.id) ? " done" : ""), "Echo · " + l.echo_count);
    e.title = "Let the author know this reached someone";
    e.onclick = async () => {
      if (echoed.has(l.id)) return;
      const r = await fetch(`/api/letters/${l.id}/echo`, { method: "POST" }); if (!r.ok) return;
      const j = await r.json(); echoed.add(l.id); localStorage.setItem("echoed", JSON.stringify([...echoed]));
      e.textContent = "Echo · " + j.echo_count; e.classList.add("done");
    };
    foot.appendChild(e);
  }
  return wrap;
}
