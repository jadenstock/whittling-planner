// The Learn page: the cuts and what each is for, with a diagram of each.

const $ = (id) => document.getElementById(id);
const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const levelClass = (level) => `how-${level.replace(/ /g, "-")}`;

// ---------------------------------------------------------------- diagram pieces
// Each diagram is a 240 × 150 sketch: wood with its grain, the knife, the chip, and arrows.

let uid = 0;

/** A piece of wood: path d, with grain lines running "h" (across the sketch) or "v" (up and down). */
function wood(d, grain = "h", step = 9) {
  const id = `clip${uid++}`;
  let lines = "";
  if (grain === "h") for (let y = 4; y < 150; y += step) lines += `M0,${y}H240`;
  if (grain === "v") for (let x = 4; x < 240; x += step) lines += `M${x},0V150`;
  return `<clipPath id="${id}"><path d="${d}"/></clipPath>
    <path class="wood" d="${d}"/>
    ${lines ? `<path class="grain" d="${lines}" clip-path="url(#${id})"/>` : ""}
    <path class="wood-edge" d="${d}"/>`;
}

const arrow = (d, bad = false) => `<path class="${bad ? "bad" : "move"}" d="${d}"/>`;
const label = (x, y, text, cls = "lbl", anchor = "start") =>
  `<text class="${cls}" x="${x}" y="${y}" text-anchor="${anchor}">${text}</text>`;
const num = (x, y, n) => `<circle class="num-bg" cx="${x}" cy="${y}" r="7"/>${label(x, y + 3.5, n, "num", "middle")}`;

/** A blade seen end on: a thin wedge from its edge back to its spine. */
const wedge = (edge, back, spine) => `<path class="blade" d="M${edge}L${back}L${spine}Z"/>`;

/** A carving knife seen from the side, tip at (0, 0) pointing along +x, edge facing +y. */
const knife = (transform, faded = false) => `<g transform="${transform}" ${faded ? 'class="faded"' : ""}>
    <rect class="handle" x="-118" y="-13" width="58" height="17" rx="8"/>
    <path class="blade" d="M-62,-9L-20,-9L0,3L-62,3Z"/>
    <path class="edge" d="M-62,3L0,3"/>
  </g>`;

const thumb = (cx, cy, rx, ry, rot = 0) => `<g transform="rotate(${rot} ${cx} ${cy})">
    <ellipse class="thumb" cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}"/>
    <ellipse class="nail" cx="${cx - rx * 0.45}" cy="${cy - ry * 0.15}" rx="${rx * 0.35}" ry="${ry * 0.5}"/>
  </g>`;

const shaving = (d) => `<path class="shaving-edge" d="${d}"/><path class="shaving" d="${d}"/>`;

const svg = (body, title) =>
  `<svg viewBox="0 0 240 150" role="img" aria-label="${escapeHtml(title)}" class="sketch">${body}</svg>`;

const DIAGRAMS = {
  straightaway: () => svg(`
    ${wood("M14,70H40Q50,78 60,78H150V70H226V128H14Z")}
    ${wedge("152,78", "102,69", "101,61")}
    ${shaving("M148,72L112,62C92,56 78,50 72,40C66,30 74,22 82,26C88,30 86,37 80,37")}
    ${arrow("M130,44H206")}
    ${label(168, 36, "away from you", "lbl", "middle")}
    ${label(40, 18, "shaving")}
  `, "Straightaway cut: the blade lifts a shaving as it moves away from you"),

  pull: () => svg(`
    ${wood("M14,70H88V78H178Q190,78 200,70H226V128H14Z")}
    ${wedge("86,78", "136,69", "137,61")}
    ${shaving("M90,72L126,62C146,56 160,50 166,40C172,30 164,22 156,26C150,30 152,37 158,37")}
    ${thumb(38, 62, 22, 10)}
    <path class="pencil" d="M70,60V88"/>
    ${arrow("M118,40H66")}
    ${label(92, 30, "toward your thumb", "lbl", "middle")}
    ${label(70, 100, "the cut ends here,", "lbl", "middle")}
    ${label(70, 112, "short of your thumb", "lbl", "middle")}
  `, "Pull cut: the blade moves toward your thumb, which rests past the end of the cut"),

  push: () => svg(`
    ${wood("M14,70H110Q116,76 122,76H150V70H226V128H14Z")}
    ${wedge("152,76", "104,68", "103,60")}
    ${shaving("M148,71L118,62C108,58 104,52 106,46C108,40 115,42 114,47")}
    ${thumb(84, 60, 16, 9, -15)}
    ${arrow("M42,52L66,56")}
    ${arrow("M156,46H184")}
    ${label(20, 22, "the other thumb")}
    ${label(20, 34, "pushes the blade")}
    ${label(170, 36, "a short stroke", "lbl", "middle")}
  `, "Thumb push cut: the thumb of the other hand pushes on the back of the blade"),

  stop: () => svg(`
    ${wood("M14,60H70L130,96V60H226V128H14Z")}
    <path class="chip" d="M70,60L130,60L130,96Z"/>
    <path class="cutline" d="M130,52V98"/>
    ${arrow("M58,50L118,88")}
    ${num(140, 46, "1")}
    ${label(152, 43, "straight in,")}
    ${label(152, 55, "on the line")}
    ${num(30, 34, "2")}
    ${label(42, 37, "slice toward it")}
    ${label(104, 116, "the chip pops out", "lbl", "middle")}
  `, "Stop cut: cut straight in on the line, then slice toward it so the chip pops out"),

  vcut: () => svg(`
    ${wood("M14,60H90L120,100L150,60H226V128H14Z")}
    <path class="chip" d="M90,60H150L120,100Z"/>
    ${arrow("M74,46L112,96")}
    ${arrow("M166,46L128,96")}
    ${num(66, 38, "1")}
    ${num(174, 38, "2")}
    ${label(120, 22, "two cuts at about 45°", "lbl", "middle")}
    ${label(120, 120, "they meet at the bottom", "lbl", "middle")}
  `, "V-cut: two angled cuts that meet at the bottom, lifting a V-shaped chip"),

  scoop: () => svg(`
    ${wood("M14,60H60C80,60 92,104 120,104C148,104 160,60 180,60H226V128H14Z")}
    ${arrow("M54,50C76,52 90,92 112,95")}
    ${arrow("M186,50C164,52 150,92 128,95")}
    ${arrow("M126,114C150,114 162,90 174,74", true)}
    ${label(120, 26, "from both rims", "lbl", "middle")}
    ${label(120, 38, "down to the bottom", "lbl", "middle")}
    ${label(232, 104, "on up: tears", "lbl bad-text", "end")}
  `, "Scoop cut: from each rim down to the bottom of the hollow; carrying on up the far side tears the wood"),

  lever: () => svg(`
    ${wood("M14,104H96C104,104 104,70 118,70C132,70 132,104 140,104H226V150H14Z")}
    ${knife("translate(176 116) rotate(-140) scale(1 -1) translate(62 0)", true)}
    ${knife("translate(176 116) rotate(-165) scale(1 -1) translate(62 0)")}
    ${thumb(176, 116, 12, 9, -30)}
    ${arrow("M124,69A70,70 0 0 0 107.5,101.4")}
    ${label(14, 22, "thumb braced on the wood;")}
    ${label(14, 34, "swing the blade around it")}
  `, "Lever cut: the knife pivots around the thumb braced on the wood"),

  chip: () => svg(`
    ${wood("M14,14H226V136H14Z")}
    <path class="pit-1" d="M80,28L38,110L80,83Z"/>
    <path class="pit-2" d="M38,110L122,110L80,83Z"/>
    <path class="pit-3" d="M122,110L80,28L80,83Z"/>
    <path class="cutline thin" d="M80,83L80,28M80,83L38,110M80,83L122,110"/>
    <path class="outline-tri" d="M80,28L38,110L122,110Z"/>
    ${num(138, 44, "1")}
    ${label(148, 41, "tip in, middle")}
    ${label(148, 53, "to each corner")}
    ${num(138, 104, "2")}
    ${label(148, 101, "slice each side")}
    ${label(148, 113, "toward the middle")}
  `, "Triangle chip seen from above: press in from the middle to each corner, then slice each side"),

  facet: () => svg(`
    <path class="pencil" d="M56,22H150V116H56Z"/>
    <path class="chip" d="M56,22H80L56,46ZM126,22H150V46ZM150,92V116H126ZM80,116H56V92Z"/>
    ${wood("M80,22H126L150,46V92L126,116H80L56,92V46Z")}
    ${arrow("M132,14L158,40")}
    ${label(166, 30, "one flat cut")}
    ${label(166, 42, "per facet")}
    ${label(14, 138, "Left as the knife left it, not rounded")}
  `, "Flat-plane cut: each corner becomes one flat facet instead of a curve"),

  saw: () => svg(`
    ${wood("M14,30H226V128H14Z")}
    <path class="pencil" d="M14,92C40,74 60,62 80,64C98,66 100,44 120,40C140,36 150,54 152,68C172,72 200,74 226,82"/>
    <path class="cutline" d="M36,30V72M56,30V60M174,30V65M196,30V68M216,30V72"/>
    ${label(120, 22, "waste", "lbl", "middle")}
    ${arrow("M92,112L58,64")}
    ${label(96, 114, "stop short of the line")}
  `, "Saw cuts: several cuts into the waste, each stopping short of the pencil line"),

  // ---- the topics
  downhill: () => svg(`
    ${wood("M14,140V112C60,112 80,56 120,56C160,56 180,112 226,112V140Z")}
    ${arrow("M108,46C86,48 70,76 42,98")}
    ${arrow("M200,100C176,80 156,50 134,46", true)}
    <path class="tear" d="M166,84l7,-9M174,92l7,-9M158,76l6,-9"/>
    ${label(14, 30, "downhill: clean", "lbl ok-text")}
    ${label(226, 22, "uphill: digs in", "lbl bad-text", "end")}
    ${label(226, 34, "and tears", "lbl bad-text", "end")}
  `, "Cut downhill: from the high point toward the low point. Cutting uphill digs in and tears"),

  shortgrain: () => svg(`
    ${wood("M20,94H50V34C50,20 80,20 80,34V94H110V120H20Z", "v", 7)}
    ${wood("M130,94H160V34C160,20 190,20 190,34V94H220V120H130Z", "h", 7)}
    <path class="crack" d="M158,88l6,-2l6,3l6,-2l6,2l6,-2l4,1"/>
    ${label(65, 135, "grain along it:", "lbl ok-text", "middle")}
    ${label(65, 147, "strong", "lbl ok-text", "middle")}
    ${label(175, 135, "grain across it:", "lbl bad-text", "middle")}
    ${label(175, 147, "snaps", "lbl bad-text", "middle")}
  `, "Short grain: a part with the grain along it is strong; with the grain across it, it snaps"),

  endgrain: () => {
    let side = "";
    for (let y = 68; y < 120; y += 8) side += `M30,${y}H170`;
    let top = "";
    for (let t = 0.2; t < 1; t += 0.25) top += `M${30 + t * 30},${60 - t * 24}H${170 + t * 30}`;
    const id = `clip${uid++}`;
    let rings = "";
    for (let r = 20; r < 120; r += 9) rings += `<circle cx="214" cy="128" r="${r}"/>`;
    return svg(`
      <path class="wood" d="M30,60H170V120H30Z"/>
      <path class="grain" d="${side}"/>
      <path class="wood top" d="M30,60L60,36H200L170,60Z"/>
      <path class="grain" d="${top}"/>
      <clipPath id="${id}"><path d="M170,60L200,36V96L170,120Z"/></clipPath>
      <path class="wood end" d="M170,60L200,36V96L170,120Z"/>
      <g class="rings" clip-path="url(#${id})">${rings}</g>
      <path class="wood-edge" d="M30,60H170V120H30ZM30,60L60,36H200L170,60M170,120L200,96V36"/>
      ${label(92, 140, "side grain: slices clean", "lbl", "middle")}
      ${label(232, 134, "end grain:", "lbl", "end")}
      ${label(232, 146, "the fiber ends", "lbl", "end")}
    `, "End grain is the cut ends of the fibers; side grain is along them");
  },

  slice: () => svg(`
    ${wood("M14,70H226V110H14Z")}
    ${knife("translate(96,56) rotate(-90) scale(0.75)")}
    ${arrow("M104,74H146")}
    ${arrow("M104,74L140,108")}
    ${label(152, 78, "push")}
    ${label(146, 122, "slice: push while")}
    ${label(146, 134, "drawing it along")}
    ${label(14, 22, "seen from above")}
  `, "Slicing: the blade moves forward and along its length at the same time"),

  strop: () => svg(`
    <rect class="board" x="14" y="78" width="212" height="22" rx="3"/>
    <rect class="leather" x="14" y="70" width="212" height="9" rx="2"/>
    ${wedge("72,70", "126,70", "125,62")}
    ${arrow("M134,52H200")}
    ${arrow("M62,52H20", true)}
    ${label(166, 44, "spine first", "lbl ok-text", "middle")}
    ${label(42, 44, "never edge first", "lbl bad-text", "middle")}
    ${label(120, 120, "bevel flat on the leather", "lbl", "middle")}
  `, "Stropping: pull the knife spine first, with the bevel flat on the leather"),
};

// ---------------------------------------------------------------- the page

const data = await (await fetch("/api/learn")).json();
const cutLink = (c) => `<a href="#${c.key}">${escapeHtml(c.name)}</a>`;

$("uses-table").innerHTML = `<thead><tr><th>I want to…</th><th>Use</th></tr></thead><tbody>${data.uses
  .map((u) => `<tr><td>${escapeHtml(u.want)}</td><td>${u.cuts.map(cutLink).join(", ")}</td></tr>`)
  .join("")}</tbody>`;

const PRACTICE_SHOWN = 4;

function practice(c) {
  if (!c.designs.length) return `<p class="practice">Every design, in the outline and rounding steps.</p>`;
  const shown = c.designs.slice(0, PRACTICE_SHOWN);
  const more = c.designs.length - shown.length;
  return `<ul class="practice">${shown
    .map((d) => `<li><a href="/?design=${d.key}">${escapeHtml(d.name)}</a> <span class="where">${escapeHtml(d.where)}</span></li>`)
    .join("")}${more ? `<li class="more">and ${more} more</li>` : ""}</ul>`;
}

$("cut-grid").innerHTML = data.cuts
  .map(
    (c) => `<article class="cut-card" id="${c.key}">
      <figure class="cut-fig">${DIAGRAMS[c.key]()}</figure>
      <div class="cut-text">
        <header><h3>${escapeHtml(c.name)}</h3><span class="chip ${levelClass(c.level)}">${c.level}</span></header>
        <p class="aka">Also called ${escapeHtml(c.aka)}</p>
        <p class="good">${escapeHtml(c.good_for)}</p>
        <h4>How</h4>
        <ol>${c.how.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ol>
        <h4>Watch out</h4>
        <ul>${c.watch.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>
        <h4>Practice it on</h4>
        ${practice(c)}
      </div>
    </article>`,
  )
  .join("");

document.querySelectorAll("[data-diagram]").forEach((fig) => (fig.innerHTML = DIAGRAMS[fig.dataset.diagram]()));

$("path-list").innerHTML = data.path
  .map(
    (p) => `<li>
      <div class="path-head">
        <a href="/?design=${p.key}">${escapeHtml(p.name)}</a>
        <span class="chip level-${p.level}">${p.level}</span>
      </div>
      <p>${escapeHtml(p.why)}</p>
      <div class="chips">${p.cuts
        .map((c) => `<a class="chip cut${c.new ? " new" : ""}" href="#${c.key}">${escapeHtml(c.name)}${c.new ? " · new" : ""}</a>`)
        .join("")}</div>
    </li>`,
  )
  .join("");

// the content arrived after the browser looked for the #anchor, so go there now
function showTarget() {
  const el = location.hash && document.getElementById(location.hash.slice(1));
  if (!el) return;
  el.scrollIntoView({ block: "start" });
  el.classList.remove("flash");
  void el.offsetWidth; // restart the highlight
  el.classList.add("flash");
}
window.addEventListener("hashchange", showTarget);
showTarget();
