import rasterio
import numpy as np
import os
import matplotlib
import logging
from PIL import Image

# ============================================
# Logging configuration
# ============================================

logger = logging.getLogger(__name__)

# ============================================
# Index computation functions 
# ============================================

def convert_index_tif_to_jpg(tif_path, jpg_path=None):
    """Converts a single-band color-mapped GeoTIFF to JPG with colors preserved."""
    if jpg_path is None:
        jpg_path = os.path.splitext(tif_path)[0] + '.jpg'

    with rasterio.open(tif_path) as src:
        count = src.count

        if count == 1:
            array = src.read(1)

            # Check if it has a colormap
            try:
                cmap = src.colormap(1)
            except ValueError:
                cmap = None

            if cmap:
                # Apply colormap
                rgb_array = np.zeros((array.shape[0], array.shape[1], 3), dtype=np.uint8)
                for val, color in cmap.items():
                    rgb_array[array == val] = color[:3]  # drop alpha if present
            else:
                # No colormap → scale to grayscale
                arr_min, arr_max = np.nanmin(array), np.nanmax(array)
                scaled = ((array - arr_min) / (arr_max - arr_min) * 255).astype(np.uint8)
                rgb_array = np.stack([scaled] * 3, axis=-1)

        elif count >= 3:
            # RGB or RGBA TIFF
            rgb_array = np.zeros((src.height, src.width, 3), dtype=np.uint8)
            for i in range(3):
                band = src.read(i + 1)
                rgb_array[..., i] = np.clip(band, 0, 255).astype(np.uint8)

        else:
            raise ValueError(f"Unsupported TIFF format: {count} bands")

    Image.fromarray(rgb_array).save(jpg_path, "JPEG", quality=90)
    return jpg_path

def save_index(index_array, profile, output_path):
    # Scale NDVI [-1, 1] → 0–255

    scaled = 255 * (index_array - np.nanmin(index_array)) / (np.nanmax(index_array) - np.nanmin(index_array))
    scaled = scaled.astype('uint8')
    scaled[np.isnan(index_array)] = 0


    # Generate red-to-green colormap (256 values)
    cmap = matplotlib.colormaps['RdYlGn'].resampled(256)
    colormap = {i: tuple((np.array(cmap(i))[:3] * 255).astype(int)) for i in range(256)}
    colormap[0] = (0, 0, 0)  # black for invalid
    # Save with color map
    profile.update(dtype=rasterio.uint8, count=1)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(scaled, 1)
        dst.write_colormap(1, colormap)

def compute_vari(image_path, output_dir):
    with rasterio.open(image_path) as src:
        red = src.read(1).astype('float32')
        green = src.read(2).astype('float32')
        blue = src.read(3).astype('float32')      
        profile = src.profile
    
    valid_mask = (red > 0) & (green > 0) & (blue > 0)

    red[~valid_mask] = np.nan
    green[~valid_mask] = np.nan
    blue[~valid_mask] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        vari = ((green - red) / (green + red - blue))
    
    vari = np.clip(vari, -1, 1)
    vari = vari.astype(np.float32)
    
    # Extract the base filename without extension
    base_name = os.path.splitext(os.path.basename(image_path))[0]

    # Create full output paths using output_dir
    tif_output_path = os.path.join(output_dir, f"{base_name}_VARI.tif")

    # Save the outputs
    save_index(vari, profile, tif_output_path)

    logger.info("VARI saved successfully.")

def compute_ndvi(image_path, output_dir):
    with rasterio.open(image_path) as src:
        nir = src.read(4).astype('float32')   # NIR band
        red = src.read(1).astype('float32')   # Red band
        profile = src.profile

    valid_mask = (nir > 0) & (red > 0)
    nir[~valid_mask] = np.nan
    red[~valid_mask] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi = (nir - red) / (nir + red)

    ndvi = np.clip(ndvi, -1, 1).astype(np.float32)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    tif_output_path = os.path.join(output_dir, f"{base_name}_NDVI.tif")
    save_index(ndvi, profile, tif_output_path)
    logger.info("NDVI saved successfully.")

def compute_gndvi(image_path, output_dir):
    with rasterio.open(image_path) as src:
        nir = src.read(4).astype('float32')   # NIR band
        green = src.read(2).astype('float32') # Green band
        profile = src.profile

    valid_mask = (nir > 0) & (green > 0)
    nir[~valid_mask] = np.nan
    green[~valid_mask] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        gndvi = (nir - green) / (nir + green)

    gndvi = np.clip(gndvi, -1, 1).astype(np.float32)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    tif_output_path = os.path.join(output_dir, f"{base_name}_GNDVI.tif")
    save_index(gndvi, profile, tif_output_path)
    logger.info("GNDVI saved successfully.")

def compute_savi(image_path, output_dir, L=0.5):
    with rasterio.open(image_path) as src:
        nir = src.read(4).astype('float32')   # NIR band
        red = src.read(1).astype('float32')   # Red band
        profile = src.profile

    valid_mask = (nir > 0) & (red > 0)
    nir[~valid_mask] = np.nan
    red[~valid_mask] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        savi = ((nir - red) / (nir + red + L)) * (1 + L)

    savi = np.clip(savi, -1, 1).astype(np.float32)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    tif_output_path = os.path.join(output_dir, f"{base_name}_SAVI.tif")
    save_index(savi, profile, tif_output_path)
    logger.info("SAVI saved successfully.")
