from pathlib import Path
import pandas as pd 
from shapely import ops, wkt 
import networkx as nx
from shapely.geometry import Point

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file uses the line intersections (output from line_intersections), closest points to units on lines (output from lines_households_matching) and closest points to transformers (lines_transformers_matching) to create a networkx Graph with edges between points on same line. These edges have the respective distance as their weight. Then find shortest path between a point with a household id and point with transformer id using Dijkstra alogrithm. 
'''

#*#########################
#! FUNCTIONS
#*#########################
def prep_data(df, col):
    '''
    CSVs created contain an Unnamed: 0 column and columns containing geometries are imported as strings. This function drop the former and transforms the latter.
    
    *df=df to be transformed
    *col=list of column(s) containing geometries
    '''
    if 'Unnamed: 0' in df.columns: 
        df=df.drop('Unnamed: 0', axis=1)    
    for c in col: 
        df[c]=df[c].apply(wkt.loads)
    
    return df

#*#########################
#! DATA
#*#########################
#!for now household and line data only a subset (around transformer 8459) of treatment households
#household data 
units=pd.read_csv(data_transformed/'closest_points_on_lines.csv')
units=prep_data(units, ['closest_point'])
#intersection points 
intersections=pd.read_csv(data_transformed/'intersection_points.csv')
intersections=prep_data(intersections, ['geometry'])
#read in line_id|(p_ids of points on line) df 
lineid_pid=pd.read_csv(data_transformed/'line_intersection_points.csv')
lineid_pid=prep_data(lineid_pid, [])
#transformer
transformers=pd.read_csv(data_transformed/'transformer_closest_linepoints.csv')
transfomers=prep_data(transformers, ['Trans_Location', 'geometry', 'closest_point'])
#only keep id, line and closest point on line
transformers=transformers[['Trans_No', 'Line_ID', 'closest_point']]
#!filter this for transformer 8459 
transformer=transformers[transformers['Trans_No']==8459].reset_index(drop=True)
#streamline column names across data 
lineid_pid=lineid_pid.rename(columns={'line_id': 'lines'})
transformer=transformer.rename(columns={'Line_ID': 'lines'})

#*#########################
#! DISTANCES
#*#########################
'''
In this section the distances between points on the same line are calculated.
'''
def distances_on_line(lines, units, intersections, transformer):
    '''
    Calculate distance between points on the same line.
    
    *lines=list of lines
    *units=unit df 
    *intersections=intersections df 
    *transformer=transformer df
    '''
    #for a given line
    lines=transformer['lines'].drop_duplicates()
    for line in lines:
        line=5320
        #first need to retrieve all points that are on this line
        unit_points=units[units['lines']==line]

def additive(a, b):
    return a+b