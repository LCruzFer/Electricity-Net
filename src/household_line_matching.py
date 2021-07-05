from pathlib import Path
import pandas as pd 
import geopandas as gpd 
from shapely import ops, wkt
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
This file is used to match a household unit to the line of the electricity network that is closest to the location of the unit. Then retrieve the point on the closest line that is closest to the unit and give it the household's ID. Final structure should be id|line id|geom of point on line.
'''

#TODO: implement finding the actually closest point on the line, for first step not necessary yet
#TODO: wrap functions into one class such that columns and dataframes only need to be supplied once!

#*#########################
#! FUNCTIONS
#*#########################

class matching_and_distances:
    #class for matching points with lines and getting distances between them 
    def __init__(self, p1, p2, cols_p1, cols_p2):
        '''
        *p1=df with id and geometry column 
        *p2=df with id and geometry column
        *cols_p1=column names of id and geometry column in p1 as tuple
        *cols_p2=column names of id and geometry column in p2 as tuple
        '''
        self.p1=p1.set_index(cols_p1[0])
        self.p2=p2.set_index(cols_p2[0])
        self.p1_geom=self.p1[cols_p1[1]]
        self.p2_geom=self.p2[cols_p2[1]]
        
    def get_closest(self):
        '''
        For each point in p1 find the id of closest point/line (using point in comments but can also be a line) in p2. 
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

    def hh_line_distance(self, match_dict):
        '''
        Using results from get_closest() find distance between the points that are closest.
        
        *match_dict=dict returnd from get_closest() where key is id of a point in p1 and val is id of the point in p2 closest to it
        '''
        #access a (key, val) pair in match_dict 
        distance_dict={}
        for key, val in match_dict.items():
            #retrieve the geom of key and val respectively
            geom_key=self.p1_geom[key]
            geom_val=self.p2_geom[val]
            #calculate distance between these two
            distance=geom_key.distance(geom_val)
            #and save in dictionary 
            distance_dict[(key, val)]=distance

        return distance_dict

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
treat_closest_lines=treatment_matching.get_closest()
#get distances between the unit and its closest line 
treat_line_distances=treatment_matching.hh_line_distance(treat_closest_lines)

