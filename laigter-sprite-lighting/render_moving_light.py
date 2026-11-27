#!/usr/bin/env python3
"""Moving light preview from diffuse + normal + specular maps.

Usage:
  python3 render_moving_light.py DIFFUSE NORMAL SPECULAR [--out DIR] [--frames 24]

Writes moving_light.gif (light orbiting the sprite) and before_after.png
(flat vs lit vs normal map) into the out folder (default: current folder).
Needs Pillow and numpy. The point is a fast honesty check: if the GIF does
not visibly relight, the maps are wrong, fix them before wiring an engine.
"""
import argparse, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diffuse")
    ap.add_argument("normal")
    ap.add_argument("specular")
    ap.add_argument("--out", default=".")
    ap.add_argument("--frames", type=int, default=24)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    diffuse = Image.open(args.diffuse).convert("RGBA")
    normal_img = Image.open(args.normal).convert("RGB").resize(diffuse.size)
    spec_img = Image.open(args.specular).convert("L").resize(diffuse.size)

    W, H = diffuse.size
    scale = max(1, 384 // max(W, H))
    DW, DH = W * scale, H * scale
    resample = Image.NEAREST if scale > 1 else Image.LANCZOS

    d = np.asarray(diffuse.resize((DW, DH), resample)).astype(np.float32) / 255.0
    n = np.asarray(normal_img.resize((DW, DH), resample)).astype(np.float32) / 255.0
    s = np.asarray(spec_img.resize((DW, DH), resample)).astype(np.float32) / 255.0
    normals = n * 2.0 - 1.0
    normals = normals / np.maximum(np.linalg.norm(normals, axis=2, keepdims=True), 1e-6)
    alpha = d[..., 3:4]

    yy, xx = np.mgrid[0:DH, 0:DW]
    frames = []
    for i in range(args.frames):
        ang = 2 * math.pi * i / args.frames
        light = np.stack([np.full((DH, DW), math.cos(ang)),
                          np.full((DH, DW), math.sin(ang)),
                          np.full((DH, DW), 0.65)], axis=2)
        light = light / np.linalg.norm(light, axis=2, keepdims=True)
        diff = np.clip(np.sum(normals * light, axis=2, keepdims=True), 0, 1)
        halfv = light + np.array([0, 0, 1.0])
        halfv = halfv / np.linalg.norm(halfv, axis=2, keepdims=True)
        spec = np.power(np.clip(np.sum(normals * halfv, axis=2, keepdims=True), 0, 1), 24) * s[..., None]
        lit = d[..., :3] * (0.38 + 0.85 * diff) + spec * 0.9
        comp_alpha = np.concatenate([np.clip(lit, 0, 1), alpha], axis=2)
        bg = np.where((((xx // 16) + (yy // 16)) % 2)[..., None] == 0, 0.92, 0.78)
        comp = comp_alpha[..., :3] * alpha + bg * (1 - alpha)
        frames.append(Image.fromarray((np.clip(comp, 0, 1) * 255).astype(np.uint8)))

    frames[0].save(out / "moving_light.gif", save_all=True,
                   append_images=frames[1:], duration=90, loop=0)

    flat_big = diffuse.resize((DW, DH), resample)
    bgim = Image.new("RGB", (DW, DH), (235, 235, 235))
    bgim.paste(flat_big, (0, 0), flat_big)
    sheet = Image.new("RGB", (DW * 3 + 24, DH + 44), "white")
    sheet.paste(bgim, (0, 44))
    sheet.paste(frames[args.frames // 4], (DW + 12, 44))
    sheet.paste(normal_img.resize((DW, DH), resample), (DW * 2 + 24, 44))
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 14), "BEFORE flat", fill="black")
    dr.text((DW + 20, 14), "AFTER lit", fill="black")
    dr.text((DW * 2 + 32, 14), "Normal map", fill="black")
    sheet.save(out / "before_after.png")
    print(f"ok size={diffuse.size} display={DW}x{DH} frames={args.frames} out={out}")


if __name__ == "__main__":
    main()
