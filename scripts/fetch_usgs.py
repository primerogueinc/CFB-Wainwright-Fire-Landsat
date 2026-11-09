"""Fetch a full Landsat Collection 2 Level-2 scene, unmodified, into landsat/<date UTC>/<level>_usgs/.

Usage: python3 scripts/fetch_usgs.py PRODUCT_ID [--note "..."]
  e.g. python3 scripts/fetch_usgs.py LC08_L2SP_040023_20261017_02_T1

Source: Microsoft Planetary Computer's copy of the USGS Landsat Collection 2 archive
(the USGS's own download servers require an EROS sign-in). Files are written byte-for-byte
as served; the STAC item is saved alongside (with access tokens removed). Writes manifest.json
(SHA-256 per file, frame, pixel size, coverage of reference points, band values there) and
a SWIR preview of the area around the fire."""
import sys, os, json, hashlib, urllib.request, urllib.parse
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2"
BOX = (-110.96, 52.74, -110.85, 52.80)
POINTS = {"origin": (-110.9214, 52.7764), "A_range2": (-110.90632, 52.77279), "B_road_head": (-110.89965, 52.77045), "range11": (-110.9577, 52.7678)}


def get_json(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(url, dest):
    tmp = dest + ".part"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
                size = int(r.headers.get("Content-Length", 0))
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            if size and os.path.getsize(tmp) != size:
                raise IOError(f"short read {os.path.getsize(tmp)} != {size}")
            os.replace(tmp, dest)
            return
        except Exception as e:
            print("  retry", os.path.basename(dest), e)
    raise SystemExit("download failed: " + dest)


def main(item_id, note):
    import rasterio
    from rasterio.warp import transform, transform_bounds
    from rasterio.windows import from_bounds
    from PIL import Image

    item = get_json(STAC + item_id)
    token = get_json(SAS)["token"]
    p = item["properties"]
    date = p["datetime"][:10]
    level = p.get("landsat:correction", "L2")
    dest = os.path.join(REPO, "landsat", date, f"{level}_usgs")
    os.makedirs(dest, exist_ok=True)

    files = {}
    for key, a in item["assets"].items():
        href = a["href"]
        if "blob.core.windows.net" not in href:
            continue
        name = os.path.basename(urllib.parse.urlparse(href).path)
        out = os.path.join(dest, name)
        if not os.path.exists(out):
            print("get", name)
            download(href + "?" + token, out)
        files[name] = {"asset": key, "source_url": href, "bytes": os.path.getsize(out), "sha256": sha(out)}

    # STAC item as served, minus links/rendering helpers that embed tokens
    clean = {k: v for k, v in item.items() if k != "links"}
    clean["assets"] = {k: {kk: vv for kk, vv in a.items()} for k, a in item["assets"].items() if "blob.core.windows.net" in a["href"]}
    json.dump(clean, open(os.path.join(dest, "stac_item.json"), "w"), indent=1)

    # QA: frame, coverage of reference points, values at points
    def band(suffix):
        n = next((n for n in files if n.endswith(suffix)), None)
        return os.path.join(dest, n) if n else None

    qa = {"values_at_points": {}}
    ref = rasterio.open(band("_SR_B7.TIF"))
    a = ref.read(1)
    xs, ys = transform("EPSG:4326", ref.crs, [v[0] for v in POINTS.values()], [v[1] for v in POINTS.values()])
    qa.update({"crs": str(ref.crs), "pixel_m": list(ref.res), "bounds": [round(v, 1) for v in ref.bounds], "covers_points": {}})
    for (k, _), x, y in zip(POINTS.items(), xs, ys):
        i, j = ref.index(x, y)
        qa["covers_points"][k] = bool(0 <= i < a.shape[0] and 0 <= j < a.shape[1] and a[i, j] != 0)
    bb = transform_bounds("EPSG:4326", ref.crs, *BOX)
    box = ref.read(1, window=from_bounds(*bb, ref.transform), boundless=True, fill_value=0)
    qa["fire_box_valid_frac"] = round(float((box != 0).mean()), 3)
    for n in sorted(files):
        if not n.endswith(".TIF"):
            continue
        r = rasterio.open(os.path.join(dest, n))
        tag = n.split("_02_T1_")[-1][:-4]
        px, py = transform("EPSG:4326", r.crs, [v[0] for v in POINTS.values()], [v[1] for v in POINTS.values()])
        for (k, _), x, y in zip(POINTS.items(), px, py):
            i, j = r.index(x, y)
            if 0 <= i < r.height and 0 <= j < r.width:
                v = r.read(1, window=((i, i + 1), (j, j + 1)))[0, 0]
                qa["values_at_points"].setdefault(k, {})[tag] = int(v) if np.issubdtype(type(v), np.integer) else round(float(v), 4)
    qp = rasterio.open(band("_QA_PIXEL.TIF")).read(1, window=from_bounds(*bb, ref.transform))
    qa["fire_box_qa_pixel"] = {"cloud_frac": round(float((((qp >> 3) & 1) | ((qp >> 1) & 1)).mean()), 3),
                               "clear_frac": round(float(((qp >> 6) & 1).mean()), 3),
                               "note": "USGS cloud mask; dense smoke over an active fire is often flagged as cloud."}
    qa["usable"] = bool(all(qa["covers_points"][k] for k in ("origin", "A_range2", "B_road_head")) and qa["fire_box_valid_frac"] > 0.95)

    # Preview: SWIR2 / SWIR1 / red (fire shows bright red-orange), area around the base
    stack = []
    for s in ("_SR_B7.TIF", "_SR_B6.TIF", "_SR_B4.TIF"):
        r = rasterio.open(band(s))
        stack.append(r.read(1, window=from_bounds(*transform_bounds("EPSG:4326", r.crs, -111.25, 52.62, -110.6, 52.92), r.transform)).astype("float32"))
    x = np.dstack(stack)
    pos = x[x > 0]
    lo, hi = (np.percentile(pos, 1), np.percentile(pos, 99.5)) if pos.size else (0, 1)
    im = Image.fromarray((np.clip((x - lo) / (hi - lo), 0, 1) * 255).astype("uint8"))
    im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    im.save(os.path.join(dest, "preview_swir.jpg"), quality=88)

    man = {"source": "USGS Landsat Collection 2 Level-2, via Microsoft Planetary Computer (landsat-c2-l2)",
           "product_id": os.path.commonprefix([n for n in files if n.endswith(".TIF")]).rstrip("_"),
           "stac_item": item_id, "date_utc": date, "datetime_utc": p["datetime"], "mission": p["platform"],
           "wrs_path_row": f"{p['landsat:wrs_path']}/{p['landsat:wrs_row']}", "level": level,
           "scene_cloud_cover": p.get("eo:cloud_cover"), "doi": p.get("sci:doi"), "note": note or "",
           "n_files": len(files), "qa": qa, "previews": ["preview_swir.jpg"], "files": files,
           "licence": "Landsat data courtesy of the U.S. Geological Survey (public domain)"}
    json.dump(man, open(os.path.join(dest, "manifest.json"), "w"), indent=1)
    print(date, level, len(files), "files", qa["usable"], qa["fire_box_qa_pixel"])


if __name__ == "__main__":
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else None
    main(sys.argv[1], note)
