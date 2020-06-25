"""
Rudimentary GeoJSON parser to take single and multi-geometry GeoJSON and convert it to an Esri file geodatabase.
Author: Eric Eagle | eric.c.eagle.civ@mail.mil
"""

import arcpy
from collections import OrderedDict
from datetime import datetime
import json
import os


class GeoJSONUtils:

    def __init__(self, json_in):
        """
        Constructor.

        :param json_in: input valid json
        :type json_in: str
        """
        self.json_in = json_in
        self.sr = arcpy.SpatialReference(4326)

    def get_json(self):
        """
        Class instance getter.

        :returns: str
        """
        return self.json_in

    def build_schema(self):
        """
        Returns a dictionary containing a field map (list of field headings), field definitions (schema)
        and rows (Point, Line, Polygon) for building out feature classes.

        :returns: dict
        """
        field_defs = []
        fields = []
        point_rows = []
        line_rows = []
        polygon_rows = []
        for i in self.json_in['features']:  # first iterate through it all and get all the fields
            props = i.get('properties')

            for k, v in props.items():
                if k not in fields:
                    fields.append(k)

        for i in self.json_in['features']:  # now fill in any props that any features are missing, and sort them all
            geom = i['geometry']
            props = i['properties']
            for f in fields:
                if f not in props.keys():
                    props[f] = ''
            props = OrderedDict(sorted(props.items()))

            for k, v in props.items():
                schema_row = [k, "TEXT", k.replace('_', ' '), 256]
                if schema_row not in field_defs:
                    field_defs.append(schema_row)
            row = [str(v) for k, v in sorted(props.items())]  # coerce everything to str cause this stuff is a mess
            parsed_geom = GeoJSONUtils.parse_geometry(geom)
            geotype = parsed_geom['type']
            egeom = parsed_geom['esri_geom']

            if geotype == "POINT":
                row.insert(0, egeom)
                print(row)
                point_rows.append(row)
            elif geotype == "POLYLINE":
                row.insert(0, egeom)
                print(row)
                line_rows.append(row)
            else:
                row.insert(0, egeom)
                print(row)
                polygon_rows.append(row)

        return {
            "fields": fields,
            "field_defs": field_defs,
            "rows": [point_rows, line_rows, polygon_rows]
        }

    @staticmethod
    def parse_geometry(gj_geom):
        """
        Grabs GeoJSON geometry, returns an Esri geometry object and its description in a dictionary

        :param gj_geom: GeoJSON ['geometry'] entry
        :returns: dict
        """
        try:
            esri_geom = arcpy.AsShape(gj_geom)
            if gj_geom['type'] == 'Point':
                return {
                    "type": "POINT",
                    "esri_geom": esri_geom
                }
            elif gj_geom['type'] in ['LineString', 'MultiLineString']:
                return {
                    "type": "POLYLINE",
                    "esri_geom": esri_geom
                }
            elif gj_geom['type'] in ['Polygon', 'MultiPolygon']:
                return {
                    "type": "POLYGON",
                    "esri_geom": esri_geom
                }
            else:
                print("Not a Point, Line or Polygon feature.")
                return False
        except KeyError as ke:
            print(f"Error: {ke}.  Malformed JSON. Could not parse.")
            return False

    @staticmethod
    def merge_geojson(files):
        """
        Takes geojson and pushes it all together.

        :param files: list of geojson files.
        :type files: list
        """
        gj_list = []
        for f in files:
            with open(f, 'r') as geojson:
                gj = json.load(geojson)
                gj_list.append(gj)
        base_gj = gj_list[0]
        for feat in gj_list[1:]:
            for f in feat['features']:
                base_gj['features'].append(f)
        return base_gj

    @staticmethod
    def timestamp():
        """
        Gets current time string for uniquely named feature classes (helps to avoid schema locks).

        :returns: str
        """
        return datetime.now().strftime("%Y%m%dT%H%M%S")

    @staticmethod
    def make_fgdb(gdb):
        """
        Makes a file geodatabase if it doesn't already exist.

        :param gdb: input FGDB object
        :type gdb: file
        :returns: file
        """
        if not arcpy.Exists(gdb):
            gdb_path, gdb_name = os.path.split(gdb)
            return arcpy.CreateFileGDB_management(gdb_path, gdb_name)
        else:
            return gdb

    def make_fc(self, gdb, fc_name, fields, rows, geotype, geotoken):
        """
        Reusable logic for building the feature class.

        :param gdb: file geodatabase to store the output in
        :param fc_name: name of feature class
        :param fields: list of field headings
        :param rows: nested list of (potentially) point, line and polygon rows
        :param geotype: Esri-recognized geometric type designator (str)
        :param geotoken: Esri geometric token
        """
        if not arcpy.Exists(fc_name):
            fc = arcpy.CreateFeatureclass_management(gdb, fc_name, geotype, spatial_reference=self.sr)
            # print(fields)
            arcpy.AddFields_management(fc, fields)
            field_list = sorted(GeoJSONUtils.build_schema(self).get('fields'))
            field_list.insert(0, geotoken)
            field_map = tuple(field_list)
            # print(field_map)
            with arcpy.da.InsertCursor(fc, field_map) as cursor:
                for row in rows:
                    try:
                        cursor.insertRow(row)
                    except RuntimeError as re:
                        print(f"Problem inserting row, {re}")

            fc_stats = {
                "name": fc_name,
                "rows": len(rows)
            }
            return fc_stats

    def make_features(self, gdb, fc_name, fields, rows):
        """
        Orchestration method that checks the rows and calls the feature class builder.

        :param gdb: output geodatabase
        :param fc_name: feature class prefix
        :param fields: the fields to be matched against
        :param rows: the rows to be matched up with the fields
        """
        point_geotoken = "SHAPE@XY"
        other_geotoken = "SHAPE@"
        now = GeoJSONUtils.timestamp()
        stats = []

        if len(rows[0]) > 0:
            point_rows = rows[0]
            point_fc_name = fc_name + now + '_p'
            point_fc = GeoJSONUtils.make_fc(self, gdb, point_fc_name, fields, point_rows, "POINT", point_geotoken)
            stats.append(point_fc)
        if len(rows[1]) > 0:
            line_rows = rows[1]
            line_fc_name = fc_name + now + '_l'
            line_fc = GeoJSONUtils.make_fc(self, gdb, line_fc_name, fields, line_rows, "POLYLINE", other_geotoken)
            stats.append(line_fc)
        if len(rows[2]) > 0:
            poly_rows = rows[2]
            poly_fc_name = fc_name + now + '_a'
            poly_fc = GeoJSONUtils.make_fc(self, gdb, poly_fc_name, fields, poly_rows, "POLYGON", other_geotoken)
            stats.append(poly_fc)
        return stats
