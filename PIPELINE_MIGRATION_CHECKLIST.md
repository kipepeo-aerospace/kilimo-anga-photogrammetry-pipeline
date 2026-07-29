# Pipeline Repo — Phase 2: Migration & Rewrite

**Repo:** Pipeline (photogrammetry engine) | **Branch:** `gcp-migration` | **Region:** `europe-west1`
**Prerequisite:** `INFRA_SETUP_CHECKLIST.md` must be fully complete (buckets, Firestore, Artifact Registry, `angacloud-pipeline-sa` all exist) before starting this.

> Most of this phase is code work — there's no console equivalent for editing Python files. Console steps apply where noted (Artifact Registry browsing, Cloud Run Job creation).

---

## 1. Replace `azure_blob.py` with `gcs_storage.py`

- [ ] Rename `azure_blob.py` → `gcs_storage.py`.
- [ ] Remove `azure-storage-blob` from `requirements.txt`, add `google-cloud-storage`.
- [ ] Update every function to use the `google-cloud-storage` client and `gs://` URIs instead of Azure blob container references — **keep the exact same function signatures** (same function names, same arguments) so `main.py` doesn't need structural changes, only the import line.
- [ ] Map bucket usage: raw images → `angastack-raw-images`, converted TIFFs → `angastack-tiffs`, orthomosaic → `angastack-mosaics`, NDVI/VARI outputs → `angastack-index-maps`.
- [ ] Confirm path pattern used when reading/writing: `{user_id}/{farm_id}/{job_id}/filename`.

---

## 2. Rewrite `indices.py` — add quantitative stats extraction

This is the core gap-fix: the current version only produces visual NDVI/VARI maps. It needs to also compute and persist numbers.

- [ ] Using `numpy`/`rasterio`, compute alongside the existing raster generation:
  - NDVI: `mean`, `min`, `max`, `std_dev`.
  - NDVI `stress_percentage` — % of pixels with NDVI < 0.3.
  - NDVI `healthy_percentage` — % of pixels with NDVI > 0.6.
  - VARI: `mean`, `min`, `max`.
- [ ] Compute zone breakdown using the threshold bands:
  - `< 0.3` → `stressed` (high stress level)
  - `0.3 – 0.6` → `moderate`
  - `> 0.6` → `healthy` (low stress level)
  - Each zone object: `zone_id`, `ndvi_mean`, `stress_level`, `pixel_count`.
- [ ] Construct the stats JSON payload matching the Firestore job schema:
  ```
  stats.ndvi.mean / min / max / std_dev / stress_percentage / healthy_percentage
  stats.vari.mean / min / max
  stats.zone_breakdown: [ { zone_id, ndvi_mean, stress_level, pixel_count }, ... ]
  ```
- [ ] Write this payload directly to the Firestore document at `users/{user_id}/farms/{farm_id}/jobs/{job_id}` using the `google-cloud-firestore` client (added in the next section) — don't route this through the backend API, the pipeline writes directly.

---

## 3. Refactor `main.py` orchestration

- [ ] Update imports: replace `azure_blob` with `gcs_storage`.
- [ ] Add `google-cloud-firestore` to `requirements.txt` and initialise a Firestore client at startup.
- [ ] Reconfigure CLI/env-var input parameters to match what Cloud Run Jobs will pass in: `USER_ID`, `FARM_ID`, `JOB_ID` (these arrive as environment variable overrides at job execution time, set by the backend when it triggers the job — see Backend checklist).
- [ ] After the pipeline finishes successfully, update the Firestore job document's `status` field to `"complete"` directly from `main.py` — this fully decouples pipeline completion from the backend API (the backend just watches Firestore rather than being told directly by the pipeline).
- [ ] Set `completed_at` timestamp on the same write.
- [ ] On failure, catch the exception and write `status: "failed"` with an error message field, so failures are visible in Firestore rather than silently disappearing.

---

## 4. Dockerize

- [ ] Update the Dockerfile: remove any `azure-*` SDK install lines, add `google-cloud-storage` and `google-cloud-firestore` to the installed dependencies (these should already be picked up if they're in `requirements.txt`, but double-check the Dockerfile doesn't pin an old `requirements-azure.txt` or similar).
- [ ] Build and tag the image locally to test before pushing:
  ```bash
  docker build -t europe-west1-docker.pkg.dev/angastack-platform/angastack-registry/pipeline:v1 .
  ```

---

## 5. Push to Artifact Registry

- [ ] Confirm you've run `gcloud auth configure-docker europe-west1-docker.pkg.dev` once on this machine (done in the Infra checklist — re-run if you're on a different machine).
- [ ] Push:
  ```bash
  docker push europe-west1-docker.pkg.dev/angastack-platform/angastack-registry/pipeline:v1
  ```
- [ ] Verify it landed:
  - Console: **Artifact Registry → angastack-registry** → you should see a `pipeline` image with tag `v1`.

> ⚠️ Note: an earlier draft of this doc referenced the path `europe-west1-docker.pkg.dev/kilimo-anga-v1/kilimo-anga/pipeline:v1` — that's a stale project/repo name from before the project was renamed to `angastack-platform`. Use the path above, not that one.

---

## 6. Create the Cloud Run Job

- [ ] Console: **Cloud Run → Jobs → Create Job**.
  - Container image URL: browse to Artifact Registry → `angastack-registry` → `pipeline` → `v1` (or paste the full path from above).
  - Job name: `angacloud-pipeline-job`.
  - Region: `europe-west1`.
  - CPU: `2`.
  - Memory: `4Gi`.
  - Task timeout: `3600` seconds.
  - Number of retries: `1`.
  - Service account: `angacloud-pipeline-sa` (created in Infra checklist).
  - Leave environment variables as defaults for now — `USER_ID`/`FARM_ID`/`JOB_ID` get set per-execution when the backend triggers a run, not baked into the job definition.
- [ ] CLI equivalent:
  ```bash
  gcloud run jobs create angacloud-pipeline-job \
    --image=europe-west1-docker.pkg.dev/angastack-platform/angastack-registry/pipeline:v1 \
    --cpu=2 \
    --memory=4Gi \
    --task-timeout=3600s \
    --max-retries=1 \
    --region=europe-west1 \
    --service-account=angacloud-pipeline-sa@angastack-platform.iam.gserviceaccount.com
  ```

---

## 7. Test end-to-end

- [ ] Manually trigger one execution with test `USER_ID`/`FARM_ID`/`JOB_ID` values pointing at a small test image set already sitting in `angastack-raw-images`:
  - Console: **Cloud Run → Jobs → angacloud-pipeline-job → Execute** → override environment variables for this run only.
  - CLI:
    ```bash
    gcloud run jobs execute angacloud-pipeline-job \
      --region=europe-west1 \
      --update-env-vars=USER_ID=test-user,FARM_ID=test-farm,JOB_ID=test-job
    ```
- [ ] Verify: orthomosaic and index maps land in `angastack-mosaics` / `angastack-index-maps`, `stats` JSON appears on the Firestore job document, and `status` flips to `complete`.

---

## Phase 2 completion checkpoint

- [ ] Pipeline runs as a Cloud Run Job execution, pulls raw images from GCS, writes outputs to GCS.
- [ ] Numerical stats JSON (NDVI/VARI + zone breakdown) is written directly to the Firestore job document.
- [ ] Job status is set to `complete` (or `failed`) directly by the pipeline, with no dependency on the backend being called back.
