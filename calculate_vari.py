import rasterio
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib
import pandas as pd

def save_index(index_array, profile, output_path):
    # Scale NDVI [-1, 1] → 0–255
    array_max = np.nanmax(index_array)
    array_min = np.nanmin(index_array)
    print(f"Max: {array_max}, Min: {array_min}")

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

def save_raw_csv(index_array, output_path):
    flat = index_array[~np.isnan(index_array)].flatten()
    df = pd.DataFrame(flat, columns=["Index_Value"])
    df.to_csv(output_path, index=False)

def compute_vari(input_path):
    with rasterio.open(input_path) as src:
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
    

    base = os.path.splitext(input_path)[0]
    save_index(vari, profile, base + "_VARI.tif")
    save_raw_csv(vari, base + "_VARI.csv")
    print("VARI saved successfully.")



# initiate usage - use the specific source for the test image
if __name__ == "__main__":
    compute_vari("output/greenwood_mosaic.tif")