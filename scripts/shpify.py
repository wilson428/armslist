#!/usr/bin/env python

import shapefile
import csv

w = shapefile.Writer(shapefile.POINT)
w.field('ADDRESS')
w.field('GID')
w.field('TYPE','C','40')

# make .shp, .dbf, and .shx files
with open('data/files/Handguns_Sell_Ungrouped.csv', 'rU') as csvfile:
    reader = csv.reader(csvfile, delimiter=",")
    point = 0    
    for row in reader:
        if point:
            w.point(float(row[1]), float(row[0]))
            w.record(row[3], row[2], "Point")
        point += 1

w.save("shapefiles/original0")

# add .prj fiile

prj = open("shapefiles/original0.prj", "w")
epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
prj.write(epsg)
prj.close()
