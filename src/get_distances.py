from pyparsing import col
from shapely.geometry.linestring import LineString
from shapely.geometry import Point
import pandas as pd
import nearest_neighbor_tools as nnt
from shapely import ops, wkt
import geopandas as gpd
import numpy as np
import math
import networkx as nx
import itertools


def split_line(df, id, geom):
        '''
        Split a line that contains corners into multiple lines and assign them all a new id.
        '''
        line=df.loc[id,geom]
        coords=[a.tolist() for a in line.coords.xy]
        c_x=coords[0]
        c_y=coords[1]
        no=len(c_x)
        new_lines={}
        for n in range(no-1):
            new_lines[n]=LineString([(c_x[n],c_y[n]),(c_x[n+1],c_y[n+1])])
            
        dic = {'index':[i for i in new_lines.keys()], 'geometry':[new_lines[i] for i in new_lines.keys()]}
        df = gpd.GeoDataFrame(dic)
        df.reset_index(inplace=True) 
        df = df.rename(columns={"index":"line_n"})
        df.line_n = df.line_n +1
        df["line"] = id +1
        df["Line_ID"] = df.line.astype(str) + '00'+ df.line_n.astype(str)
        return df


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

def distances_on_line(lines, units, intersections=None, transformers=None, lines_connection=None):
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
        #first need to retrieve all points that are on this line
        points_on_line=units[units['lines']==line]
        if intersections is not None :
            intersection_points=intersections[intersections.apply(lambda x: line in x['lines'], axis = 1)]
            points_on_line.append(intersection_points, ignore_index=True)
        if lines_connection is not None:
            p_connections = lines_connection[lines_connection.apply(lambda x: line in x['lines'], axis = 1)]
            points_on_line.append(p_connections, ignore_index=True)
        if transformers is not None:
            transformer_points=transformers[transformers['lines']==line]
            points_on_line.append(transformer_points, ignore_index=True)
        # combine to one df
        points_on_line = points_on_line.drop_duplicates(['geometry'],ignore_index=True) # geometry
        # initialize dictionary with point-tuples as key and distance as value        
        line_dist={}
        if len(points_on_line) >= 2:
            geoms=points_on_line['geometry'].tolist()
            for combi in itertools.combinations(geoms, 2):
                # calculate distance of all combinations
                #print((combi[0].wkt,combi[1].wkt))
                dist=combi[0].distance(combi[1])
                # retrieve point A
                pointA = points_on_line.loc[points_on_line['geometry']==combi[0], 'p_id'].reset_index(drop=True)[0]
                # retrieve point B
                pointB = points_on_line.loc[points_on_line['geometry']==combi[1], 'p_id'].reset_index(drop=True)[0]
                # Store in dictionary
                line_dist[(pointA, pointB)] = dist
            # make dictionary in one df
            dic = {'points':[i for i in line_dist.keys()],'distance':[line_dist[i] for i in line_dist.keys()]}
            points_distance = gpd.GeoDataFrame(dic)
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



class distances:
    '''
    calculate distances from households to transformer along the lines of the electricity net
    '''

    def __init__(self, df_hh, df_tr, df_lines, cols_hh, cols_tr, lines_geom):
        '''
        cols_hh = (hh_id, hh_geom, hh_trans)
        cols_tr = (tr_id, tr_geom)
        lines_geom = geometry column of line df
        '''

        # id columns
        self.hh_id = cols_hh[0]
        self.tr_id = cols_tr[0]
        self.hh_tr = cols_hh[2] ## corresponding transformer id to hh
        # geometry columns
        self.hh_geom = cols_hh[1]
        self.tr_geom = cols_tr[1]
        self.lines_geom = lines_geom
        # dataframes
        df_hh = df_hh[[self.hh_id, self.hh_geom, self.hh_tr]].dropna(axis = 0, subset = [self.hh_geom])
        df_hh[self.hh_id] = df_hh[self.hh_id].astype(int)
        df_tr = df_tr[[self.tr_id, self.tr_geom]].dropna(axis=0, subset=[self.tr_geom])
        df_tr[self.tr_id]=df_tr[self.tr_id].astype(int)
        #drop third dimension of geometry that contains no info
        df_tr[self.tr_geom]=[ops.transform(nnt._to_2d, line) for line in df_tr[self.tr_geom]]
        df_lines = df_lines[[self.lines_geom]].dropna(axis=0, subset = [self.lines_geom])
        df_lines = df_lines.explode(ignore_index=True) # MultiLineString to Linestring
        df_lines[self.lines_geom]=[ops.transform(nnt._to_2d, line) for line in df_lines[self.lines_geom]]
        df_lines = df_lines.drop_duplicates(self.lines_geom) 
        df_lines.reset_index(inplace=True)
        df_lines = df_lines.rename(columns={"index":"line_id"})  
        #
        self.df_hh = df_hh
        self.df_tr = df_tr
        self.df_lines = df_lines


    def lines_splitting(self):
        '''
        splits all lines using function split_line
        '''
        split = pd.DataFrame()
        for i in range(len(self.df_lines)):
            df=split_line(self.df_lines,i, self.lines_geom)
            split = split.append(df)
        lines_all=self.df_lines.merge(split, left_on='line_id', right_on="line") 
        lines_all=lines_all.drop(["line", "geometry_x"], axis=1)
        lines_all=lines_all.rename(columns={"geometry_y":"geometry"})
        lines_all['Line_ID'] = lines_all['Line_ID'].astype(int)
        return gpd.GeoDataFrame(lines_all)

    def transf_line_match(self):
        '''
        matches transformer to closest line and get that point on the line
        '''
        lines = self.lines_splitting()
        trans_matching = nnt.matching_and_distances(self.df_tr, lines, (self.tr_id, self.tr_geom), ('Line_ID', 'geometry'))
        trans_closest = trans_matching.closest_points_df()
        trans_closest = trans_closest.rename(columns={'closest_point':'geometry'})
        trans_closest['geometry'] = gpd.GeoSeries(trans_closest['geometry'].apply(wkt.loads))
        return trans_closest

    def line_intersections(self):
        '''
        find intersection points of lines giving each point id and line on which they are. One point that is intersection of multiple lines will have ID|geom|(lines it lies on).
        '''
        lines = self.lines_splitting() 
        #first get all intersections
        intersections=all_intersections(lines)
        intersections_df=pd.DataFrame.from_dict(intersections, orient='index').rename(columns={0: 'geometry'})
        #make a copy of the intersections df that can be transformed 
        point_df=intersections_df #.copy()
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
        point_df['geometry'] = gpd.GeoSeries(point_df['geometry'].apply(wkt.loads))     
        return point_df

    def hh_line_match(self):
        '''
        match a hh unit to the line that is closest to the location of the unit. Then retrieve the point on the closest line that is closest to the unit and give it the household's ID. Final structure should be id|line id|geom of point on line.
        '''
        #use class matching_and_distances 
        #initialize class with lines and treatment household data
        lines = self.lines_splitting()
        treatment_matching=nnt.matching_and_distances(self.df_hh, lines, (self.hh_id, self.hh_geom), ('Line_ID', 'geometry'))
        closest_points=treatment_matching.closest_points_df()
        closest_points['closest_point'] = gpd.GeoSeries(closest_points['closest_point'].apply(wkt.loads))
        closest_points = closest_points.rename(columns={'closest_point':'geometry'})
        return closest_points

    def lines_connections(self):
        '''
        construct connection lines, i.e. collect start and endpoint of a line and find closest point to another line
        '''
        lines_points = self.lines_splitting()[['Line_ID', 'geometry']]
        # get start and endpoints
        lines_points['startpoint'] = lines_points.apply(lambda row: str(199) + str(row.Line_ID), axis=1)
        lines_points['endpoint'] = lines_points.apply(lambda row: str(299) + str(row.Line_ID), axis=1)
        lines_points['start_geom'] = lines_points.apply(lambda row: Point(row.geometry.coords[0]), axis = 1)
        lines_points['end_geom'] = lines_points.apply(lambda row: Point(row.geometry.coords[-1]), axis = 1)
        
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
        lines_connection['geometry'] = gpd.GeoSeries(lines_connection['geometry'])
        
        return lines_connection
        
    def lines_distances(self):
        '''
        calculate distances between points on the same line
        '''
        lines = self.lines_splitting()['Line_ID'].tolist()
        lines_connection = self.lines_connections()
        # need to extract all lines in lines_connection
        for x in lines_connection.lines.explode().drop_duplicates().tolist():
            if x not in lines:
                lines.append(x)
        units = self.hh_line_match()
        intersections = self.line_intersections()
        transformers = self.transf_line_match()
        distances = distances_on_line(lines=lines, units=units, intersections=intersections, transformers=transformers, lines_connection=lines_connection)
        return distances
        

    def dist_network(self, algorithm = 'bellman-ford'):
        '''
        constructing network graph to sum up the distances between household and transformer along the lines
        '''
        hh = self.df_hh
        #transformers = self.transf_line_match()
        units = self.hh_line_match()
        distances = self.lines_distances()
        points_dist = distances[['pointA', 'pointB', 'distance']].dropna().reset_index(drop=True)

        # initialize network graph
        G = nx.Graph()

        # fill up edges with weights
        for i in range(len(points_dist)):
            G.add_edge(points_dist['pointA'][i], points_dist['pointB'][i], weight=points_dist['distance'][i])
        # define source list
        source = units['p_id'].tolist()
        # initialize df
        dist = pd.DataFrame(columns=['source', 'target', 'distance', 'path']) 
        # use dist_st to get all distances from source to target in G
        for s in source:
            # extract corresponding transformer number from HH-ID
            t = hh.loc[hh[self.hh_id]==s,self.hh_tr].reset_index(drop=True)[0]
            if (t in G.nodes()) and (s in G.nodes()) and (nx.has_path(G,s,t)):
                df = dist_st(G=G, s=s, t=t, algorithm = algorithm)
                dist = dist.append(df, ignore_index=True)
        
        # distance from hh to line
        dist['hh_to_line'] = 0
        for i in source:
            # location of hh
            hh_loc = hh.loc[hh[self.hh_id] == i,self.hh_geom].reset_index(drop=True)[0]
            # location on line
            p_loc = units.loc[units['p_id']==i,'geometry'].reset_index(drop=True)[0]
            # distance
            d = hh_loc.distance(p_loc)
            # save in df
            dist.loc[dist['source']==i,'hh_to_line'] = d
        
        dist['total_dist'] = dist['distance'] + dist['hh_to_line']

        #### now add geometry of hh and transformer
        #dist['source_loc'] = dist.apply(lambda row: hh.loc[hh[self.hh_id] == row.source,self.hh_geom].reset_index(drop=True)[0], axis =1)

        #dist['target_loc'] = dist.apply(lambda row: transformers.loc[transformers['p_id'] == row.target,'geometry'].reset_index(drop=True)[0], axis =1)

        # convert distance to km
        #dist['total_dist_km'] =  dist.apply(lambda row: deg_to_km(row.total_dist,'km'), axis=1)

        #dist = dist.rename(columns={'source': 'household', 'target': 'transformer','source_loc': 'household_loc', 'target_loc': 'transformer_loc'})

        return dist



