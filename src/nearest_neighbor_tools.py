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
from shapely.geometry.polygon import LinearRing

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



class matching_and_distances:
    #class for matching points with lines and getting distances between them 
    def __init__(self, p1, p2, cols_p1, cols_p2):
        '''
        *p1=df with id and geometry column 
        *p2=df with id and geometry column 
        #!IF LINES AND POINTS MATCHED p1 IS POINTS DF, p2 IS LINE DF
        *cols_p1=column names of id and geometry column in p1 as tuple
        *cols_p2=column names of id and geometry column in p2 as tuple
        '''
        self.p1=p1.set_index(cols_p1[0])
        self.p2=p2.set_index(cols_p2[0])
        self.p1_geom=self.p1[cols_p1[1]]
        self.p2_geom=self.p2[cols_p2[1]]
        self.match_dict=self.get_closest()
        
    def get_closest(self):
        '''
        For each point in p1 find the id of closest point/line (using point in comments but can also be a line) in p2. 
        Automatically executed and saved as self when initializing class as needed for all further methods.
        '''
        #loop over the id, geom pair of p1 and look for closest point in p2
        #save results in a dictionary with {id1: closest of id2}
        final_dict={}
        for p, geom in zip(self.p1.index, self.p1_geom):
            #calculate distance between p and each point in p2 and save in a dictionary
            distances={p2_id: geom.distance(p2_geom) for p2_id, p2_geom in zip(self.p2.index, self.p2_geom)}
            #find the key of this dict that has smallest value -> id of closest point 
            closest=min(distances, key=distances.get)
            #then save point id and id of closest point in final dict
            final_dict[p]=closest
            
        return final_dict

    def hh_line_distance(self):
        '''
        Using results from get_closest() find distance between the points that are closest.
        
        *match_dict=dict returnd from get_closest() where key is id of a point in p1 and val is id of the point in p2 closest to it
        '''
        #access a (key, val) pair in match_dict 
        distance_dict={}
        for key, val in self.match_dict.items():
            #retrieve the geom of key and val respectively
            geom_key=self.p1_geom[key]
            geom_val=self.p2_geom[val]
            #calculate distance between these two
            distance=geom_key.distance(geom_val)
            #and save in dictionary 
            distance_dict[(key, val)]=distance

        return distance_dict

    def closest_points(self):
        '''
        #!NEEDED ONLY FOR POINT-LINE MATCHING
        Using the results from get_closest() find the closest point on line segment (vals of match_dict) to point (key of match_dict) and assign it the id of the point (key of match_dict). 
        
        *match_dict=dict returnd from get_closest() where key is id of a point in p1 and val is id of the point in p2 closest to it
        '''
        closest_p_dict={}
        #for each (key, val) pair in match_dict 
        for key, val in self.match_dict.items(): 
            #retrieve the geometry of point (key) and line (val)
            p_geom=self.p1_geom[key]
            line_geom=self.p2_geom[val]
            #apply shapely.ops.nearest points 
            #returns a tuple with nearest point on both geometries 
            #want point on line, i.e. second element of tuple and return wkt version
            closest_on_line=ops.nearest_points(p_geom, line_geom)[1].wkt
            #assign the point id to this point and save in dictionary
            closest_p_dict[key]=closest_on_line

        return closest_p_dict

    def closest_points_df(self):
        '''
        Use closest_points() and create a df with point_id|line_id|closest point on line using the self.match_dict().
        '''
        #get closest points (see closest_points() description)
        closest_p=self.closest_points()
        #turn dict into a df with index being point id (key of closest_p)
        #rename the columns to appropriate name
        closest_df=pd.DataFrame.from_dict(closest_p, orient='index').rename(columns={0:'closest_point'})
        #turn match_dict into a dataframe as well, reset index and rename columns
        match_df=pd.DataFrame.from_dict(self.match_dict, orient='index').rename(columns={0: 'lines'})
        #then merge based on point_id 
        final_df=pd.merge(closest_df, match_df, on=closest_df.index)
        #rename key_0 columns
        final_df=final_df.rename(columns={'key_0': 'p_id'})
        
        return final_df
