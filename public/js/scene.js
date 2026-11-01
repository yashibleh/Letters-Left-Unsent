// Paper-cut landscape in three colours: ice silver, deep aubergine, a little marigold.
// Everything is flat cut paper: no outlines, a soft lift-shadow, and pointed edges like the firs.
(function () {
  const C = { ice: "#e4eaf0", ice2: "#c9d3dd", ice3: "#f3f6f9", silver: "#b9c5d2", aub: "#2f1533", aub2: "#4d2753", mari: "#e0a93b" };
  const M2 = "#f0c96a", M3 = "#c98f22";                       // lighter and deeper marigold, for layered paper
  const NS = "http://www.w3.org/2000/svg";
  const mk = (t, a = {}, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  let sd = 3; const rnd = () => (sd = sd * 16807 % 2147483647) / 2147483647;
  const cut = (p) => mk("g", { filter: "url(#cut)" }, p);     // gives a shape the paper-cut edge and shadow

  function star(cx, cy, R, r, n, rot = 0) {                   // n-pointed star path
    let d = "";
    for (let i = 0; i < n * 2; i++) {
      const a = Math.PI * i / n - Math.PI / 2 + rot, rad = i % 2 ? r : R;
      d += (i ? "L" : "M") + (cx + Math.cos(a) * rad).toFixed(1) + " " + (cy + Math.sin(a) * rad).toFixed(1);
    }
    return d + "Z";
  }
  function fir(g, x, y, h, op) {                              // paper-cut fir tree
    mk("rect", { x: x - h * .03, y: y - h * .12, width: h * .06, height: h * .14, fill: C.aub, opacity: op }, g);
    for (let i = 0; i < 4; i++) {
      const ty = y - h * .1 - i * h * .22, tw = h * .5 * (1 - i * .2) * (.9 + rnd() * .2);
      mk("path", { d: `M${x - tw / 2} ${ty}L${x + (rnd() - .5) * 4} ${ty - h * .34}L${x + tw / 2} ${ty}Z`, fill: C.aub, opacity: op }, g);
    }
  }
  function stemAndLeaves(f, x, y, h) {
    mk("path", { d: `M${x - 1.6} ${y}Q${x + 6} ${y - h * .5} ${x + .4} ${y - h}L${x + 3.4} ${y - h}Q${x + 9} ${y - h * .5} ${x + 1.6} ${y}Z`, fill: C.aub }, f);
    mk("path", { d: `M${x + 2} ${y - h * .28}Q${x + 17} ${y - h * .3} ${x + 25} ${y - h * .56}Q${x + 8} ${y - h * .5} ${x + 2} ${y - h * .28}Z`, fill: C.aub2 }, f);
    mk("path", { d: `M${x + 1} ${y - h * .46}Q${x - 14} ${y - h * .46} ${x - 21} ${y - h * .72}Q${x - 5} ${y - h * .69} ${x + 1} ${y - h * .46}Z`, fill: C.aub2 }, f);
  }
  function tulip(g, x, y, h) {                                // three-pointed paper tulip, two layers
    const f = cut(g); stemAndLeaves(f, x, y, h);
    const b = mk("g", { transform: `translate(${x + 2} ${y - h})` }, f);
    mk("path", { d: "M-9 0Q-12-14-8-23L-3-11L0-25L3-11L8-23Q12-14 9 0Q0 7-9 0Z", fill: C.mari }, b);
    mk("path", { d: "M-5 0Q-7-9-4-15L0-7L4-15Q7-9 5 0Q0 4-5 0Z", fill: M2 }, b);
  }
  function daisy(g, x, y, h) {                                // eight-pointed star flower, three layers
    const f = cut(g); stemAndLeaves(f, x, y, h);
    mk("path", { d: star(x + 2, y - h, 16, 7, 8), fill: M3 }, f);
    mk("path", { d: star(x + 2, y - h, 13, 5.5, 8, Math.PI / 8), fill: C.mari }, f);
    mk("circle", { cx: x + 2, cy: y - h, r: 4.2, fill: M2 }, f);
    mk("circle", { cx: x + 2, cy: y - h, r: 1.8, fill: C.aub }, f);
  }
  function postbox(g, x, y, s) {                              // a little post box with a letter going in, built from layers of paper
    const f = cut(mk("g", { transform: `translate(${x} ${y}) scale(${s})` }, g));
    mk("path", { d: "M-5 0L-4 -46L4 -46L5 0Z", fill: C.aub }, f);                                    // post
    mk("path", { d: "M-15 0L-11 -9L-7 0ZM7 0L11 -9L15 0Z", fill: C.aub, opacity: .85 }, f);            // two little grass tufts
    mk("path", { d: "M-26 -46V-88Q-26 -108 0 -108Q26 -108 26 -88V-46Z", fill: C.aub }, f);            // back layer
    mk("path", { d: "M-22 -50V-87Q-22 -103 0 -103Q22 -103 22 -87V-50Z", fill: C.aub2 }, f);           // front layer
    mk("rect", { x: -9, y: -100, width: 18, height: 13, rx: 1.5, fill: C.ice3 }, f);                  // letter poking out of the slot
    mk("path", { d: "M-9 -100L0 -93L9 -100Z", fill: C.ice2 }, f);
    mk("circle", { cx: 0, cy: -93, r: 2.4, fill: C.mari }, f);
    mk("rect", { x: -14, y: -90, width: 28, height: 6, rx: 3, fill: C.aub }, f);                        // the slot
    mk("rect", { x: 26, y: -96, width: 3, height: 32, fill: C.aub }, f);                                // flag pole
    mk("path", { d: "M29 -96H49L43 -89L49 -82H29Z", fill: C.mari }, f);                                // swallow-tail flag
    mk("path", { d: "M29 -90H42L40 -89L42 -88H29Z", fill: M2 }, f);
  }
  function floater(g, x, y, rot, s, delay, draw) {
    const o = mk("g", { transform: `translate(${x} ${y}) rotate(${rot}) scale(${s})` }, g);
    draw(cut(mk("g", { class: "float", style: `animation-delay:${delay}s` }, o)));
  }
  const envelope = (f) => {
    mk("rect", { x: -31, y: -21, width: 62, height: 42, rx: 2.5, fill: C.ice3 }, f);
    mk("path", { d: "M-31 21L-2 0L-31 -5ZM31 21L2 0L31 -5Z", fill: C.ice2, opacity: .6 }, f);          // lower folds
    mk("path", { d: "M-31 -21H31L0 5Z", fill: C.ice2 }, f);                                           // flap
    mk("circle", { cx: 0, cy: 4, r: 6, fill: M3 }, f); mk("circle", { cx: 0, cy: 4, r: 4.6, fill: C.mari }, f);
    mk("circle", { cx: 0, cy: 4, r: 1.9, fill: M2 }, f);                                              // wax seal
  };
  const plane = (f) => {
    mk("path", { d: "M-34 4L34-18L8 21Z", fill: C.ice3 }, f);
    mk("path", { d: "M-34 4L34-18L2 5Z", fill: C.ice2 }, f);
    mk("path", { d: "M2 5L8 21L13-9Z", fill: C.silver }, f);
    [[-44, 10, 2.6], [-54, 15, 2], [-63, 19, 1.5]].forEach(([cx, cy, r]) => mk("circle", { cx, cy, r, fill: C.mari, opacity: .85 }, f));
  };
  const heart = (f) => mk("path", { d: "M0 8C-15-3-10-17 0-9C10-17 15-3 0 8Z", fill: C.mari }, f);

  window.buildScene = function (svg) {
    svg.replaceChildren(); sd = 3;
    // sky + sun live on their own layer behind the scene, so the sun can move without the heavy filters repainting
    const old = document.getElementById("scene-back"); if (old) old.remove();
    const back = svg.cloneNode(false); back.id = "scene-back"; back.replaceChildren();
    svg.parentNode.insertBefore(back, svg);
    const bdefs = mk("defs", {}, back), defs = mk("defs", {}, svg);
    const sky = mk("linearGradient", { id: "sky", x1: 0, y1: 0, x2: 0, y2: 1 }, bdefs);
    [[0, "#c3cfdb"], [.55, C.ice3], [1, C.ice]].forEach(([o, c]) => mk("stop", { offset: o, "stop-color": c }, sky));
    const glow = mk("radialGradient", { id: "glow" }, bdefs);
    mk("stop", { offset: 0, "stop-color": C.mari, "stop-opacity": .55 }, glow); mk("stop", { offset: 1, "stop-color": C.mari, "stop-opacity": 0 }, glow);
    const wc = mk("filter", { id: "wc", x: "-20%", y: "-30%", width: "140%", height: "160%" }, defs);
    mk("feTurbulence", { type: "fractalNoise", baseFrequency: ".012", numOctaves: 3, seed: 3, result: "n" }, wc);
    mk("feDisplacementMap", { in: "SourceGraphic", in2: "n", scale: 40 }, wc); mk("feGaussianBlur", { stdDeviation: 3 }, wc);
    const torn = mk("filter", { id: "torn", x: "-3%", y: "-10%", width: "106%", height: "125%" }, defs);   // torn paper edge + soft lift (hills, firs)
    mk("feTurbulence", { type: "fractalNoise", baseFrequency: ".025 .06", numOctaves: 2, seed: 7, result: "t" }, torn);
    mk("feDisplacementMap", { in: "SourceGraphic", in2: "t", scale: 7 }, torn);
    mk("feDropShadow", { dx: 0, dy: -2, stdDeviation: 3, "flood-color": C.aub, "flood-opacity": .22 }, torn);
    const ct = mk("filter", { id: "cut", x: "-15%", y: "-15%", width: "130%", height: "140%" }, defs);      // gentler version for small cut-outs
    mk("feTurbulence", { type: "fractalNoise", baseFrequency: ".09", numOctaves: 2, seed: 5, result: "t" }, ct);
    mk("feDisplacementMap", { in: "SourceGraphic", in2: "t", scale: 2.2, result: "d" }, ct);
    mk("feDropShadow", { in: "d", dx: 1.2, dy: 2.4, stdDeviation: 1.6, "flood-color": C.aub, "flood-opacity": .3 }, ct);
    const paper = mk("filter", { id: "paper", x: 0, y: 0, width: "100%", height: "100%" }, defs);
    mk("feTurbulence", { type: "fractalNoise", baseFrequency: ".012 .02", numOctaves: 3, seed: 4 }, paper);
    mk("feColorMatrix", { values: "0 0 0 0 .62  0 0 0 0 .68  0 0 0 0 .76  0 0 0 .9 -.3" }, paper);

    mk("rect", { width: 1440, height: 720, fill: "url(#sky)" }, back);
    const sunPos = mk("g", { transform: "translate(1010 470)" }, back);
    const sun = mk("g", { class: "sun", id: "sun" }, sunPos);
    mk("circle", { r: 280, fill: "url(#glow)" }, sun); mk("circle", { r: 62, fill: C.mari, opacity: .95 }, sun);

    const cl = mk("g", { filter: "url(#wc)" }, svg);
    [[250, 330, 230, 60, C.ice3], [440, 300, 150, 48, C.ice3], [140, 350, 150, 40, C.ice2],
     [1190, 280, 230, 70, C.ice3], [1330, 330, 190, 50, C.ice2], [820, 250, 170, 40, C.ice3]]
      .forEach(([cx, cy, rx, ry, f]) => mk("ellipse", { cx, cy, rx, ry, fill: f, "fill-opacity": .85 }, cl));
    mk("rect", { width: 1440, height: 720, filter: "url(#paper)", opacity: .45 }, svg);

    floater(svg, 440, 215, -10, 1, 0, envelope); floater(svg, 1170, 190, 9, 1.15, -2.5, envelope);
    floater(svg, 800, 150, -18, 1.1, -4.5, plane); floater(svg, 150, 300, 7, .8, -1.2, plane);
    floater(svg, 640, 290, 12, .9, -3.2, heart); floater(svg, 980, 340, -8, .7, -5.5, heart);

    const hill = (d, fill, rim) => { const g = mk("g", { filter: "url(#torn)" }, svg);
      mk("path", { d, fill }, g); if (rim) mk("path", { d, fill: "none", stroke: C.ice3, "stroke-width": 2.5, transform: "translate(0 -2)" }, g); return g; };
    hill("M-20 470Q220 420 460 455T900 440T1460 450V760H-20Z", C.ice2, true);
    const trees = mk("g", { filter: "url(#torn)" }, svg);
    for (let x = 90; x < 1440; x += 70 + rnd() * 80) fir(trees, x, 452 + rnd() * 16, 60 + rnd() * 60, .5);
    hill("M-20 545Q300 490 620 528T1100 512T1460 534V760H-20Z", C.silver, true);
    postbox(svg, 330, 545, 1.5);
    hill("M-20 615Q360 568 760 602T1460 592V760H-20Z", C.aub, true);
    [[tulip, 120, 612, 70], [daisy, 178, 608, 50], [tulip, 1190, 600, 86], [daisy, 1258, 604, 58], [tulip, 1338, 598, 74]]
      .forEach(([fn, x, y, h]) => fn(svg, x, y, h));
    return { setSun(t) { sun.style.transform = `translateY(${(1 - t) * 190}px)`; sun.style.opacity = .3 + .7 * t; } };
  };
})();
