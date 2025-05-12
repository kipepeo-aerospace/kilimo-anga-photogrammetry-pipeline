import rasterio
from rasterio.merge import merge
import glob
import os

def stitch_geotiffs(input_folder, output_path="stitched_output.tif"):
    # Find all .tif files in the folder
    tif_files = glob.glob(os.path.join(input_folder, "*.tif"))

    src_files_to_mosaic = []
    for tif in tif_files:
        src = rasterio.open(tif)
        # print(f"Opened: {tif}")
        # print(f"CRS: {src.crs}")
        # print(f"Transform: {src.transform}")
        src_files_to_mosaic.append(src)

    # Merge
    mosaic, out_transform = merge(src_files_to_mosaic)

    # Copy metadata
    out_meta = src_files_to_mosaic[0].meta.copy()  # Use metadata from the first image
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "count": mosaic.shape[0]
    })

    # Save output
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    print(f"Stitched GeoTIFF saved as: {output_path}")

# main
if __name__ == "__main__":
    stitch_geotiffs("../converted_tiffs")
