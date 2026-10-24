"""Ingest a raw Copernicus Browser Landsat export (zip) into landsat/<date UTC>/<collection>/.
Usage: python3 scripts/ingest.py EXPORT.zip [--note "Landsat 9, path 40 row 23, 18:17 UTC"]
Copies files unchanged; writes manifest.json (SHA-256 per file, frame, pixel size, coverage of reference points, cloud/haze check) and a preview."""
import sys, os, re, json, hashlib, zipfile, tempfile, glob, shutil
import numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX = (-110.96, 52.74, -110.85, 52.80)
POINTS = {"origin": (-110.9214, 52.7764), "A_range2": (-110.90632, 52.77279), "B_road_head": (-110.89965, 52.77045), "range11": (-110.9577, 52.7678)}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def main(zin, note):
    import rasterio
    from rasterio.windows import from_bounds
    from PIL import Image
    tmp = tempfile.mkdtemp(); zipfile.ZipFile(zin).extractall(tmp)
    files = sorted(f for f in glob.glob(tmp + "/**/*", recursive=True) if os.path.isfile(f))
    groups = {}
    for f in files:
        b = os.path.basename(f)
        m = re.match(r"(\d{4}-\d{2}-\d{2})-\d{2}_\d{2}_\d{4}-\d{2}-\d{2}-\d{2}_\d{2}_(Landsat[^_]*?(?:_[0-9-]+)?)_(L\d[A-Z]?)_(.+)\.(tiff?|jpe?g|png)$", b, re.I)
        if not m: print("skip", b); continue
        groups.setdefault((m.group(1), m.group(2), m.group(3).upper(), "tiff" if m.group(5).lower().startswith("tif") else "jpg"), []).append(f)
    for (date, mission, lvl, fmt), fs in groups.items():
        dest = os.path.join(REPO, "landsat", date, f"{lvl}_{fmt}"); os.makedirs(dest, exist_ok=True)
        tifs = [f for f in fs if f.lower().endswith((".tif", ".tiff"))]
        qa = {}
        raw = [f for f in tifs if "(Raw)" in f] or tifs
        if raw:
            r = rasterio.open(raw[0]); a = r.read(1)
            qa = {"crs": str(r.crs), "pixel_deg": list(r.res), "pixel_m_approx": [round(r.res[0] * 111320 * np.cos(np.radians(52.77)), 1), round(r.res[1] * 110950, 1)],
                  "bounds": [round(v, 5) for v in r.bounds], "covers_points": {}, "values_at_points": {}}
            for k, (lo, la) in POINTS.items():
                i, j = r.index(lo, la); qa["covers_points"][k] = bool(0 <= i < a.shape[0] and 0 <= j < a.shape[1] and a[i, j] != 0)
            box = r.read(1, window=from_bounds(*BOX, r.transform), boundless=True, fill_value=0)
            qa["fire_box_valid_frac"] = round(float((box != 0).mean()), 3)
            for f in raw:
                band = re.search(r"_(B\d+[A-Z]?|QA[^_(]*)_\(Raw\)", f)
                if not band: continue
                rr = rasterio.open(f); aa = rr.read(1)
                for k, (lo, la) in POINTS.items():
                    i, j = rr.index(lo, la)
                    if 0 <= i < aa.shape[0] and 0 <= j < aa.shape[1]: qa["values_at_points"].setdefault(k, {})[band.group(1)] = round(float(aa[i, j]), 4)
            qa["usable"] = bool(all(qa["covers_points"][k] for k in ("origin", "A_range2", "B_road_head")) and qa["fire_box_valid_frac"] > 0.95)
        vis = next((f for f in tifs if re.search(r"True_color|SWIR|False_color", f)), None)
        prev = []
        if vis:
            rr = rasterio.open(vis); x = rr.read([1, 2, 3], window=from_bounds(*BOX, rr.transform), boundless=True).astype("float32"); x = np.moveaxis(x, 0, -1)
            p = np.percentile(x[x > 0], 99.5) if (x > 0).any() else 1
            im = Image.fromarray((np.clip(x / p, 0, 1) * 255).astype("uint8")); im.thumbnail((1200, 1200)); im.save(os.path.join(dest, "preview.jpg"), quality=85); prev.append("preview.jpg")
        for f in fs: shutil.copy2(f, os.path.join(dest, os.path.basename(f)))
        man = {"source": "Copernicus Browser export (Sentinel Hub), received from Prime Rogue", "date_utc": date, "mission": mission, "level": lvl, "format": fmt, "note": note or "",
               "layers": sorted(re.sub(r".*_(L\d[A-Z]?)_", "", os.path.splitext(os.path.basename(f))[0]) for f in fs), "n_files": len(fs), "qa": qa, "previews": prev,
               "original_upload": os.path.basename(zin), "original_upload_sha256": sha(zin),
               "files": {os.path.basename(f): {"bytes": os.path.getsize(f), "sha256": sha(f)} for f in fs},
               "licence": "Landsat data courtesy of the U.S. Geological Survey (public domain)"}
        json.dump(man, open(os.path.join(dest, "manifest.json"), "w"), indent=1)
        print(date, mission, lvl, fmt, len(fs), qa.get("pixel_m_approx"), qa.get("usable"))
    shutil.rmtree(tmp)
if __name__ == "__main__":
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else None
    main(sys.argv[1], note)
