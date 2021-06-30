from os import close
from pathlib import Path
import numpy as np
import pandas as pd 
import geopandas as gpd
import networkx as nx
from shapely import ops, wkt
import shapely
from shapely.geometry import Point, LineString, MultiPoint
from shapely.geometry.multipolygon import MultiPolygon

#*set path 
wd=Path.cwd()
data_lines=wd/'data'/'lines'
data_fieldwork=wd/'data'/'Kakamega Fieldwork Shapefiles'

#*#########################
#! FUNCTIONS
#*#########################
def _to_2d(x, y, z):
    '''
    Helper function do drop feature dimension from shapely geometry objects. 
    Apply to an object in the following way: 
    new_shape = shapely.ops.transform(_to_2d, shape)
    
    Taken from: https://github.com/Toblerity/Shapely/issues/709
    '''
    return tuple(filter(None, [x, y]))

def get_closest_id(p, points, points_cols): 
    '''
    For p find the id of the point in points that is closest to the point. 
    
    *point=shapely.geometry.Point
    *points=gpd df containing id and geometry of points
    *points_cols=tuple of (id, geometry) column names in points
    '''
    #unpack column names tuple 
    id_points=points_cols[0]
    geom_points=points_cols[1]
    if 'geometry' not in points.columns: 
        raise KeyError('No geometry column in points df')
    #calculate distance to all points
    distances={px: p.distance(point) for px, point in zip(points[id_points], points[geom_points])}
    #get line that has shortest distance to point
    closest=min(distances, key=distances.get)
    
    return closest

def find_closest(points, other_points, cols_points, cols_otherpoints): 
    '''
    Given point from poitns find the closest point among other_points, save its index and itself. 

    *points=gpd df containing points to find closest line to and corresponding id
    *other_points=gpd df with other points to match points to and corresponding id of other_points
    *cols_points=tuple of (id, geometry) column names of points 
    *cols_otherpoints=tuple of (id, geometry) column names of other_points 
    '''
    #unpack column names first 
    id_points=cols_points[0]
    geom_points=cols_points[1]
    id_otherpoints=cols_otherpoints[0]
    geom_otherpoints=cols_otherpoints[1]
    #save in a dictionary of structure {point id: (index of closest point, closest point)}
    #loop over all points and their id in points 
    all_closest_points={}
    for px, point in zip(points[id_points], points[geom_points]):
        #get id of the closest point in other_points
        closest_id=get_closest_id(point, other_points, points_cols=cols_otherpoints)
        #get the actual point
        closest_point=other_points[other_points[id_otherpoints]==closest_id][geom_otherpoints].item()
        #save both as tuple in dict with key being px
        all_closest_points[px]=(closest_id, closest_point)
    
    return all_closest_points