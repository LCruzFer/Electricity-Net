from pathlib import Path
import math
import numpy as np
import pandas as pd 
import geopandas as gpd 
from shapely import ops, wkt 
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString, point

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
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
    #if the two lines are the same return np.nan
    if line1==line2: 
        intersect=np.nan
    #use intersection method of LineString object if they are not
    elif line1!=line2: 
        intersect=line1.intersection(line2).wkt
        if intersect=='LINESTRING EMPTY': 
        #if there is no intersection, replace returned text with NaN
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

def to_one_list(row): 
    '''
    Combine all columns of a dataframe into one column with a list containing the prior column values.
    
    *row=df row to be transformed
    '''
    val_list=[x for x in row if math.isnan(x)==False]
    if len(val_list)==1: 
        val_list=val_list[0]
    
    return val_list

#*#########################
#! DATA
#*#########################
#read in lines with transformer numbers - output from lines_transformers_matching.py
lines=pd.read_csv(data_transformed/'lines_w_transformernos.csv')
lines=lines.drop(['Unnamed: 0', 'Trans_Location', 'point'], axis=1)
#turn geometry into shapely object from string 
lines['geometry']=lines['geometry'].apply(wkt.loads)
#lines=lines[lines['Trans_No']==8459]

#*#########################
#! INTERSECTIONS
#*#########################
#apply functions to data
#first get all intersections
intersections=all_intersections(lines)
#then turn into a dataframe
intersections_df=pd.DataFrame.from_dict(intersections, orient='index').rename(columns={0: 'geometry'})
'''
Intersections df now contains the geometry of an intersection of 3 lines twice, one row for each pair of lines intersecting in this point. Now get a df with point|(lines this point lies on), where point=intersection, and assign an id to each intersection.
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
#reset index 
point_df=point_df.reset_index()
#unpack list of lists that is now lines column
point_df['lines']=point_df['lines'].apply(unpack_lists)
#!also want a df with line_id|(points that are on line) to match with other points (units, transformers) and calculate distance between points on same line
#brute-force approach for now that is probably not very elegant 
#first retrieve all unique lines 
lines_unique=[]
for x in point_df['lines']:
    for y in x:
        lines_unique.append(y)
#then find rows in line_df that have line in their lines column and save the corresponding p_ids in a dictionary 
line_point_dict={}
for line in lines_unique:
    #get boolean series whether line is in lines col 
    bools_list=[line in x for x in point_df['lines']]
    #retrieve rows that have line in their lines col
    rows=point_df[bools_list]
    #get the point ids 
    points=rows['p_id'].tolist()
    #and save in dict 
    line_point_dict[line]=points
#turn into a df 
line_df=pd.DataFrame.from_dict(line_point_dict, orient='index')
line_df['p_id']=line_df.apply(to_one_list, axis=1)
line_df=line_df.reset_index().rename(columns={'index': 'line_id'}).drop(list(range(0, 5)), axis=1)

#!DONE 
#now write into a CSV 
point_df.to_csv(data_transformed/'intersection_points.csv')
line_df.to_csv(data_transformed/'line_intersection_points.csv')