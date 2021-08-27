from pathlib import Path
import pandas as pd 
import geopandas as gpd
from shapely import ops, wkt 
import networkx as nx
from shapely.geometry import Point
import itertools 
import numpy as np
import networkx as nx
import math

from shapely.geometry.linestring import LineString
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file uses a network graph to find the distance from a household to the transformer. First, the distance between points laying on the same line are calculated. Then, a weighted network graph is constructed to find the shortest path. Finally, the distance between a household to the point on line is added.

files used:
closest_points_on_lines.csv (household)
intersection_points.csv
trans_line_closest.csv
lines_all_split.csv
Treatment_Households.shp

output: distances.csv

###
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

def str_to_list(df, col):
    '''
    csv stores list as string: retrieve list and corresponding integers in list
    '''
    df[col]=df[col].apply(lambda x: x.strip('][').split(','))
    df[col]=df[col].apply(lambda x: [float(e) for e in x])
    df[col]=df[col].apply(lambda x: [int(e) for e in x])

    return df


def distances_on_line(lines, units, intersections, transformers, lines_connection):
    '''
    Calculate distance between points on the same line.
    
    *lines=list of lines
    *units=unit df 
    *intersections=intersections df 
    *transformers=transformers df

    returns a df with the line, the corresponding distances of two points on this line, including the geometry of the points
    '''
    #for a given line
    #lines=transformer['lines'].drop_duplicates()
    # empty final dataframe
    distances = pd.DataFrame(columns=['line', 'points', 'distance', 'pointA', 'pointB', 'geometry_A', 'geometry_B'])
    for line in lines:
        #line=52201
        #first need to retrieve all points that are on this line
        unit_points=units[units['lines']==line]
        intersection_points=intersections[intersections.apply(lambda x: line in x['lines'], axis = 1)]
        p_connections = lines_connection[lines_connection.apply(lambda x: line in x['lines'], axis = 1)]
        transformer_points=transformers[transformers['lines']==line]
        # combine to one df
        points_on_line = unit_points.append([intersection_points,transformer_points, p_connections], ignore_index=True).drop_duplicates(['p_id'])
        # initialize dictionary with point-tuples as key and distance as value
        line_dist={}
        if len(points_on_line) >= 2:
            geoms=points_on_line['geometry'].tolist()
            for combi in itertools.combinations(geoms, 2):
                # calculate distance of all combinations
                dist=combi[0].distance(combi[1])
                # retrieve point A
                pointA = points_on_line.loc[points_on_line['geometry']==combi[0], 'p_id'].reset_index(drop=True)[0]
                # retrieve point B
                pointB = points_on_line.loc[points_on_line['geometry']==combi[1], 'p_id'].reset_index(drop=True)[0]
                # Store in dictionary
                line_dist[(pointA, pointB)] = dist
            # make dictionary in one df
            points_distance = pd.DataFrame.from_dict(line_dist, orient='index', columns=['distance'])
            points_distance=points_distance.reset_index()        
            points_distance=points_distance.rename(columns={'index':'points'})
            # include corresponding line
            points_distance['line'] = line
            # retrieve point ids
            points_distance['pointA'] = points_distance.apply(lambda row: row.points[0], axis=1)
            points_distance['pointB'] = points_distance.apply(lambda row: row.points[1], axis=1)
            # retrieve point geometry
            points_distance['geometry_A'] = points_distance.apply(lambda row: points_on_line.loc[points_on_line['p_id'] == row.pointA,'geometry'].reset_index(drop=True)[0], axis=1)
            points_distance['geometry_B'] = points_distance.apply(lambda row: points_on_line.loc[points_on_line['p_id'] ==row.pointB,'geometry'].reset_index(drop=True)[0], axis=1)
            # add to df
            distances=distances.append(points_distance, ignore_index=True)
        elif len(points_on_line) == 1: 
            # put in nan's if points_on_line has less than 2 entries, because distance can not be calculated
            point = points_on_line.loc[:, 'p_id'].reset_index(drop=True)[0]
            geom = points_on_line.loc[:, 'geometry'].reset_index(drop=True)[0].wkt
            no_dist = pd.DataFrame({'line':[line], 'distance':[np.nan], 'points': point, 'geometry_A':geom, 'pointA': point}).reset_index(drop=True)
            distances=distances.append(no_dist, ignore_index=True)
        else: 
            no_dist = pd.DataFrame({'line':[line], 'distance':[np.nan]}).reset_index(drop=True)
            distances=distances.append(no_dist, ignore_index=True)
    return distances

def dist_st(G,s,t, algorithm='bellman-ford'):
    '''
    find the shortest path between s and t in network graph and calculate the distance,
    return df with source, target, and the distance containing one row and the path as a list of points
    G: network Graph
    s: source
    t: target
    algorithm: default is bellman-ford, alternative is dijkstra
    '''
    #a = s
    #b = t
    #df = points_dist
    # get path points between source and target, weighted by distance
    path = nx.shortest_path(G, source=s, target=t, weight='distance', method=algorithm)
    # initialize distance
    d = 0
    # add up distance along path
    for i in range(len(path)):
        if i < len(path)-1: # sonst index out of range
            d += G.edges[(path[i],path[i+1])]['weight']
    # make df        
    x = {'source':s,'target':t, 'distance':d, 'path':[path]}
    to_df = pd.DataFrame.from_dict(x)
    return to_df

def deg_to_km(deg, unit='m'):
    '''
    -- function by Lucas --
    Turn degrees into m using haversine formula.
    Using formula from here: https://sciencing.com/convert-distances-degrees-meters-7858322.html
    L=(2*pi*r*A)/360 
    where r of earth=6371km, A is degrees, L is output length
    *deg=degrees
    *unit=choose unit of output to be m or km
    '''
    if unit=='m':
        unit=1000
    elif unit=='km': 
        unit=1
    else: 
        raise ValueError(f'Unit must be one of m or km.')
    nom=2*math.pi*deg*6371*unit
    denom=360
    
    return nom/denom

    
#*#########################
#! DATA
#*#########################

#household data 
units=pd.read_csv(data_transformed/'closest_points_on_lines.csv')
units=prep_data(units, ['closest_point'])
units=units.rename(columns = {units.columns[1]:'geometry'})
#intersection points 
intersections=pd.read_csv(data_transformed/'intersection_points.csv')
intersections=prep_data(intersections, ['geometry'])
intersections=str_to_list(intersections,'lines')

'''
#read in line_id|(p_ids of points on line) df 
lineid_pid=pd.read_csv(data_transformed/'line_intersection_points.csv')
lineid_pid=prep_data(lineid_pid, [])
lineid_pid=str_to_list(lineid_pid, 'p_id')
#streamline column names across data 
lineid_pid=lineid_pid.rename(columns={'line_id': 'lines'})

'''

#transformer
transformers=pd.read_csv(data_transformed/'trans_line_closest.csv')
transformers=prep_data(transformers, ['closest_point'])
transformers=transformers.rename(columns={'closest_point':'geometry'})

#*treatment households
treatment_hh=gpd.read_file(data_fieldwork/'Treatment_Households.shp')


# lines
lines=pd.read_csv(data_transformed/'lines_all_split.csv')
lines = prep_data(lines, ['geometry'])

########## need to construct connection lines
# get start and endpoints
lines_points = lines[['Line_ID', 'geometry']]
lines_points['startpoint'] = lines_points.apply(lambda row: str(199) + str(row.Line_ID), axis=1)
lines_points['endpoint'] = lines_points.apply(lambda row: str(299) + str(row.Line_ID), axis=1)
lines_points['start_geom'] = lines_points.apply(lambda row: row.geometry.boundary[0], axis = 1)
lines_points['end_geom'] = lines_points.apply(lambda row: row.geometry.boundary[1], axis = 1)

# df with all points in lines
lines_start = lines_points[['Line_ID', 'startpoint', 'start_geom']].rename(columns={'startpoint':'p_id', 'start_geom':'geometry'})
lines_end = lines_points[['Line_ID', 'endpoint', 'end_geom']].rename(columns={'endpoint':'p_id', 'end_geom':'geometry'})
lines_points = lines_start.append(lines_end, ignore_index=True)

# find closest point which is not on same line
lines_points['closest'] = lines_points.apply(lambda row: nnt.get_closest_id(row.geometry, lines_points[lines_points.Line_ID != row.Line_ID], ('p_id', 'geometry')), axis = 1)

lines_points['geom_closest'] = lines_points.apply(lambda row: lines_points.loc[lines_points.p_id == row.closest, 'geometry'].reset_index(drop=True)[0], axis = 1)

# construct new line with LINESTRING and new ID
lines_points['line_geom'] = lines_points.apply(lambda row: LineString([row.geometry, row.geom_closest]), axis=1)
lines_points['new_line_id'] = lines_points.apply(lambda row: str(999) + str(row.Line_ID), axis =1).astype(int)

# add list of lines where point lies on
lines_points['lines'] = lines_points.apply(lambda row: lines_points.loc[(lines_points.closest == row.p_id) | (lines_points.p_id == row.p_id), 'new_line_id'].drop_duplicates().tolist(), axis = 1)
lines_points.apply(lambda row: row.lines.append(row.Line_ID), axis=1)

lines_connection = lines_points[['p_id', 'geometry', 'lines']]
lines_connection['p_id'] = lines_connection['p_id'].astype(int)

#*#########################
#! DISTANCES
#*#########################
'''
In this section the distances between points on the same line are calculated.
'''


# use function distances_on_line
lines_list=lines['Line_ID'].drop_duplicates().tolist()
# need to extract all lienes in lines_connection
for x in lines_connection.lines.explode().drop_duplicates().tolist():
    if x not in lines_list:
        lines_list.append(x)

#lines_list.append(lines_connection.lines.explode().drop_duplicates().tolist())
distances = distances_on_line(lines=lines_list, units=units, intersections=intersections, transformers=transformers, lines_connection=lines_connection)
distances[~(distances.distance.isnull())]
# lines with nan
no_distances=distances[distances.distance.isnull()]
# 
len(no_distances)

#########################
# need to construct distances for unconnected lines

'''
# get start and end point of lines with no distance
no_distances['line_geometry'] = no_distances.apply(lambda row: lines.geometry[lines.Line_ID == row.line].reset_index(drop=True)[0], axis =1)
no_distances['line_startpoint'] = no_distances.apply(lambda row: row.line_geometry.boundary[0], axis = 1)
no_distances['line_endpoint'] = no_distances.apply(lambda row: row.line_geometry.boundary[1], axis = 1)

# make points df with all points which are connected
points = distances[['pointA', 'geometry_A']].rename(columns={'pointA':'point', 'geometry_A':'geometry'}).dropna()
points = points.append(distances[['pointB', 'geometry_B']].rename(columns={'pointB':'point', 'geometry_B':'geometry'}).dropna()).reset_index(drop=True)

# df of start and end points of unconnected lines
new_lines = no_distances[['line', 'line_startpoint']].rename(columns={'line_startpoint': 'geometryA'})
new_lines['line'] = new_lines.apply(lambda row: str(row.line) + str(1), axis=1)
linesB = no_distances[['line', 'line_endpoint']].rename(columns={'line_endpoint': 'geometryA'})
linesB['line'] = linesB.apply(lambda row: str(row.line) + str(2), axis=1)
# get distances of points on same line
same_lines = new_lines.copy()
same_lines = same_lines.rename(columns = {'line':'pointA'})
#same_lines['pointA'] = same_lines['pointA'].astype(int)
same_lines['pointB'] = linesB['line']
same_lines['geometryB'] = linesB['geometryA'] 


# find the closest points of all connected points
new_lines = new_lines.append(linesB).rename(columns = {'line':'pointA'}).reset_index(drop=True)
#new_lines['pointA'] = new_lines['pointA'].astype(int)
new_lines['pointB'] = new_lines.apply(lambda row: nnt.get_closest_id(row.geometryA, points, ('point', 'geometry')), axis = 1)
# get geometry of closest point
new_lines['geometryB'] = new_lines.apply(lambda row: points.loc[points.point == row.pointB, 'geometry'].reset_index(drop=True)[0], axis=1)

# add points on same line
new_lines = new_lines.append(same_lines).reset_index(drop=True)

# get distance between points
new_lines['distance'] = new_lines.apply(lambda row: row.geometryA.distance(row.geometryB), axis=1)
'''

#*#########################
#! Network Graph
#*#########################
'''
In this section the network graph is constructed to sum up the distances between unit and transformer along the lines.
'''

points_dist = distances[['pointA', 'pointB', 'distance']].dropna().reset_index(drop=True)
# append new constructed points-distance
#points_dist = points_dist.append(new_lines[['pointA', 'pointB', 'distance']]).drop_duplicates().reset_index(drop=True)

# initialize network graph
G = nx.Graph()

# fill up edges with weights
for i in range(len(points_dist)):
    G.add_edge(points_dist['pointA'][i], points_dist['pointB'][i], weight=points_dist['distance'][i])

# visualization
#nx.draw(G, with_labels= True, alpha=.2)


# define source list
source = units['p_id'].tolist()

# initialize df
dist_bf = pd.DataFrame(columns=['source', 'target', 'distance', 'path']) 
# use dist_st to get all distances from source to target in G
for s in source:
    # extract corresponding transformer number from HH-ID
    t = treatment_hh[treatment_hh['OBJECTID']==s]['Trans_No'].reset_index(drop=True)[0]
    if (t in G.nodes()) and (s in G.nodes()) and (nx.has_path(G,s,t)):
        df = dist_st(G=G, s=s, t=t, algorithm = 'bellman-ford')
        dist_bf = dist_bf.append(df, ignore_index=True)

# using dijkstra algorithm
dist_dij = pd.DataFrame(columns=['source', 'target', 'distance', 'path']) 
# use dist_st to get all distances from source to target in G
for s in source:
    # extract corresponding transformer number from HH-ID
    t = treatment_hh[treatment_hh['OBJECTID']==s]['Trans_No'].reset_index(drop=True)[0]
    if (t in G.nodes()) and (s in G.nodes()) and (nx.has_path(G,s,t)):
        df = dist_st(G=G, s=s, t=t, algorithm = 'dijkstra')
        dist_dij = dist_dij.append(df, ignore_index=True)

# rename and merge
dist_bf = dist_bf.rename(columns = {'distance':'distance_bf', 'path':'path_bf'})
dist_dij = dist_dij.rename(columns = {'distance':'distance_dij', 'path':'path_dij'})   
dist_all = dist_bf.merge(dist_dij, on=['source', 'target'])

len(dist_all) # 473
len(source) # 596

'''
missing distances for more than 100 hh
reason: some lines do not intersect -> see Visualization
'''

#*#########################
#! Distances HH to line
#*#########################

# units df contains location of closest points on line from hh
# treatment_hh contains location of hh 
# nead to find distance between those 

# new column
dist_all['hh_to_line'] = 0
for i in source:
    # location of hh
    hh_loc = treatment_hh[treatment_hh['OBJECTID'] == i]['geometry'].reset_index(drop=True)[0]
    # location on line
    p_loc = units[units['p_id']==i]['geometry'].reset_index(drop=True)[0]
    # distance
    d = hh_loc.distance(p_loc)
    # save in df
    dist_all.loc[dist_all['source']==i,'hh_to_line'] = d

# column with total distance from hh to transformer
# for now only bellman-ford, although they are similar for all except one household
dist_all['total_bf'] = dist_all['distance_bf']+dist_all['hh_to_line']  

### could add distance from transformer to line, but should be very small

#*#########################
#! Final df
#*#########################

#### now add geometry of hh and transformer
dist_all['source_loc'] = dist_all.apply(lambda row: treatment_hh.loc[treatment_hh['OBJECTID'] == row.source,'geometry'].reset_index(drop=True)[0], axis =1)

dist_all['target_loc'] = dist_all.apply(lambda row: transformers.loc[transformers['p_id'] == row.target,'geometry'].reset_index(drop=True)[0], axis =1)

## convert distance to km 
# according to https://gis.stackexchange.com/questions/80881/what-is-unit-of-shapely-length-attribute unit is degrees 


# apply function
dist_all['total_bf_km'] =  dist_all.apply(lambda row: deg_to_km(row.total_bf,'km'), axis=1)

# export to csv
dist_all.to_csv(data_transformed/'distances.csv')
