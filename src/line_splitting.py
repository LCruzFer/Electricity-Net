from pathlib import Path
import geopandas as gpd
import pandas as pd 
from shapely import ops, wkt 
import networkx as nx
from shapely.geometry import Point
from shapely.geometry.linestring import LineString
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
Some lines in the electricity networks contain at least one corner (or more), i.e. their linestring is defined by three points (or more). This makes problems later on. Therefore, split those lines into two (or more) and assign them an unique id each by adding '1' or '2' to the end of their id.
'''

#*#########################
#! FUNCTIONS
#*#########################
def split_line(line, id):
    '''
    Split a line that contains corners into multiple lines and assign them all a new id.
    '''
    line=lines.loc[5376, 'geometry']
    coords=[a.tolist() for a in line.coords.xy]
    c_x=coords[0]
    c_y=coords[1]
    no=len(c_x)
    new_lines={}
    for n, x, y in zip(no, c_x, c_y):
        new_lines[n]=LineString


#*#########################
#! DATA
#*#########################
lines=gpd.read_file(data_lines/'lines_all.shp')
#drop third dimension of geometry that contains no info
lines['geometry']=[ops.transform(nnt._to_2d, line) for line in lines['geometry']]