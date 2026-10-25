# Changes from upstream

Upstream: https://github.com/ASFHyP3/hyp3-nisar-cv, tag `v0.1.0` at commit 047ca975452e155b74dc420a08c8b171c038ac91 (2026-10-16), by the Alaska Satellite Facility HyP3 team (Steven Beninati, Andrew Johnson and others), BSD 3-Clause License (Copyright (c) 2026, HyP3).

This copy starts from upstream's file tree at 047ca97 without its git history. It is unchanged except for the items below. The processing code (`gcov.py`, the Welford CV, the water mask and crop classification in `process.py`), the thresholds and the LICENSE are untouched. `.github/` was left out: its workflows lint the code, build the Docker image, and tag and publish releases on the upstream repository.

## 2026-10-25: README gives the water threshold as -16.5 dB

The README said `--water-threshold-db` defaults to `16.5`; the code's default (`process.WATER_THRESH_DB`, the ATBD water threshold) is `-16.5`. Open water reflects the radar signal away and its backscatter is far below that of land, so the threshold is negative. A user who copied `16.5` from the README would set it at +16.5 dB (about 45 in linear power), below which nearly every pixel falls, and almost the whole scene would be classified as water. Only the README changed.

## 2026-10-25: `--bucket` uploads the water mask and crop area

`process_crop_area` wrote `_WATER.tif` and `_CROP_100m.tif` but returned them as a separate list that `main()` discarded, so `--bucket` uploaded only the CV, CV_100m and NVALID files and the crop area product never reached the bucket. `process_crop_area` now adds its files to `result.outputs` and returns the result. This is upstream's own fix from its develop branch (commits b62f7a9b29235cacec28ef279a60bb58a31e66db and 2bd60c320780f7a5543cca5831ad78dd78ea5503, merged 2026-10-21; upstream's changelog lists it under 0.1.1, not yet tagged). Products do not change.

## 2026-10-25: the version comes from the git tag

`pyproject.toml` declared the version as dynamic but did not list `setuptools_scm` as a build requirement or configure it, so every install reported `0.0.0`, even from the tagged release. `setuptools_scm>=8` is now a build requirement with a `[tool.setuptools_scm]` table, so `nisar_cv.__version__` carries the tag (for example `0.1.0.post1`) and a dev version between tags. A copy without git metadata, such as a source archive, still installs and reports `0.0.0`.

## 2026-10-25: `--bucket` uploads the saved GCOV layers too

With `--save-gcovs true`, `process_cv` wrote one GeoTIFF per input granule but left it out of `result.outputs`, so a HyP3 job that asked for the layers never got them back (only files in the bucket leave the container). The saved layers now follow the products in `result.outputs` and are uploaded with them. Without `--save-gcovs` nothing changes. Products do not change.

## 2026-10-25: an Earthdata Login token in `EARTHDATA_TOKEN`

`gcov.earthdata_session()` could only log in with the username and password in `~/.netrc`. A platform that runs jobs on a user's behalf, such as NASA MAAP, can give the job that user's Earthdata Login token instead, and a token is safer to put in a job than a password. When `EARTHDATA_TOKEN` is set and not empty, the session now authenticates with `asf_search`'s `ASFSession().auth_with_token()`; otherwise it reads `~/.netrc` exactly as before. The granule downloads (`gcov.download_granule`, `ASFProduct.download`) use that same session, and the search needs no login, so this is the only change; nothing uses earthaccess or fsspec. If Earthdata Login rejects the token, the run stops with an `ASFAuthenticationError` that names `EARTHDATA_TOKEN`, and it does not fall back to `~/.netrc`. The variable name is the one burst2safe (ASFHyP3/burst2safe) reads. The README's credentials note has one line about it, and `tests/test_auth.py` covers both paths and a rejected token without network access. Products do not change.

Checked on 2026-10-25 from a clone tagged `v0.1.0.post2` (same env versions as below): `pytest` passes 4 tests (2 of them fail on the previous commit), ruff and mypy pass. The README example with `--crop-area true --save-gcovs true` and no token (the `~/.netrc` path) gives CV, CV_100m, NVALID, WATER and CROP_100m that are pixel-identical to the previous version's code replayed on the same layers, with the same numbers as below. The same run with a real token in `EARTHDATA_TOKEN` and `~/.netrc` hidden gives byte-identical files. A made-up token stops in about 3 s with the authentication error, before any download.

## Check

On 2026-10-25, in a fresh conda env built from `environment.yml` (Python 3.14.9, GDAL 3.13.3, numpy 2.5.4, h5py 3.16.0, asf_search 14.0.4), from a clone tagged `v0.1.0.post1`:

- `nisar_cv.__version__` is `0.1.0.post1`. `ruff check src`, `ruff format --check src` and `mypy src` pass. There are no tests yet.
- The README example (four GCOV granules, track 148 frame 24, the README subset) with `--crop-area true --save-gcovs true --bucket nisar-cv-test --bucket-prefix check`, against a local S3 mock (moto server on localhost, dummy keys): exit 0, 1 min 50 s, 355 MB peak memory, 8.6 GB downloaded. All nine files written (CV, CV_100m, NVALID, WATER, CROP_100m and the four layers) are in the bucket, byte for byte the same as the local files and tagged `file_type=product`.
- Products are the same as before: replaying the unchanged v0.1.0 code and this copy on the same four saved layers gives pixel-identical CV, CV_100m, NVALID, WATER and CROP_100m files with the same grids, and a plain numpy recompute of the CV from the layers matches to 7e-6 relative (3,492,860 pixels; water 38,305 pixels; crop area classes 91.6% non-crop, 7.4% crop, 1.1% water).
