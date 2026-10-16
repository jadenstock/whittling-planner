// Shared by the planner and the explore page: data decoding, the 3D viewer, and wood coloring.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export const $ = (id) => document.getElementById(id);

export function decode(b64, Type) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Type(bytes.buffer);
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export const blockLabel = (name) => name.split("x").join(" × ");

/** A BufferGeometry from base64 positions and indices, with a color attribute to paint. */
export function meshGeometry(positionsB64, indicesB64) {
  const g = new THREE.BufferGeometry();
  const positions = decode(positionsB64, Float32Array);
  g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(positions.length), 3));
  g.setIndex(new THREE.BufferAttribute(decode(indicesB64, Uint32Array), 1));
  g.computeVertexNormals();
  return g;
}

// ---------------------------------------------------------------- wood

const WOOD_LIGHT = new THREE.Color(0xead6b4); // THREE.Color converts hex from sRGB to linear
const WOOD_DARK = new THREE.Color(0xc4a179);

export const smoothstep = (a, b, x) => {
  const t = Math.min(Math.max((x - a) / (b - a), 0), 1);
  return t * t * (3 - 2 * t);
};

/** Basswood with growth rings, so the grain direction is visible on the model.
 *  `ringMm` is the ring spacing in the model's units. */
export function woodColor(p, grainAxis, size, out, ringMm = 2.4) {
  const [a, b] = [0, 1, 2].filter((i) => i !== grainAxis);
  // pith off one corner of the block, so the rings cross every long-grain face at an angle
  const du = p[a] + size[a] * 0.8 + ringMm * 6;
  const dv = p[b] + size[b] * 0.8 + ringMm * 6;
  const r = Math.hypot(du, dv) + 0.15 * ringMm * Math.sin((p[grainAxis] * 0.06 * 2.4) / ringMm + (du * 0.05 * 2.4) / ringMm);
  const ring = (r / ringMm) % 1;
  out.copy(WOOD_LIGHT).lerp(WOOD_DARK, smoothstep(0.72, 0.97, ring) * 0.5);
  return out;
}

const tmp = new THREE.Color();

/** Fill a geometry's colors: wood, plus an optional overlay per vertex. */
export function paint(geom, grainAxis, size, overlay, ringMm) {
  const pos = geom.attributes.position.array;
  const col = geom.attributes.color.array;
  const p = [0, 0, 0];
  for (let i = 0, n = pos.length / 3; i < n; i++) {
    p[0] = pos[3 * i];
    p[1] = pos[3 * i + 1];
    p[2] = pos[3 * i + 2];
    woodColor(p, grainAxis, size, tmp, ringMm);
    if (overlay) overlay(i, tmp);
    col[3 * i] = tmp.r;
    col[3 * i + 1] = tmp.g;
    col[3 * i + 2] = tmp.b;
  }
  geom.attributes.color.needsUpdate = true;
}

// ---------------------------------------------------------------- viewer

export const VIEWS = {
  iso: [1, -1.25, 0.75],
  front: [1, 0, 0.08],
  side: [0, -1, 0.08],
  top: [-0.002, 0, 1],
};

/** A Z-up scene with orbit controls, lights, and camera framing. */
export function createViewer(el, { fov = 35 } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 5000);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  scene.add(new THREE.HemisphereLight(0xfff8ee, 0x8a7a66, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 1.5);
  const fill = new THREE.DirectionalLight(0xffffff, 0.45);
  scene.add(key, fill);

  let goal = null;
  let box = [1, 1, 1];

  const viewer = {
    renderer, scene, camera, controls,
    /** Frame the box [0, size] for a view; `instant` jumps instead of gliding. */
    frame(size, view = "iso", instant = false) {
      box = size;
      const [L, W, H] = size;
      controls.target.set(L / 2, W / 2, H / 2);
      key.position.set(L * 2, -W * 2.5, H * 3);
      fill.position.set(-L * 2, W * 2, H);
      viewer.look(view, instant);
    },
    look(view, instant = false) {
      const dir = new THREE.Vector3(...VIEWS[view]).normalize();
      const pos = controls.target.clone().addScaledVector(dir, fitDistance(dir));
      if (instant) {
        camera.position.copy(pos);
        goal = null;
      } else {
        goal = pos;
      }
    },
    resize() {
      renderer.setSize(el.clientWidth, el.clientHeight, false);
      camera.aspect = el.clientWidth / Math.max(el.clientHeight, 1);
      camera.updateProjectionMatrix();
    },
  };

  /** Camera distance along `dir` at which every corner of the box fits in view. */
  function fitDistance(dir) {
    const [L, W, H] = box;
    const forward = dir.clone().negate();
    const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
    const up = new THREE.Vector3().crossVectors(right, forward);
    const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.8; // 20% breathing room
    const tanH = tanV * camera.aspect;
    let dist = 0;
    for (const cx of [0, L]) for (const cy of [0, W]) for (const cz of [0, H]) {
      const v = new THREE.Vector3(cx, cy, cz).sub(controls.target);
      const depth = v.dot(dir);
      dist = Math.max(dist, depth + Math.abs(v.dot(up)) / tanV, depth + Math.abs(v.dot(right)) / tanH);
    }
    return dist;
  }

  new ResizeObserver(() => viewer.resize()).observe(el);
  viewer.resize();
  renderer.setAnimationLoop(() => {
    if (goal) {
      camera.position.lerp(goal, 0.18);
      if (camera.position.distanceTo(goal) < 0.001 * Math.max(...box)) goal = null;
    }
    controls.update();
    renderer.render(scene, camera);
  });
  return viewer;
}

/** Wireframe edges of the box [0, size]. */
export function blockEdges(size, color = 0x8a7a66, opacity = 0.45) {
  const [L, W, H] = size;
  const lines = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(L, W, H)),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }),
  );
  lines.position.set(L / 2, W / 2, H / 2);
  return lines;
}

export function woodMaterial() {
  return new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.85, metalness: 0,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1, // pencil lines draw on top
  });
}
