from pathlib import Path
import pandas as pd 
import geopandas as gpd 
from shapely import ops
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
lines=gpd.read_file(data_lines/'lines_all.shp')
lines['Line_ID']=101+lines.index
#drop freature dimension from linestring for matching to transformers to work
lines['geometry']=[ops.transform(nnt._to_2d, line) for line in lines['geometry']]
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
lines_w_transnos.to_csv(data_lines/'lines_w_transformernos.csv')

#*#########################
#! CLOSEST POINT ON LINE
#*#########################
#find the closest point to the transformer on the line that is closest to it
#use the prior results
#first only keep relevant columns of lines_w_transnos df 
trans_closest_line=lines_w_transnos[['Trans_No', 'Trans_Location', 'Line_ID', 'geometry']]
#for each (transformer, line) pair find the nearest point on the line from the transformer
#!make more pythonic once more internet access
trans_closest_line['closest_point']=0
for i in trans_closest_line.index:
    trans_geom=trans_closest_line.loc[i, 'Trans_Location']
    line_geom=trans_closest_line.loc[i, 'geometry']
    closest_point=ops.nearest_points(trans_geom, line_geom)[1]
    trans_closest_line.loc[i, 'closest_point']=closest_point

#write to csv 
trans_closest_line.to_csv(data_transformed/'transformer_closest_linepoints.csv')