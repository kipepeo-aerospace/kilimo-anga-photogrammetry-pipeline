import os
import subprocess
from PIL import Image
from osgeo import gdal, osr
import re
import subprocess
import shutil


def dms_to_dd(dms_str):
    # Example input: 1 deg 15' 32.45" S
    match = re.match(r"(\d+)\D+(\d+)\D+([\d.]+)\"?\s*([NSEW])", dms_str)
    if not match:
        return None
    degrees, minutes, seconds, direction = match.groups()
    dd = float(degrees) + float(minutes)/60 + float(seconds)/3600
    if direction in ['S', 'W']:
        dd *= -1
    return dd

def clear_folder(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    else:
        os.makedirs(folder_path)

def convert_jpeg_to_geotiff(jpeg_path, output_path):
    cmd = ['exiftool', '-GPSLatitude', '-GPSLongitude', jpeg_path]
    output = subprocess.check_output(cmd).decode()
    lat = lon = None

    for line in output.splitlines():
        if "GPS Latitude" in line:
            lat = dms_to_dd(line.split(":")[1].strip())
        if "GPS Longitude" in line:
            lon = dms_to_dd(line.split(":")[1].strip())

    if lat is None or lon is None:
        print(f"Skipping {jpeg_path}: No GPS metadata found.")
        return

    # Open original JPEG to get size
    ds = gdal.Open(jpeg_path)
    width = ds.RasterXSize
    height = ds.RasterYSize
    bands = ds.RasterCount

    # Calculate pixel size in degrees using GSD (Ground Sampling Distance)
    # Convert GSD (meters per pixel) to degrees
    pixel_size = gsd / 111320  # Rough approximation of 1 degree = 111320 meters at the equator


    # Top-left coordinates
    top_left_x = lon - (width / 2) * pixel_size
    top_left_y = lat + (height / 2) * pixel_size

    # Define geotransform
    geotransform = (top_left_x, pixel_size, 0, top_left_y, 0, -pixel_size)

    # Create GeoTIFF with georeferencing
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, width, height, bands, gdal.GDT_Byte)

    out_ds.SetGeoTransform(geotransform)

    # Set projection to WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    out_ds.SetProjection(srs.ExportToWkt())

    # Copy pixel data
    for i in range(1, bands + 1):
        out_ds.GetRasterBand(i).WriteRaster(0, 0, width, height, ds.GetRasterBand(i).ReadRaster())

    out_ds.FlushCache()
    print(f"Converted: {jpeg_path} → {output_path}")



if __name__ == "__main__":
    input_folder = "../aerial_images"
    output_folder = "../converted_tiffs"
    clear_folder(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    gsd = 0.00114 

    for filename in os.listdir(input_folder):
        if filename.lower().endswith((".jpg", ".jpeg")):
            input_path = os.path.join(input_folder, filename)
            output_filename = os.path.splitext(filename)[0] + ".tif"
            output_path = os.path.join(output_folder, output_filename)
            convert_jpeg_to_geotiff(input_path, output_path)