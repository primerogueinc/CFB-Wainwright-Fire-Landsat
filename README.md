# CFB Wainwright fire: Landsat imagery

Raw, unmodified Landsat 8/9 exports covering the Oct. 17, 2026 fire at CFB Wainwright, Alberta, kept so anyone can check the analysis in the [CFB Wainwright fire archive](https://github.com/primerogueinc/cfb-wainwright-fire-archive). Sentinel data are in separate repositories ([Sentinel-2](https://github.com/primerogueinc/CFB-Wainwright---Full-Satellite-Data---Copernicus-), [Sentinel-1](https://github.com/primerogueinc/CFB-Wainwright-Fire-Sentinel-1), [Sentinel-3](https://github.com/primerogueinc/CFB-Wainwright-Sentinel-3-Archives)).

Landsat passed over the base at 12:17 p.m. MDT on Oct. 17, while the fire was burning: NASA FIRMS recorded 59 active-fire detections from that pass. Its 30 m shortwave-infrared bands show flaming fire, and its 15 m panchromatic band shows ground detail.

Each folder holds the files exactly as received: `landsat/<date UTC>/<level>_<format>/` for exports from [Copernicus Browser](https://browser.dataspace.copernicus.eu/), and `landsat/<date UTC>/<level>_usgs/` for full USGS scenes. Each also has a `manifest.json` (SHA-256 of every file, frame, pixel size, coverage of the fire's origin, the Range 2 point, the road head and Range 11, band values at those points) and a preview.

## Exports

| Date (UTC) | Level | Format | Files | Usable | Folder |
|---|---|---|---|---|---|
| 2026-10-17 18:17 | Collection 2 Level-2 (L2SP) | Full scene, cloud-optimized GeoTIFF + metadata | 23 | Yes: the fire front shows in the SWIR bands through smoke. The USGS cloud mask flags the whole area as cloud (smoke). | [`landsat/2026-10-17/L2SP_usgs/`](landsat/2026-10-17/L2SP_usgs/) |

## Full USGS scenes

The 18:17 UTC Oct. 17 pass is kept as the complete Landsat 8 Collection 2 Level-2 scene (path 40, row 23, product `LC08_L2SP_040023_20261017_20261021_02_T1`): surface reflectance bands 1–7, surface temperature and its inputs, QA layers, angle and metadata files. The USGS's own download server requires an EROS sign-in, so the files were taken unmodified from Microsoft Planetary Computer's copy of the USGS archive; `stac_item.json` records the catalogue entry. Level-1 files for the same scene can be downloaded from USGS EarthExplorer with a free account. Dataset citation: Earth Resources Observation and Science (EROS) Center (2020), Landsat 8-9 OLI/TIRS Collection 2 Level-2, U.S. Geological Survey, https://doi.org/10.5066/P9OGBGM6.

```
python3 scripts/fetch_usgs.py LC08_L2SP_040023_20261017_02_T1 [--note "..."]
```

## Adding an export

```
python3 scripts/ingest.py path/to/Browser_images.zip [--note "Landsat 9, 18:17 UTC"]
```

## Licence

Scripts and documentation: see LICENSE. Data: Landsat imagery courtesy of the U.S. Geological Survey; public domain.

Maintained by Prime Rogue Inc. Contact: contact@primerogueinc.com
