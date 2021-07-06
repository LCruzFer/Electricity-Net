from pathlib import Path
import pandas as pd 
from shapely import ops, wkt 
import networkx as nx

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file uses the line intersections (output from line_intersections), closest points to units on lines (output from lines_households_matching) and closest points to transformers (lines_transformers_matching) to create a networkx Graph with edges between points on same line. These edges have the respective distance as their weight. Then find shortest path between a point with a household id and point with transformer id using Dijkstra alogrithm. 
'''
#*#########################
#! DATA
#*#########################
#!for now household and line data only a subset (around transformer 8459) of treatment households
#household data 
units=pd.read_csv(data_transformed/'closest_points_on_lines.csv')
units['closest_point']=units['closest_point'].apply(wkt.loads)
units=units.drop('Unnamed: 0', axis=1)
#intersection points 
intersections=pd.read_csv(data_transformed/'intersection_points.csv')
intersections['geometry']=intersections['geometry'].apply(wkt.loads)
#transformer
transformers=pd.read_csv(data_transformed/'transformer_closest_linepoints.csv')
transformers=transformers.drop('Unnamed: 0', axis=1)
transformers['closest_point']=transformers['closest_point'].apply(wkt.loads)
#only keep id, line and closest point on line
transformers=transformers[['Trans_No', 'Line_ID', 'closest_point']]
#!filter this for transformer 8459 
transformer=transformers[transformers['Trans_No']==8459].reset_index(drop=True)

