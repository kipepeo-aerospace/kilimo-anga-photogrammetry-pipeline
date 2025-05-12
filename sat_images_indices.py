import rasterio
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib import cm

def compute_index(nir, red, green, blue, mode='NDVI', L=0.5):
    with np.errstate(divide='ignore', invalid='ignore'):
        if mode == 'NDVI':
            result = (nir - red) / (nir + red)
        elif mode == 'GNDVI':
            result = (nir - green) / (nir + green)
        elif mode == 'SAVI':
            result = ((nir - red) / (nir + red + L)) * (1 + L)
        elif mode == 'VARI':
            result = ((green - red) / (green + red - blue))
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    result = np.clip(result, -1, 1)
    return result.astype(np.float32)

def save_index(index_array, profile, output_path):
    # Scale NDVI [-1, 1] → 0–255
    scaled = ((index_array + 1) * 127.5).astype('uint8')
    scaled = np.clip(scaled, 0, 255)

    # Generate red-to-green colormap (256 values)
    cmap = cm.get_cmap('RdYlGn', 256)
    colormap = {i: tuple((np.array(cmap(i))[:3] * 255).astype(int)) for i in range(256)}

    # Save with color map
    profile.update(dtype=rasterio.uint8, count=1)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(scaled, 1)
        dst.write_colormap(1, colormap)

def compute_indices_from_separate_bands(red_path, green_path, blue_path, nir_path):
    # Read each band as separate images
    with rasterio.open(red_path) as red_src:
        red = red_src.read(1).astype('float32')
        profile = red_src.profile

    with rasterio.open(green_path) as green_src:
        green = green_src.read(1).astype('float32')

    with rasterio.open(blue_path) as blue_src:
        blue = blue_src.read(1).astype('float32')

    with rasterio.open(nir_path) as nir_src:
        nir = nir_src.read(1).astype('float32')

    # Compute indices
    ndvi = compute_index(nir, red, green, blue, mode='NDVI')
    #gndvi = compute_index(nir, red, green, blue, mode='GNDVI')
    #savi = compute_index(nir, red, green, blue, mode='SAVI')
    #vari = compute_index(nir, red, green, blue, mode='VARI')

    # Save results

    output_dir = "../output/"
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(red_path)[0]
    save_index(ndvi, profile, os.path.join(output_dir, "_NDVI.tif"))
    #save_index(gndvi, profile, base + "_GNDVI.tif")
    #save_index(savi, profile, base + "_SAVI.tif")
    #save_index(vari, profile, base + "_VARI.tif")

    print("Indices saved successfully.")

# initiate usage
if __name__ == "__main__":
    # these paths are generic to my computer's directory - adjust accordingly
    red_image = "../sat_images/B04.jp2"
    green_image = "../sat_images/B03.jp2"
    blue_image = "../sat_images/B02.jp2"
    nir_image = "../sat_images/B08.jp2"
    
    compute_indices_from_separate_bands(red_image, green_image, blue_image, nir_image)
