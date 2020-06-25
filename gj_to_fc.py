import arcpy
from geojson_utils import GeoJSONUtils as gj
import json
import os
from pathlib import Path

arcpy.env.overwriteOutput = True

# change the search dir to whatever parent directory you want
search_dir = "C:/Temp/HE360_20200601_20200602"
gj_files = []
out_dir = "C:/Temp"  # you can also change the out dir to anything you want

gj_out = os.path.join(out_dir, "geojson_out.geojson")
gdb_out = os.path.join(out_dir, "converted_json.gdb")

out_fc_name = "gj_out"

for path in Path(search_dir).rglob('*.geojson'):
    gj_files.append(path)

for g in gj_files:
    print(g)  # get the file list

# merge to new geojson file
mg = gj.merge_geojson(gj_files)
with open(gj_out, 'w', encoding='utf-8') as f:
    json.dump(mg, f, ensure_ascii=False, indent=4)

# instantiate the utilities base object
parsed = gj(mg)

# get the data all set up
data = parsed.build_schema()

# break out the data to parts
fields = data.get('fields')
field_defs = data.get('field_defs')
rows = data.get('rows')

# make the fgdb and set it as the session workspace
gdb = gj.make_fgdb(gdb_out)
arcpy.env.Workspace = gdb

# dump it all to feature classes
out_features = parsed.make_features(gdb, out_fc_name, field_defs, rows)
print(f"Done. Stats: ")
for result in out_features:
    print(f"Feature class: {result['name']} | Built {result['rows']} rows.")
