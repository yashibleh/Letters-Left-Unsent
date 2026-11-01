// Scroll-driven story: lines fade in as you reach them, the sun climbs with your scroll, the last button leads on.
const $ = (s) => document.querySelector(s);
const scene = buildScene($("#scene")); scene.setSun(0);
const hint = $("#hint");

function onScroll() {
  const max = document.documentElement.scrollHeight - innerHeight;
  scene.setSun(max > 0 ? Math.min(1, scrollY / max) : 0);
  hint.style.opacity = scrollY > 40 ? 0 : 1;
}
addEventListener("scroll", onScroll, { passive: true }); onScroll();

const bits = [...document.querySelectorAll(".reveal")];
if ("IntersectionObserver" in window) {
  const io = new IntersectionObserver((entries) => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: .6, rootMargin: "0px 0px -8% 0px" });
  bits.forEach(b => io.observe(b));
} else bits.forEach(b => b.classList.add("in"));
