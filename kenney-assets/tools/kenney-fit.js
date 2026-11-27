// kenney-fit.js: load Kenney GLB assets at real world scale in Three.js.
//
// Why this exists: Kenney kits are authored at roughly half scale and each
// kit disagrees about what a metre is. Never hand-tune scale numbers per
// model. Measure the loaded bounds, fit to a real world target, ground it.
//
// Manifest entry shape (see make-manifest.py):
//   { name, file, fit: { mode: "height"|"width"|"none", meters: 1.8 } }
// Placement shape:
//   { at: [x, z], rotY: radians, on: "hostAssetName", dx: 0, dz: 0 }

import * as THREE from 'three';

export function measure(obj) {
  obj.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(obj);
  const size = new THREE.Vector3();
  box.getSize(size);
  return { box, size };
}

function fitAxis(obj, axis, meters) {
  const { size } = measure(obj);
  const raw = axis === 'y' ? size.y : size.x;
  if (!raw) return 1;
  const s = meters / raw;
  obj.scale.multiplyScalar(s);
  obj.updateMatrixWorld(true);
  return s;
}

export const fitHeight = (obj, m) => fitAxis(obj, 'y', m);
export const fitWidth = (obj, m) => fitAxis(obj, 'x', m);

// Move obj so its base sits exactly at y (default floor 0), keeping x/z.
export function ground(obj, y = 0) {
  const { box } = measure(obj);
  obj.position.y += y - box.min.y;
  obj.updateMatrixWorld(true);
  return obj;
}

// Centre obj horizontally over (x, z). Call after scaling and rotation.
export function centerAt(obj, x, z) {
  const { box } = measure(obj);
  const c = new THREE.Vector3();
  box.getCenter(c);
  obj.position.x += x - c.x;
  obj.position.z += z - c.z;
  obj.updateMatrixWorld(true);
  return obj;
}

// Sit obj on top of a host object (TV on a cabinet, laptop on a desk).
// dx/dz offset from the host centre, in metres.
export function placeOn(obj, host, dx = 0, dz = 0) {
  const hb = measure(host).box;
  const hc = new THREE.Vector3();
  hb.getCenter(hc);
  centerAt(obj, hc.x + dx, hc.z + dz);
  ground(obj, hb.max.y);
  return obj;
}

// Load every manifest entry, scale it, place it, and return a name map.
// placements: { name: { at, rotY, on, dx, dz } }. Hosts must be listed
// before the items that sit on them in the manifest array.
export async function loadScene(loader, manifest, placements, scene) {
  const placed = {};
  const report = {};
  for (const entry of manifest) {
    const gltf = await loader.loadAsync(entry.file);
    const obj = gltf.scene;
    const raw = measure(obj).size.clone();
    let scale = 1;
    if (entry.fit && entry.fit.mode === 'height') scale = fitHeight(obj, entry.fit.meters);
    if (entry.fit && entry.fit.mode === 'width') scale = fitWidth(obj, entry.fit.meters);
    const p = placements[entry.name] || {};
    if (p.rotY) obj.rotation.y = p.rotY;
    if (p.on && placed[p.on]) {
      placeOn(obj, placed[p.on], p.dx || 0, p.dz || 0);
    } else {
      ground(obj, 0);
      if (p.at) centerAt(obj, p.at[0], p.at[1]);
    }
    scene.add(obj);
    placed[entry.name] = obj;
    const fin = measure(obj);
    report[entry.name] = {
      raw: { x: raw.x, y: raw.y, z: raw.z },
      scale,
      final: { x: fin.size.x, y: fin.size.y, z: fin.size.z },
      baseY: fin.box.min.y,
      topY: fin.box.max.y,
      foot: { minX: fin.box.min.x, maxX: fin.box.max.x, minZ: fin.box.min.z, maxZ: fin.box.max.z },
      target: entry.fit ? entry.fit.meters : null,
      mode: entry.fit ? entry.fit.mode : 'none',
      on: p.on || null,
    };
  }
  return { placed, report };
}

// G4 helper: AABB footprint overlaps among grounded items.
// exclude: names to skip (rugs). stacked items are skipped via report.on.
export function footprintOverlaps(report, exclude = []) {
  const names = Object.keys(report).filter(
    (n) => !report[n].on && !exclude.includes(n)
  );
  const hits = [];
  for (let i = 0; i < names.length; i++) {
    for (let j = i + 1; j < names.length; j++) {
      const a = report[names[i]].foot, b = report[names[j]].foot;
      const ox = Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX);
      const oz = Math.min(a.maxZ, b.maxZ) - Math.max(a.minZ, b.minZ);
      if (ox > 0.02 && oz > 0.02) hits.push([names[i], names[j], +ox.toFixed(3), +oz.toFixed(3)]);
    }
  }
  return hits;
}
