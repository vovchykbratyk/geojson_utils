from datetime import datetime
import geopandas as gpd
import json
import os
from pathlib import Path


# methods

def merge_geojson(files):
    """
    Merges multiple files containing valid geojson into a single object
    :param files: list of files
    :type files: list
    :return: json object
    """
    geojson_list = []  # will hold the json objects
    for f in files:
        with open(f, 'r') as geojson:
            gj = json.load(geojson)  # load each file's geojson content...
            geojson_list.append(gj)  # ...and append it to the geojson_list till there are no more files
    base_gj = geojson_list[0]  # get first json object and use as the wrapper or base into which all other features will be appended
    for feat in geojson_list[1:]:  # start the loop at the second position of the list...
        for f in feat['features']:  # ...get each feature from each parent json object...
            base_gj['features'].append(f)  # ...and append it to the base geojson object
    return base_gj


def timestamp():
    """
    Gets current time stamp for unique file names
    :return: str
    """
    return datetime.now().strftime('%Y%m%dT%H%M%S')


# do the work

## parameters
search_path = "C:/Temp/HE360_20200601_20200602"  # path to look in
gjl = []  # list object that will hold the file references
out_path = "C:/Temp"  # where to write the output geopackage

## look in the search path and get the list of geojson files
for path in Path(search_path).rglob('*.geojson'):
    gjl.append(path)

## feed the list in to the merging function
mg = merge_geojson(gjl)

## read it in to a geopandas GeoDataFrame using the from_features() method
gdf = gpd.GeoDataFrame.from_features(mg['features'])

## set up the output filename
out_fn = "merged_" + timestamp() + ".gpkg"
file_out = os.path.join(out_path, out_fn)

## And now write it to a geopackage
gdf.to_file(file_out, driver="GPKG")

## You can print the geodataframe if you want just to see if it all worked
print(gdf)
