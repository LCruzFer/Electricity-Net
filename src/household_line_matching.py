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

# already defined in nearest_neighbor_tools

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
lines=pd.read_csv(data_transformed/'lines_w_transformernos.csv')
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
treatment_matching=nnt.matching_and_distances(sub_treatment_hh, lines, ('OBJECTID', 'geometry'), ('Line_ID', 'geometry'))
#get dict with indices of {hh id: closest line id}
treat_closest_lines=treatment_matching.match_dict
#get distances between the unit and its closest line 
treat_line_distances=treatment_matching.hh_line_distance()
#get dict with closest point on line that is matched to point
closest_points=treatment_matching.closest_points_df()

#write to csv 
closest_points.to_csv(data_transformed/'closest_points_on_lines.csv')