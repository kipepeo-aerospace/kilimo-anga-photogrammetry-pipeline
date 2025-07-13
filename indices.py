import rasterio
import numpy as np
import os
import matplotlib
import logging

# ============================================
# Logging configuration
# ============================================

logger = logging.getLogger(__name__)

# ============================================
# Index computation functions 
# ============================================

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

