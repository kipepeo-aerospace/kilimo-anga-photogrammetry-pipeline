import rasterio

with rasterio.open("test_field.tif") as src:
    print("Band count:", src.count)
    print("Band descriptions:", src.descriptions)
    print("Shape:", src.read(1).shape)
    print("Dtype:", src.dtypes)
    print("Max pixel in band 1:", src.read(1).max())
