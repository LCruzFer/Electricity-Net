from pathlib import Path
import math
import numpy as np
import pandas as pd 
import geopandas as gpd 
from shapely import ops, wkt 
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString, point

#*set path 
wd=Path.cwd()
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file is used to find the intersection points of lines in an electricity network giving each point an ID and line on which they are. One point that is intersection of multiple lines will have ID|geom|(lines it lies on). 
'''

#*#########################
#! FUNCTIONS
#*#########################
def get_intersection(line1, line2): 
    '''
    Check if there is an intersection between line1 and line2, which are both shapely.LineString. 
    
    *line1, line2=shapely.LineString
    '''
    #use intersection method of LineString object
    intersect=line1.intersection(line2).wkt
    #if there is no intersection, replace returned text with NaN
    if intersect=='LINESTRING EMPTY': 
        intersect=np.nan
    #return intersection coordinates
    return intersect

def all_intersections(line_df, id_col='Line_ID', geom_col='geometry'): 
    '''
    Find all intersections of shapely LineStrings. 
    
    *lines=df containing lines
    *id_col=column name of id column
    *geom_col=column name of column containing shapely geometry defining LineString
    '''
    #set index to line id
    line_df=line_df.set_index(id_col)
    #save intersections in a dict
    intersections={}
    #for each (line_id, line) pair 
    for lid, line in zip(line_df.index, line_df[geom_col]): 
        #first, get a dataframe with all other lines except line l_id
        other_lines=line_df.drop(lid)
        #get intersection between l_id and all other lines and give it an id
        for lid2, line2 in zip(other_lines.index, other_lines[geom_col]): 
            #first find intersection 
            intersection=get_intersection(line, line2)
            #if intersection is correct type (string), save it in intersections 
            if isinstance(intersection, str): 
                intersections[(lid, lid2)]=intersection
    #return dictionary of all intersections
    return intersections

def tuple_to_list(tup):
    '''
    Turn a tuple into a list.
    
    *tuple=tuple
    '''
    ls=[x for x in tup]
    
    return ls

def unpack_lists(ls):
    '''
    Unpack a list of lists and remove duplicates.
    '''
    new_ls=[]
    for x in ls: 
        for i in x:
            if i not in new_ls:
                new_ls.append(i)
    return new_ls

#*#########################
#! DATA
#*#########################
#read in lines with transformer numbers - output from lines_transformers_matching.py
lines=pd.read_csv(data_lines/'lines_w_transformernos.csv')
lines=lines.drop(['Unnamed: 0', 'Trans_Location', 'point'], axis=1)
#turn geometry into shapely object from string 
lines['geometry']=lines['geometry'].apply(wkt.loads)
lines=lines[lines['Trans_No']==8459]

#*#########################
#! INTERSECTIONS
#*#########################
#apply functions to data
#first get all intersections
intersections=all_intersections(lines)
#then turn into a dataframe
intersections_df=pd.DataFrame.from_dict(intersections, orient='index').rename(columns={0: 'geometry'})
'''
Intersections df now contains the geometry of an intersection of 3 lines twice, one row for each pair of lines intersecting in this point. Now get a df with point|lines this point lies on, where point=intersection, and assign an id to each intersection.
'''
#make a copy of the intersections df that can be transformed 
point_df=intersections_df.copy()
#create a point id: same geometry gets the same id
point_df['p_id']=point_df.groupby(['geometry']).ngroup()+1
#reset index of this df to get a column with the line IDs
point_df=point_df.reset_index().rename(columns={'index': 'lines'})
#turn line tuples into lists
point_df['lines']=point_df['lines'].apply(tuple_to_list)
#merge lists of lines with same point id into one
point_df=point_df.groupby(['p_id', 'geometry']).agg(lambda x: x.tolist())
#unpack list of lists that is now lines column
point_df['lines']=point_df['lines'].apply(unpack_lists)
