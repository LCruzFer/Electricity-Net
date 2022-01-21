'''
This file is intended to match the transformer to the closest line and get that point on the line
'''

from pathlib import Path
import pandas as pd 
import geopandas as gpd 
from shapely import ops, wkt
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

#*#########################
#! DATA
#*#########################
#lines 
lines=pd.read_csv(data_transformed/'lines_all_split.csv')
lines['geometry']=lines['geometry'].apply(wkt.loads)
#transformers
transformers=gpd.read_file(data_fieldwork/'Final_Transformers.shp')
transformers['Trans_No']=transformers['Trans_No'].astype(int)
transformers['geometry']=[ops.transform(nnt._to_2d, line) for line in transformers['geometry']]



#*#########################
#! LINE IDENTIFIER
#*#########################
'''
The lines dataset does not contain any information on the transformer the lines belong to. Therefore, match them based on the following approach: 
- get points of transformers and centres of lines 
- get distance from centre of line to each transformer
- assign transformer number to line where dist(line, transformer) is minimum distance
'''
#! this is not perfect yet as this nnt.closest() simply uses center points of lines for matching purposes; it should be fine for the raw matching but isn't perfect obviously
#get centre of each line
lines['point']=[line.interpolate(0.5, normalized=True) for line in lines['geometry']]
#get transformer point and number
transformer_points=transformers[['Trans_No', 'geometry']]
#only use sub df containing line id and centre point
line_points=lines[['point', 'Line_ID']]
#apply find_closest function 
#TODO: IMPROVE PERFORMANCE OF nnt.find_closest() but LATER
nearest_one=nnt.find_closest(line_points, transformer_points, cols_points=('Line_ID', 'point'), cols_otherpoints=('Trans_No', 'geometry'))

#now create dataframe with trans_no for each line 
#first turn dict into df
nearest_one_df=pd.DataFrame.from_dict(nearest_one, orient='index').reset_index()
#rename columns 
nearest_one_df=nearest_one_df.rename(columns={'index': 'Line_ID', 0: 'Trans_No', 1: 'Trans_Location'})
#merge onto lines df but only keep its id, geometry and point column 
lines_w_transnos=lines[['Line_ID', 'geometry', 'point']].merge(nearest_one_df, on='Line_ID', how='left')

#write to a csv 
lines_w_transnos.to_csv(data_transformed/'lines_w_transformernos.csv')


#*##########################
#! Matching
#*##########################
# use class matching_and_distances from nnt
trans_matching= nnt.matching_and_distances(transformers, lines, ('Trans_No', 'geometry'), ('Line_ID', 'geometry'))
# df with point-ID (which is similar to transformer-ID), the closest line and that point
trans_closest = trans_matching.closest_points_df()

# export dataframe 
trans_closest.to_csv(data_transformed/'trans_line_closest.csv')
