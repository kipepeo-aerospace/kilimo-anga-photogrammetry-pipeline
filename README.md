# 🌾 Kilimo Anga Photogrammetry Pipeline

This is a containerized drone image processing pipeline developed by **Kipepeo Aerospace Ltd.** under the **Kilimo Anga** initiative. The pipeline is designed to automate the generation of orthomosaics and vegetation indices (e.g., NDVI) from drone-captured multispectral imagery, enabling fast, scalable analysis for precision agriculture.

---

## 🛠 Features

* 📷 Converts raw `.JPG` images to `.TIF` format using **Pillow**
* 🧩 Stitches converted `.TIF` images into a georeferenced mosaic using **Rasterio**
* 🌿 Computes vegetation indices (e.g., NDVI) from stitched mosaics
* 📦 Fully containerized with **Docker**, enabling cloud-native deployments
* ☁️ Integrated with **Azure Blob Storage** for both input and output handling
* 🔁 Pipeline is structured in two phases for easy integration with a web frontend

---

## 📂 Project Structure

```
photogrammetry-pipeline/
│
├── stitching.py                # Step 1: Convert .JPG to .TIFF
├── stitching.py                # Step 2: Stitch TIFFs into orthomosaic
├── indices.py                  # Step 3: Generate vegetation indices (e.g., NDVI)
├── main.py                     # Main script to run the full pipeline
├── azure_blob.py               # Contains azure blob functions
│
├── Dockerfile                  # Lightweight Python + GDAL container setup
├── .dockerignore               # Things to ignore in the docker build
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (hidden from public)
└── README.md                   # This file
```

---

## 📦 Docker Build & Run

### Build Image

```bash
docker build -t photogrammetry-pipeline .
```

### Run Container

```bash
docker run --env-file .env photogrammetry-pipeline
```

---

## 🛰 Pipeline Flow

1. **Download Phase**:

   * Downloads raw `.JPG` images from `raw-images/<CLIENT>/<FIELD_DIR>/` in Azure Blob Storage.

2. **Conversion Phase**:

   * Converts `.JPG` files to `.TIF` format using Pillow.

3. **Mosaicking Phase**:

   * Merges all `.TIF` images into a single orthomosaic using Rasterio.

4. **Index Phase**:

   * Computes vegetation indices and saves result as GeoTIFF.

5. **Upload Phase**:

   * Uploads final outputs to `index-maps/<CLIENT>/<FIELD_DIR>/` in Azure Blob Storage.

---

## 📥 Sample Input Folder Structure on Blob

```
raw-images/
└──raw-images/
   └── client-001/
      └── field-001/
        ├── IMG_001.JPG
        ├── IMG_002.JPG
        └── ...
```

## 📤 Output Folder Structure on Blob

```
index-maps/
└── client-001/
    └── field-001/
        ├── mosaic.tif
        ├── ndvi.tif
        └── ...
```

---

## 🧪 Notes

* The image capture setup uses a **Raspberry Pi 4** running a custom **64MP quad-camera** with R/G/B/NIR filters.
* Image metadata may be used for further geolocation correction.
* Vegetation index support can be extended beyond NDVI.

---

## 📌 Next Steps

* Integrate full blob-aware CLI controls
* Add support for other indices (GNDVI, SAVI, etc.)
* Webhook support for async triggering from a frontend
* CI/CD with Azure Pipelines (in progress)

---

## 🧑‍💻 Maintainers

* **Brian Lembuss** – Aerospace Engineering, Software & Systems Architect
* **Kipepeo Aerospace Ltd.** under the **Kilimo Anga** initiative

---

## 📜 License

Private — internal use by Kipepeo Aerospace Ltd. For commercial licensing, contact us directly.

---
