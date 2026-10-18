#!/usr/bin/env python3
"""Compute SNM per corner from `klt sim` waveform artifacts, with the pinned gf180-sram extractor.

Usage: snm_from_artifacts.py <outdir> [--pair]
  <outdir>: the `klt sim -o` directory (one subdir per corner holding waveform.raw.json).
  default: single-curve mode on v(out) vs v(in) (decoupled half-cell; identical inverters).
  --pair : Monte Carlo mode; curves v(outa) and v(outb) (two independently mismatched half cells).
Prints per corner: eye_snm (largest inscribed square, 45-degree frame) and pinned_snm (gf180-sram snm_extract.py).
"""
import bisect
import importlib.util
import json
import math
import pathlib
import sys

pin = pathlib.Path(__file__).resolve().parents[3] / "sim/build/pinned/snm_extract.py"
spec = importlib.util.spec_from_file_location("snm_extract", pin)
sx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sx)


def curve(wf, xname, yname):
    names = [v["name"] for v in wf["variables"]]
    xi, yi = names.index(xname), names.index(yname)
    pts = sorted((p[xi], p[yi]) for p in wf["points"])
    return pts


def rotated(pts):
    """(u, v) = ((x-y)/sqrt2, (x+y)/sqrt2) of a monotone-decreasing VTC, sorted by u."""
    r2 = math.sqrt(2)
    return sorted(((x - y) / r2, (x + y) / r2) for x, y in pts)


def at(rot, u):
    us = [p[0] for p in rot]
    i = bisect.bisect_left(us, u)
    if i <= 0:
        return rot[0][1]
    if i >= len(rot):
        return rot[-1][1]
    (u0, v0), (u1, v1) = rot[i - 1], rot[i]
    return v0 if u1 == u0 else v0 + (v1 - v0) * (u - u0) / (u1 - u0)


def eyes(pts1, pts2=None, n=4000):
    """Largest axis-aligned square in each eye of the butterfly (Seevinck, 45-degree frame).

    Curve 1 is y=f1(x); the mirror of curve 2 about y=x is x=f2(y). In the rotated frame the
    mirror of a curve is its reflection u -> -u, so the gap along the diagonal at coordinate u
    is D(u) = v1(u) - v2(-u) and the side of the square is |D|/sqrt2, maximised inside each eye
    (between consecutive sign changes of D; the outer tails are not eyes).
    """
    r1 = rotated(pts1)
    r2 = rotated(pts2 if pts2 is not None else pts1)
    umax = max(abs(r1[0][0]), abs(r1[-1][0]), abs(r2[0][0]), abs(r2[-1][0]))  # `at` clamps beyond a curve end
    us = [-umax + 2 * umax * k / n for k in range(n + 1)]
    d = [at(r1, u) - at(r2, -u) for u in us]
    # sign changes of D, ignoring samples inside the flat, saturated tails (|D| ~ 0)
    nz = [(i, x > 0) for i, x in enumerate(d) if abs(x) > 1e-4]
    cross = [nz[k][0] for k in range(len(nz) - 1) if nz[k][1] != nz[k + 1][1]]
    if len(cross) == 1 and abs(d[0]) < 1e-4 and abs(d[-1]) < 1e-4:
        # rail-to-rail curves meet their mirrors exactly at the sweep ends: the stable states
        cross = [0, cross[0], n]
    if len(cross) < 3:
        raise ValueError(f"{len(cross)} diagonal crossings (need 3 for a bistable cell)")
    c = [cross[0], cross[len(cross) // 2], cross[-1]]
    s = math.sqrt(2)
    return (max(abs(x) for x in d[c[0]:c[1] + 1]) / s, max(abs(x) for x in d[c[1]:c[2] + 1]) / s)


def snm_for(path, pair):
    wf = json.load(open(path))
    if pair:
        c1, c2 = curve(wf, "v(in)", "v(outa)"), curve(wf, "v(in)", "v(outb)")
        return sx.snm(c1, c2), eyes(c1, c2)
    c = curve(wf, "v(in)", "v(out)")
    return sx.snm(c), eyes(c)


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1])
    pair = "--pair" in sys.argv
    for p in sorted(root.glob("*/waveform.raw.json")):
        try:
            (plo, phi), (elo, ehi) = snm_for(p, pair)
            print(f"{p.parent.name} eye_snm={min(elo, ehi):.6f} pinned_snm={min(plo, phi):.6f}")
        except Exception as e:  # reported, never dropped
            print(f"{p.parent.name} ERROR {e}")
