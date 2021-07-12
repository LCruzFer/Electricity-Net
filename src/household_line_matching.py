from pathlib import Path
import pandas as pd 
import geopandas as gpd 
from shapely import ops, wkt
from shapely.geometry.polygon import LinearRing
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file is used to match a household unit to the line of the electricity network that is closest to the location of the unit. Then retrieve the point on the closest line that is closest to the unit and give it the household's ID. Final structure should be id|line id|geom of point on line.
'''

#TODO: implement finding the actually closest point on the line, for first step not necessary yet
#TODO: streamline matching_and_distances class better

#*#########################
#! FUNCTIONS
#*#########################

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

#*#########################
#! DATA
#*#########################
#load necessary data 
#keep treatment and control households in seperate dfs/files
#*treatment households
treatment_hh=gpd.read_file(data_fieldwork/'Treatment_Households.shp')
#*control households
control_hh=gpd.read_file(data_fieldwork/'Control_Households.shp')
#*line data: output from lines_transformers_matching
lines=pd.read_csv(data_lines/'lines_w_transformernos.csv')
lines=lines.drop('Unnamed: 0', axis=1)
lines['geometry']=lines['geometry'].apply(wkt.loads)
#*use a subset of the data: network around transformer number 8459
sub_treatment_hh=treatment_hh[treatment_hh['Trans_No']==8459]
sub_control_hh=control_hh[control_hh['Trans_No']==8459]
sub_lines=lines[lines['Trans_No']==8459]

#*#########################
#! MATCHING
#*#########################
#use class matching_and_distances 
#initialize class with lines and treatment household data 
treatment_matching=matching_and_distances(sub_treatment_hh, lines, ('OBJECTID', 'geometry'), ('Line_ID', 'geometry'))
#get dict with indices of {hh id: closest line id}
treat_closest_lines=treatment_matching.match_dict
#get distances between the unit and its closest line 
treat_line_distances=treatment_matching.hh_line_distance()
#get dict with closest point on line that is matched to point
closest_points=treatment_matching.closest_points_df()

#write to csv 
closest_points.to_csv(data_transformed/'closest_points_on_lines.csv')