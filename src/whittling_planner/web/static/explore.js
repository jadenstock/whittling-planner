import * as THREE from "three";
import { $, blockEdges, blockLabel, createViewer, escapeHtml, meshGeometry, paint, woodMaterial } from "./common.js";

const url = new URLSearchParams(location.search);
const state = {
  blocks: {},
  designs: [],
  block: "all",
  style: "all",
  level: "all",
  thumbs: {}, // design key → image data URL
  previews: {}, // design key → promise of { geom, lo, hi, grain }
  open: null, // the design shown in the drawer
  openBlock: null,
};

const catalog = await (await fetch("/api/designs")).json();
state.blocks = catalog.blocks;
state.designs = catalog.designs;
if (url.get("block") in state.blocks) state.block = url.get("block");

// ---------------------------------------------------------------- filters and gallery

function segmented(id, options, value) {
  $(id).innerHTML = options
    .map(([v, label]) => `<button data-value="${v}" aria-pressed="${v === value}">${escapeHtml(label)}</button>`)
    .join("");
}

function renderFilters() {
  segmented("f-block", [["all", "All"], ...Object.keys(state.blocks).map((b) => [b, blockLabel(b)])], state.block);
  segmented("f-style", [["all", "All"], ["Classic", "Classic"], ["Rustic", "Rustic"]], state.style);
  segmented("f-level", [["all", "All"], ["Beginner", "Beginner"], ["Easy", "Easy"], ["Intermediate", "Intermediate"]], state.level);
}

function card(d) {
  const fit = state.block === "all" ? null : d.fits[state.block];
  const madeFor = d.blocks.map(blockLabel).join(" · ");
  const sub = d.subject.toLowerCase() === d.name.toLowerCase() ? "" : `${d.subject} · `;
  return `<button class="design-card" data-key="${d.key}">
    <img class="thumb" data-thumb="${d.key}" alt="${escapeHtml(d.name)}" ${state.thumbs[d.key] ? `src="${state.thumbs[d.key]}"` : ""}>
    <span class="body">
      <span class="name">${escapeHtml(d.name)}</span>
      <span class="chips">
        <span class="chip level-${d.level}">${d.level}</span>
        ${d.style === "Rustic" ? '<span class="chip rustic">Rustic</span>' : ""}
      </span>
      <span class="meta">${escapeHtml(sub)}made for ${madeFor}</span>
      ${fit && !fit.made_for ? `<span class="meta">On this block: ${fit.figure_label}${fit.yaw ? `, turned ${Math.abs(fit.yaw)}°` : ""}</span>` : ""}
    </span>
  </button>`;
}

function renderGallery() {
  const shown = state.designs.filter(
    (d) => (state.style === "all" || d.style === state.style) && (state.level === "all" || d.level === state.level),
  );
  let html;
  if (state.block === "all") {
    html = shown.map(card).join("");
  } else {
    const made = shown.filter((d) => d.fits[state.block].made_for);
    const other = shown
      .filter((d) => !d.fits[state.block].made_for)
      .sort((a, b) => b.fits[state.block].fill_pct - a.fits[state.block].fill_pct);
    const label = blockLabel(state.block);
    html = `<p class="gallery-head">Made for a ${label} block</p>
      ${made.length ? made.map(card).join("") : `<p class="empty">None with these filters.</p>`}
      ${other.length ? `<p class="gallery-head">Also fit a ${label} block, smaller</p>${other.map(card).join("")}` : ""}`;
  }
  $("gallery").innerHTML = shown.length ? html : `<p class="empty">No designs match these filters.</p>`;
  const q = state.block === "all" ? "" : `?block=${state.block}`;
  history.replaceState(null, "", `/explore${q}`);
}

for (const [id, key] of [["f-block", "block"], ["f-style", "style"], ["f-level", "level"]]) {
  $(id).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-value]");
    if (!b) return;
    state[key] = b.dataset.value;
    renderFilters();
    renderGallery();
  });
}

$("gallery").addEventListener("click", (e) => {
  const b = e.target.closest(".design-card");
  if (b) openDrawer(b.dataset.key);
});

// ---------------------------------------------------------------- thumbnails

function getPreview(key) {
  state.previews[key] ??= fetch(`/api/preview/${key}`)
    .then((r) => r.json())
    .then((p) => ({ geom: meshGeometry(p.positions, p.indices), lo: p.lo, hi: p.hi, grain: "xyz".indexOf(p.grain) }));
  return state.previews[key];
}

const thumbRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
thumbRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
thumbRenderer.setSize(400, 300, false);
const thumbScene = new THREE.Scene();
const thumbCamera = new THREE.PerspectiveCamera(30, 4 / 3, 0.01, 100);
thumbCamera.up.set(0, 0, 1);
thumbScene.add(new THREE.HemisphereLight(0xfff8ee, 0x8a7a66, 1.6));
const thumbKey = new THREE.DirectionalLight(0xffffff, 1.5);
thumbKey.position.set(3, -4, 6);
const thumbFill = new THREE.DirectionalLight(0xffffff, 0.45);
thumbFill.position.set(-3, 3, 1);
thumbScene.add(thumbKey, thumbFill);
const thumbMesh = new THREE.Mesh(new THREE.BufferGeometry(), woodMaterial());
thumbScene.add(thumbMesh);

/** Aim a camera from direction `dir` so the box lo..hi fills the view. */
function aim(camera, lo, hi, dir, margin = 0.86) {
  const center = new THREE.Vector3(...lo).add(new THREE.Vector3(...hi)).multiplyScalar(0.5);
  const d = new THREE.Vector3(...dir).normalize();
  const forward = d.clone().negate();
  const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
  const up = new THREE.Vector3().crossVectors(right, forward);
  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * margin;
  const tanH = tanV * camera.aspect;
  let dist = 0;
  for (const x of [lo[0], hi[0]]) for (const y of [lo[1], hi[1]]) for (const z of [lo[2], hi[2]]) {
    const v = new THREE.Vector3(x, y, z).sub(center);
    const depth = v.dot(d);
    dist = Math.max(dist, depth + Math.abs(v.dot(up)) / tanV, depth + Math.abs(v.dot(right)) / tanH);
  }
  camera.position.copy(center).addScaledVector(d, dist);
  camera.lookAt(center);
  return center;
}

async function makeThumb(d) {
  const p = await getPreview(d.key);
  const size = p.hi.map((h, i) => h - p.lo[i]);
  paint(p.geom, p.grain, size, null, 0.1);
  thumbMesh.geometry = p.geom;
  aim(thumbCamera, p.lo, p.hi, [1, -1.25, 0.6]);
  thumbRenderer.render(thumbScene, thumbCamera);
  state.thumbs[d.key] = thumbRenderer.domElement.toDataURL("image/png");
  document.querySelectorAll(`[data-thumb="${d.key}"]`).forEach((img) => (img.src = state.thumbs[d.key]));
}

// ---------------------------------------------------------------- the drawer

let viewer = null;
const placed = new THREE.Group();

function openDrawer(key) {
  const d = state.designs.find((x) => x.key === key);
  state.open = d;
  state.openBlock = state.block !== "all" ? state.block : d.blocks[0];
  $("drawer").hidden = false;
  if (!viewer) {
    viewer = createViewer($("preview"));
    viewer.scene.add(placed);
  }
  viewer.resize();
  renderDrawer();
  $("close").focus();
}

function closeDrawer() {
  $("drawer").hidden = true;
  state.open = null;
}

async function renderDrawer() {
  const d = state.open;
  const blk = state.openBlock;
  const fit = d.fits[blk];
  $("drawer-info").innerHTML = `
    <div class="chips">
      <span class="chip level-${d.level}">${d.level}</span>
      ${d.style === "Rustic" ? '<span class="chip rustic">Rustic</span>' : '<span class="chip">Classic</span>'}
      <span class="chip">${escapeHtml(d.subject)}</span>
    </div>
    <h2 id="d-name">${escapeHtml(d.name)}</h2>
    <p>${escapeHtml(d.blurb)}</p>
    <p class="card-label" style="margin-top:6px">Cuts you'll use</p>
    <ul class="drawer-cuts">${d.cuts
      .map((c) => `<li><a href="/learn#${c.key}">${escapeHtml(c.name)}</a> <span class="where">${escapeHtml(c.where)}</span></li>`)
      .join("")}</ul>
    <p class="card-label" style="margin-top:6px">Pick a block</p>
    <ul class="fit-list">${Object.keys(state.blocks)
      .map((b) => {
        const f = d.fits[b];
        return `<li><button data-block="${b}" aria-pressed="${b === blk}">
          <span class="blk">${blockLabel(b)}</span>
          <span class="what">${f.figure_label}${f.made_for ? " · made for it" : ""}</span>
          <span class="why">${f.yaw ? `Turned ${Math.abs(f.yaw)}° in the block · ` : ""}uses ${f.fill_pct.toFixed(0)}% of the wood</span>
        </button></li>`;
      })
      .join("")}</ul>
    <p class="sub">${escapeHtml(fit.set_down)}</p>
    <a class="btn primary" href="/?design=${d.key}&block=${blk}">Plan this carving →</a>`;

  const p = await getPreview(d.key);
  if (state.open !== d || state.openBlock !== blk) return;
  placed.clear();
  const mesh = new THREE.Mesh(p.geom, woodMaterial());
  paint(p.geom, p.grain, p.hi.map((h, i) => h - p.lo[i]), null, 2.4 / fit.scale);
  mesh.scale.setScalar(fit.scale);
  mesh.rotation.z = THREE.MathUtils.degToRad(fit.yaw);
  mesh.position.set(...fit.offset);
  const [L, W, H] = fit.blank_mm;
  const wood = new THREE.Mesh(
    new THREE.BoxGeometry(L, W, H),
    new THREE.MeshBasicMaterial({ color: 0xd9c3a0, transparent: true, opacity: 0.12, depthWrite: false }),
  );
  wood.position.set(L / 2, W / 2, H / 2);
  placed.add(mesh, wood, blockEdges(fit.blank_mm, 0x8a7a66, 0.7));
  await new Promise(requestAnimationFrame); // let the drawer lay out, so the framing uses its real size
  viewer.resize();
  viewer.frame(fit.blank_mm, "iso", true);
}

$("drawer-info").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-block]");
  if (!b) return;
  state.openBlock = b.dataset.block;
  renderDrawer();
});

$("close").addEventListener("click", closeDrawer);
$("drawer").addEventListener("click", (e) => {
  if (e.target === $("drawer")) closeDrawer();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.open) closeDrawer();
});

// ---------------------------------------------------------------- start

renderFilters();
renderGallery();
state.designs.forEach((d) => getPreview(d.key)); // fetch them all at once
for (const d of state.designs) await makeThumb(d);
