# CFB Wainwright fire: Landsat imagery

Raw, unmodified Landsat 8/9 exports covering the Oct. 17, 2026 fire at CFB Wainwright, Alberta, kept so anyone can check the analysis in the [CFB Wainwright fire archive](https://github.com/primerogueinc/cfb-wainwright-fire-archive). Sentinel data are in separate repositories ([Sentinel-2](https://github.com/primerogueinc/CFB-Wainwright---Full-Satellite-Data---Copernicus-), [Sentinel-1](https://github.com/primerogueinc/CFB-Wainwright-Fire-Sentinel-1), [Sentinel-3](https://github.com/primerogueinc/CFB-Wainwright-Sentinel-3-Archives)).

Landsat passed over the base at 12:17 p.m. MDT on Oct. 17, while the fire was burning: NASA FIRMS recorded 59 active-fire detections from that pass. Its 30 m shortwave-infrared bands show flaming fire, and its 15 m panchromatic band shows ground detail.

Each folder `landsat/<date UTC>/<level>_<format>/` holds the files exactly as exported from [Copernicus Browser](https://browser.dataspace.copernicus.eu/), a `manifest.json` (SHA-256 of every file, frame, pixel size, coverage of the fire's origin, the Range 2 point, the road head and Range 11, band values at those points) and a preview.

## Exports

| Date (UTC) | Level | Format | Files | Usable | Folder |
|---|---|---|---|---|---|

## Adding an export

```
python3 scripts/ingest.py path/to/Browser_images.zip [--note "Landsat 9, 18:17 UTC"]
```

## Licence

Scripts and documentation: see LICENSE. Data: Landsat imagery courtesy of the U.S. Geological Survey; public domain.

Maintained by Prime Rogue Inc.
