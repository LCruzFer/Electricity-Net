from pathlib import Path
from networkx.algorithms.shortest_paths.generic import shortest_path
import pandas as pd 
from shapely import ops, wkt 
import networkx as nx
from shapely.geometry import Point
import itertools 
import numpy as np
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
#*#########################
#! DATA
#*#########################
#!for now household and line data only a subset (around transformer 8459) of treatment households
#household data 
units=pd.read_csv(data_transformed/'closest_points_on_lines.csv')
units=prep_data(units, ['closest_point'])
units=units.rename(columns = {units.columns[1]:'geometry'})
#intersection points 
intersections=pd.read_csv(data_transformed/'intersection_points.csv')
intersections=prep_data(intersections, ['geometry'])
intersections=str_to_list(intersections,'lines')
#read in line_id|(p_ids of points on line) df 
lineid_pid=pd.read_csv(data_transformed/'line_intersection_points.csv')
lineid_pid=prep_data(lineid_pid, [])
lineid_pid=str_to_list(lineid_pid, 'p_id')
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
        # combine to one df
        points_on_line = unit_points.append(intersection_points, ignore_index=True)
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
            distances=distances.append(points_distance, ignore_index=True)
        else: 
            # put in nan's if points_on_line has less than 2 entries, because distance can not be calculated
            no_dist = pd.DataFrame({'line':[line], 'distance':[np.nan]}).reset_index(drop=True)
            distances=distances.append(no_dist, ignore_index=True)
    return distances


# use function
lines=transformer['lines'].drop_duplicates().tolist()
distances = distances_on_line(lines=lines, units=units, intersections=intersections, transformer=transformer)
# lines with nan
no_distances=distances.line[distances.distance.isnull()].tolist()
# 220 lines
len(no_distances)

#*#########################
#! Network Graph
#*#########################
'''
In this section the network graph is constructed to sum up the distances between unit and transformer along the lines.
'''

test = distances[['pointA', 'pointB', 'distance']].dropna().reset_index(drop=True)

# initialize network graph
G = nx.Graph()

# fill up edges with weights
for i in range(len(test)):
    G.add_edge(test['pointA'][i], test['pointB'][i], weight=test['distance'][i])

# visualization
nx.draw(G, with_labels= True, font_weight='bold')


def dist_ab(G,a,b,df):
    '''
    find the shortest path between a and b in network and calculate the distance,
    return df with source, target, and the distance containing one row
    '''
    #a = s
    #b = t
    #df = test
    # get path points between source and target, weighted by distance
    path = nx.shortest_path(G, source=a, target=b, weight='distance')
    # initialize distance
    d = 0
    # add up distance along path
    for i in range(len(path)):
        if i < len(path)-1: # sonst index out of range
            # a and b can either be stored in 'pointA' or 'pointB'
            d += df['distance'][((df['pointA']==path[i]) & (df['pointB']==path[i+1])) | ((df['pointB']==path[i]) & (df['pointA']==path[i+1]))].reset_index(drop=True)[0]
    # make df        
    x = {'source':[a],'target':[b], 'distance':[d]}
    to_df = pd.DataFrame.from_dict(x)
    return to_df


# define source and target lists
source = units['p_id'].tolist()
#target = transfomers['Trans_No'].tolist() # need here point id's

# initialize df
dist = pd.DataFrame(columns=['source', 'target', 'distance']) 
# use dist_ab to get all distances from source to target in G
for s in source:
    t = 598944
    #for t in target:
    if (t in G.nodes()) and (s in G.nodes()) and (nx.has_path(G,s,t)):
        df = dist_ab(G=G, a=s, b=t, df=test)
        dist.append(df, ignore_index=True)


'''
can ignore this, was just for testing before
'''
# test shortets path
a=test['pointA'][1]
b=test['pointB'][4]
y=nx.shortest_path(G, source=a, target=b, weight='distance') # target cant be list
#length=nx.shortest_path_length(G, source=a, target=b, weight='distance')

# calculate distance

d = test['distance'][(test['pointB']==y[0]) & (test['pointA']==y[1])].reset_index(drop=True)[0] + test['distance'][(test['pointA']==y[1]) & (test['pointB']==y[2])].reset_index(drop=True)[0]
x = {'source':a,'target':b, 'distance':d}
dist.append(x, ignore_index=True)