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

def compute_indices_from_geotiff(input_path):
    with rasterio.open(input_path) as src:
        red = src.read(1).astype('float32')
        green = src.read(2).astype('float32')
        blue = src.read(3).astype('float32')
        nir = src.read(4).astype('float32')
        profile = src.profile

    ndvi = compute_index(nir, red, green, blue, mode='NDVI')
    gndvi = compute_index(nir, red, green, blue, mode='GNDVI')
    savi = compute_index(nir, red, green, blue, mode='SAVI')
    vari = compute_index(nir, red, green, blue, mode='VARI')

    base = os.path.splitext(input_path)[0]
    save_index(ndvi, profile, base + "_NDVI.tif")
    save_index(gndvi, profile, base + "_GNDVI.tif")
    save_index(savi, profile, base + "_SAVI.tif")
    save_index(vari, profile, base + "_VARI.tif")

    print("Indices saved successfully.")

# initiate usage - use the specific source for the test image
if __name__ == "__main__":
    compute_indices_from_geotiff("test_field.tif")