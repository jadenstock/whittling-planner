import * as THREE from "three";
import {
  $, blockEdges, blockLabel, createViewer, decode, escapeHtml, meshGeometry, paint, smoothstep, woodMaterial,
} from "./common.js";

const state = {
  blocks: {},
  designs: [],
  block: "2x1x1", // a stock block, or "custom"
  customIn: [3, 1.5, 1.5],
  design: null,
  angle: "auto", // "auto": turn the figure in the block when that makes it much bigger; "straight": never
  grain: null, // null = the block's grain, the safest way
  plan: null,
  geoms: [],
  stage: 0,
  mode: "cut", // "cut": the shape before this step, colored by how much to remove; "result": after it
  showWeak: false,
  showLines: true,
};

const AXIS_NAMES = { x: "Front to back", y: "Side to side", z: "Up and down" };

// ---------------------------------------------------------------- data

let loadToken = 0;

async function loadPlan() {
  const params = new URLSearchParams({ design: state.design, angle: state.angle });
  if (state.block === "custom") params.set("blank_in", state.customIn.join(","));
  else params.set("block", state.block);
  if (state.grain) params.set("grain", state.grain);
  syncUrl();

  const token = ++loadToken;
  const spinner = setTimeout(() => ($("loading").hidden = false), 150);
  try {
    const res = await fetch(`/api/plan?${params}`);
    const body = await res.json();
    if (token !== loadToken) return;
    if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Couldn't make a plan.");
    usePlan(body);
  } catch (err) {
    if (token !== loadToken) return;
    $("detail").innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  } finally {
    if (token === loadToken) {
      clearTimeout(spinner);
      $("loading").hidden = true;
    }
  }
}

function syncUrl() {
  const q = new URLSearchParams({ design: state.design });
  if (state.block === "custom") q.set("blank", state.customIn.join("x"));
  else q.set("block", state.block);
  history.replaceState(null, "", `/?${q}`);
  $("explore-link").href = state.block === "custom" ? "/explore" : `/explore?block=${state.block}`;
}

function usePlan(plan) {
  const refit = state.plan?.design.key !== plan.design.key || state.plan?.blank_mm.join() !== plan.blank_mm.join();
  new Set(state.geoms).forEach((g) => g?.dispose());
  state.geoms = plan.stages.map((s) => (s.mesh ? meshGeometry(s.mesh.positions, s.mesh.indices) : null));
  plan.stages.forEach((s, i) => {
    if (s.same_as != null) state.geoms[i] = state.geoms[s.same_as];
    if (s.heat) s.heatValues = decode(s.heat, Float32Array);
    if (s.lines) s.lineValues = decode(s.lines, Float32Array);
  });
  plan.weak = Object.fromEntries(Object.entries(plan.grain.fragile).map(([a, b]) => [a, decode(b, Float32Array)]));
  state.plan = plan;
  state.stage = Math.min(state.stage, plan.stages.length - 1);
  setScene(plan.blank_mm, refit);
  render();
}

// ---------------------------------------------------------------- 3D

const viewer = createViewer($("viewer"));
const { scene } = viewer;

const solid = new THREE.Mesh(new THREE.BufferGeometry(), woodMaterial());
const ghost = new THREE.Mesh(
  new THREE.BufferGeometry(),
  new THREE.MeshStandardMaterial({ color: 0xd9c3a0, transparent: true, opacity: 0.28, depthWrite: false }),
);
ghost.renderOrder = 1;
const pencil = new THREE.LineSegments(
  new THREE.BufferGeometry(),
  new THREE.LineBasicMaterial({ color: 0x3b332b, transparent: true, opacity: 0.85 }),
);
const spots = new THREE.Group();
const frame = new THREE.Group(); // block outline, ground, labels
scene.add(solid, ghost, pencil, spots, frame);

function setScene(blank, refit) {
  const [L, W, H] = blank;
  frame.clear();
  frame.add(blockEdges(blank));
  const span = Math.max(L, W) * 2.2;
  const grid = new THREE.GridHelper(span, Math.max(4, Math.round(span / 10)), 0x9c8c78, 0xc9bca8);
  grid.rotation.x = Math.PI / 2;
  grid.position.set(L / 2, W / 2, -0.05);
  grid.material.transparent = true;
  grid.material.opacity = 0.35;
  frame.add(grid);
  const label = textSprite("FRONT →");
  const s = Math.max(L, W, H) * 0.2;
  label.position.set(L + s * 0.9, W / 2, 0);
  label.scale.set(s * 1.4, s * 0.47, 1);
  frame.add(label);

  spots.clear();
  const final = state.plan.stages.find((st) => st.spots);
  const r = Math.max(L, W, H) * 0.012;
  for (const p of final?.spots ?? []) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), new THREE.MeshStandardMaterial({ color: 0x2a1d12 }));
    dot.position.set(...p);
    spots.add(dot);
  }
  if (refit) viewer.frame(blank, "iso", true);
}

function textSprite(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 192;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.font = "600 34px system-ui, sans-serif";
  ctx.fillStyle = "#8a7a66";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 96, 32);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
}

/** The line on a mesh where a per-vertex value crosses `level`, nudged out along the normals. */
function contour(geom, values, level, lift) {
  const pos = geom.attributes.position.array;
  const nrm = geom.attributes.normal.array;
  const idx = geom.index.array;
  const out = [];
  const pts = [];
  const edge = (i, j) => {
    const vi = values[i] - level;
    const vj = values[j] - level;
    if (vi < 0 === vj < 0) return;
    const t = vi / (vi - vj);
    for (let k = 0; k < 3; k++) {
      const p = pos[3 * i + k] + (pos[3 * j + k] - pos[3 * i + k]) * t;
      const n = nrm[3 * i + k] + (nrm[3 * j + k] - nrm[3 * i + k]) * t;
      pts.push(p + n * lift);
    }
  };
  for (let f = 0; f < idx.length; f += 3) {
    pts.length = 0;
    edge(idx[f], idx[f + 1]);
    edge(idx[f + 1], idx[f + 2]);
    edge(idx[f + 2], idx[f]);
    if (pts.length === 6) out.push(...pts);
  }
  return new Float32Array(out);
}

// ---------------------------------------------------------------- color

const srgb = (hex) => new THREE.Color(hex);
const HEAT = [srgb(0xf6d55c), srgb(0xed8a3a), srgb(0xc8342b)];
const WEAK = srgb(0xc2185b);
const MIN_HEAT_SCALE = 3; // mm: so a step of tiny cuts doesn't look all red
const CUT_LINE_MM = 0.3; // where the pencil line goes: the edge of the wood to remove

const tmp2 = new THREE.Color();

function heatColor(t, out) {
  return t < 0.5 ? out.copy(HEAT[0]).lerp(HEAT[1], t * 2) : out.copy(HEAT[1]).lerp(HEAT[2], (t - 0.5) * 2);
}

function paintWood(geom, overlay) {
  paint(geom, "xyz".indexOf(state.plan.grain.selected), state.plan.blank_mm, overlay);
}

// ---------------------------------------------------------------- render

function render() {
  renderStageList();
  renderDetail();
  renderBlankCard();
  renderGrainCard();
  renderView();
}

function renderView() {
  const { plan, geoms, stage, mode } = state;
  if (!plan) return;
  const s = plan.stages[stage];
  const legend = $("legend");
  const finishing = s.key === "finish";
  let show;
  let before = null;
  let lines = null;

  if (state.showWeak) {
    show = geoms[geoms.length - 1];
    const weak = plan.weak[plan.grain.selected];
    paintWood(show, (i, c) => c.lerp(WEAK, smoothstep(0.15, 0.6, weak[i])));
    const n = plan.grain.weak_parts[plan.grain.selected];
    legend.innerHTML = `<span class="swatch" style="background:var(--weak)"></span>
      ${n ? "Weak spots: short grain, likely to snap" : "No weak spots with this grain direction"}`;
  } else if (stage === 0) {
    show = geoms[0];
    paintWood(show);
    lines = s.lineValues;
    legend.innerHTML = `<span class="swatch line"></span><span>Pencil lines to draw on the block</span>`;
  } else if (finishing) {
    show = geoms[stage];
    paintWood(show);
    legend.innerHTML = plan.stages[stage].spots
      ? `<span class="swatch dot"></span><span>Where to mark the ${escapeHtml(featureWord(plan))}</span>`
      : "";
  } else if (mode === "cut") {
    show = geoms[stage - 1];
    const heat = s.heatValues;
    const max = Math.max(s.heat_max, MIN_HEAT_SCALE);
    paintWood(show, (i, c) => {
      const d = heat[i];
      if (d < 0.25) return; // below the grid's precision
      c.lerp(heatColor(Math.min(d / max, 1), tmp2), smoothstep(0.25, 0.8, d) * 0.92);
    });
    s.cutLine ??= contour(show, heat, CUT_LINE_MM, plan.cell_mm * 0.3);
    lines = s.cutLine;
    legend.innerHTML = `<span>Remove</span><span>0</span><span class="bar"></span><span>${max.toFixed(max < 10 ? 1 : 0)} mm</span>`;
  } else {
    show = geoms[stage];
    before = geoms[stage - 1];
    paintWood(show);
    legend.innerHTML = `<span class="swatch" style="background:#d9c3a0;opacity:.6"></span><span>Faint shape: before this step</span>`;
  }

  solid.geometry = show;
  ghost.geometry = before ?? new THREE.BufferGeometry();
  ghost.visible = !!before;
  pencil.geometry.dispose();
  pencil.geometry = new THREE.BufferGeometry();
  if (lines?.length) pencil.geometry.setAttribute("position", new THREE.BufferAttribute(lines, 3));
  pencil.visible = state.showLines && !!lines?.length;
  spots.visible = finishing && !state.showWeak;
  $("show-lines").closest("label").hidden = !lines?.length;
  document.querySelectorAll("#mode button").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
    b.disabled = stage === 0 || finishing || state.showWeak;
  });
}

function featureWord(plan) {
  const s = plan.stages.find((st) => st.key === "finish");
  const step = s.steps.find((t) => t.startsWith("Mark the "));
  return step ? step.slice(9, step.indexOf(":")) : "features";
}

function renderStageList() {
  const { plan, stage } = state;
  $("stages").innerHTML = plan.stages
    .map(
      (s, i) => `<li><button data-stage="${i}" ${i === stage && !state.showWeak ? 'aria-current="step"' : ""}>
        <span class="num">${i + 1}</span>
        <span class="title">${escapeHtml(s.title)}</span>
        <span class="pct">${s.removed_pct == null ? "" : s.removed_pct < 1 ? "<1%" : `−${pct(s.removed_pct)}`}</span>
      </button></li>`,
    )
    .join("");
}

function renderDetail() {
  const { plan, stage } = state;
  const s = plan.stages[stage];
  const isFirst = stage === 0;
  const isLast = stage === plan.stages.length - 1;
  $("detail").innerHTML = `
    <p class="card-label">Step ${stage + 1} of ${plan.stages.length}</p>
    <h2>${escapeHtml(s.title)}</h2>
    <p class="summary">${escapeHtml(s.summary)}</p>
    <ol>${s.steps.map((t) => `<li>${linkTerms(escapeHtml(t))}</li>`).join("")}</ol>
    ${s.cuts.length ? `<section class="step-cuts">
        <p class="card-label">Cuts for this step</p>
        <ul>${s.cuts.map((c) => `<li>
          <a href="/learn#${c.key}" target="learn">${escapeHtml(c.name)}</a>
          <span class="where">${escapeHtml(c.where || c.good_for)}</span>
        </li>`).join("")}</ul>
      </section>` : ""}
    ${s.removed_cm3 != null ? `<div class="stats">
        <span>Wood removed <b>${s.removed_cm3.toFixed(1)} cm³</b> (${pct(s.removed_pct)} of the block)</span>
        <span>Deepest cut <b>${inchesFromMm(s.heat_max)}</b> (${s.heat_max.toFixed(1)} mm)</span>
      </div>` : ""}
    ${s.marks.map(marksHtml).join("")}
    <div class="nav">
      <button class="btn" data-go="-1" ${isFirst ? "disabled" : ""}>← Previous</button>
      <button class="btn primary" data-go="1" ${isLast ? "disabled" : ""}>Next step →</button>
    </div>`;
}

function marksHtml(m) {
  return `<section class="marks">
    <h3>${escapeHtml(m.title)}</h3>
    <p class="where">${escapeHtml(m.where)}</p>
    <div class="marks-body">
      <figure class="diagram">${m.svg}</figure>
      <div class="marks-tables">
        <table class="stations">
          <thead><tr><th>${escapeHtml(m.station_head)}</th><th>${escapeHtml(m.across_head)}</th></tr></thead>
          <tbody>${m.rows.map((r, i) => `<tr data-row="${i}"><td>${escapeHtml(r.at)}</td><td>${escapeHtml(r.marks)}</td></tr>`).join("")}</tbody>
        </table>
        ${m.tips.length ? `<p class="tips-head">Points between the lines</p>
          <ul class="tips">${m.tips.map((t) => `<li data-tip="${t.label}"><b>${t.label}</b> ${escapeHtml(t.text)}</li>`).join("")}</ul>` : ""}
        <p class="hint">Inches, to the nearest 1/16. Hover a row to find its line in the drawing.</p>
      </div>
    </div>
  </section>`;
}

function renderBlankCard() {
  const { plan } = state;
  const p = plan.placement;
  const turned = p.yaw !== 0;
  const angleChoice = p.angle_gain_pct > 0
    ? `<div class="segmented small angle" role="radiogroup" aria-label="Placement">
        <button data-angle="straight" aria-pressed="${!turned}">Square on</button>
        <button data-angle="auto" aria-pressed="${turned}">Turned ${Math.abs(p.angle_yaw).toFixed(0)}°, ${p.angle_gain_pct.toFixed(0)}% bigger</button>
      </div>`
    : "";
  $("blank-card").innerHTML = `
    <p class="card-label">Your block</p>
    <p class="big">${plan.block_label} basswood</p>
    <p class="sub">${escapeHtml(p.set_down)}</p>
    <p class="sub">Finished ${escapeHtml(plan.design.name.toLowerCase())}: <b>${plan.figure_label}</b>, using ${p.fill_pct.toFixed(0)}% of the wood.</p>
    ${angleChoice}`;
}

function renderGrainCard() {
  const g = state.plan.grain;
  const blockAxes = g.block_axes.split("");
  const offBlock = !blockAxes.includes(g.selected);
  $("grain-card").innerHTML = `
    <p class="card-label">Grain direction</p>
    <p class="sub">Wood splits along the grain, so thin parts with the grain running across them snap easily.
      Blocks are sold with the grain along their longest side.</p>
    <div class="grain-options">${"xyz"
      .split("")
      .map((a) => {
        const n = g.weak_parts[a];
        const tags = [
          blockAxes.includes(a) ? '<span class="tag">Your block</span>' : "",
          a === g.recommended ? '<span class="tag soft">Strongest</span>' : "",
        ].join("");
        return `<label>
          <input type="radio" name="grain" value="${a}" ${a === g.selected ? "checked" : ""}>
          <span>${AXIS_NAMES[a]}${tags}</span>
          <span class="verdict ${n ? "bad" : ""}">${n ? `${n} weak spot${n > 1 ? "s" : ""}` : "No weak spots"}</span>
        </label>`;
      })
      .join("")}</div>
    ${offBlock ? `<p class="sub warn">A stock block's grain won't run this way: you'd need a block cut across the grain.</p>` : ""}
    <label class="check"><input type="checkbox" id="show-weak" ${state.showWeak ? "checked" : ""}> Show weak spots on the model</label>`;
}

// ---------------------------------------------------------------- pickers

function renderBlockPicker() {
  const names = Object.keys(state.blocks);
  $("block-picker").innerHTML =
    names
      .map((n) => `<button data-block="${n}" aria-pressed="${n === state.block}">${blockLabel(n)}</button>`)
      .join("") + `<button data-block="custom" aria-pressed="${state.block === "custom"}">Other</button>`;
  $("custom-block").hidden = state.block !== "custom";
}

function renderDesignSelect() {
  const option = (d) =>
    `<option value="${d.key}" ${d.key === state.design ? "selected" : ""}>${escapeHtml(d.name)} (${d.level.toLowerCase()})</option>`;
  if (state.block === "custom") {
    $("design-select").innerHTML = state.designs.map(option).join("");
    return;
  }
  const made = state.designs.filter((d) => d.fits[state.block].made_for);
  const other = state.designs
    .filter((d) => !d.fits[state.block].made_for)
    .sort((a, b) => b.fits[state.block].fill_pct - a.fits[state.block].fill_pct);
  $("design-select").innerHTML = `
    <optgroup label="Made for a ${blockLabel(state.block)} block">${made.map(option).join("")}</optgroup>
    <optgroup label="Also fits, smaller">${other.map(option).join("")}</optgroup>`;
}

function madeFor(block) {
  return state.designs.filter((d) => block === "custom" || d.fits[block].made_for);
}

// ---------------------------------------------------------------- events

function goTo(i) {
  const n = state.plan.stages.length;
  state.stage = Math.max(0, Math.min(n - 1, i));
  state.showWeak = false;
  render();
}

$("stages").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-stage]");
  if (b) goTo(Number(b.dataset.stage));
});

$("detail").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-go]");
  if (b) goTo(state.stage + Number(b.dataset.go));
});

// hovering a table row lights up its station line in the drawing, and the other way round
function highlight(section, attr, value) {
  section.querySelectorAll(".hl").forEach((el) => el.classList.remove("hl"));
  if (value == null) return;
  section.querySelectorAll(`[${attr}="${value}"]`).forEach((el) => el.classList.add("hl"));
}

$("detail").addEventListener("mouseover", (e) => {
  const section = e.target.closest(".marks");
  if (!section) return;
  const row = e.target.closest("[data-row]");
  const tip = e.target.closest("[data-tip]");
  if (row) highlight(section, "data-row", row.dataset.row);
  else if (tip) highlight(section, "data-tip", tip.dataset.tip);
  else highlight(section, null, null);
});

$("blank-card").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-angle]");
  if (!b || b.dataset.angle === state.angle) return;
  state.angle = b.dataset.angle;
  loadPlan();
});

$("mode").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-mode]");
  if (!b) return;
  state.mode = b.dataset.mode;
  renderView();
});

$("cams").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-cam]");
  if (b) viewer.look(b.dataset.cam);
});

$("show-lines").addEventListener("change", (e) => {
  state.showLines = e.target.checked;
  renderView();
});

$("grain-card").addEventListener("change", (e) => {
  if (e.target.name === "grain") {
    state.grain = e.target.value;
    loadPlan();
  } else if (e.target.id === "show-weak") {
    state.showWeak = e.target.checked;
    render();
  }
});

$("block-picker").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-block]");
  if (!b || b.dataset.block === state.block) return;
  state.block = b.dataset.block;
  // keep the design if it was made for this block; otherwise pick one that was
  const choices = madeFor(state.block);
  if (!choices.some((d) => d.key === state.design)) state.design = choices[0].key;
  state.grain = null;
  state.angle = "auto";
  renderBlockPicker();
  renderDesignSelect();
  loadPlan();
});

$("design-select").addEventListener("change", (e) => {
  state.design = e.target.value;
  state.grain = null;
  state.angle = "auto";
  state.showWeak = false;
  loadPlan();
});

let debounce;
["blank-l", "blank-w", "blank-h"].forEach((id) =>
  $(id).addEventListener("input", () => {
    const dims = ["blank-l", "blank-w", "blank-h"].map((i) => parseFloat($(i).value));
    if (!dims.every((v) => v >= 0.5 && v <= 24)) return;
    state.customIn = dims;
    clearTimeout(debounce);
    debounce = setTimeout(loadPlan, 450);
  }),
);

document.addEventListener("keydown", (e) => {
  if (!state.plan || e.target.closest("input, textarea, select")) return;
  if (e.key === "ArrowRight") goTo(state.stage + 1);
  if (e.key === "ArrowLeft") goTo(state.stage - 1);
});

const pct = (v) => (v < 1 ? "<1%" : `${v.toFixed(0)}%`);

function inchesFromMm(mm) {
  const sixteenths = Math.round((mm / 25.4) * 16);
  if (sixteenths === 0) return "under 1/32 in";
  const whole = Math.floor(sixteenths / 16);
  let num = sixteenths % 16;
  let den = 16;
  while (num && num % 2 === 0) {
    num /= 2;
    den /= 2;
  }
  return `${whole ? whole : ""}${whole && num ? " " : ""}${num ? `${num}/${den}` : ""} in`;
}

// ---------------------------------------------------------------- links to the Learn page

let linkTerms = (html) => html;

/** Turn the names of cuts and grain ideas in escaped step text into links to the Learn page. */
function makeLinker(terms) {
  const re = new RegExp(terms.map((t) => `(${t.pattern})`).join("|"), "gi");
  return (html) =>
    html.replace(re, (match, ...groups) => {
      const i = groups.findIndex((g, k) => k < terms.length && g !== undefined);
      return `<a href="/learn#${terms[i].anchor}" target="learn">${match}</a>`;
    });
}

// ---------------------------------------------------------------- start

const [catalog, learn] = await Promise.all(["/api/designs", "/api/learn"].map((u) => fetch(u).then((r) => r.json())));
linkTerms = makeLinker(learn.terms);
state.blocks = catalog.blocks;
state.designs = catalog.designs;

const url = new URLSearchParams(location.search);
const blank = url.get("blank")?.split("x").map(Number);
if (blank?.length === 3 && blank.every((v) => v >= 0.5 && v <= 24)) {
  state.block = "custom";
  state.customIn = blank;
  ["blank-l", "blank-w", "blank-h"].forEach((id, i) => ($(id).value = blank[i]));
} else if (url.get("block") in state.blocks) {
  state.block = url.get("block");
}
const asked = state.designs.find((d) => d.key === url.get("design"));
state.design = asked ? asked.key : madeFor(state.block)[0].key;

renderBlockPicker();
renderDesignSelect();
loadPlan();
