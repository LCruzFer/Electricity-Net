from pathlib import Path
import geopandas as gpd
import pandas as pd 
from shapely import ops, wkt 
import networkx as nx
from shapely.geometry import Point
from shapely.geometry.linestring import LineString
import nearest_neighbor_tools as nnt

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'

'''
Some lines in the electricity networks contain at least one corner (or more), i.e. their linestring is defined by three points (or more). This makes problems later on. Therefore, split those lines into two (or more) and assign them an unique id each by adding '1' or '2' to the end of their id.
'''

#*#########################
#! FUNCTIONS
#*#########################
def split_line(line, id):
    '''
    Split a line that contains corners into multiple lines and assign them all a new id.
    '''
    line=line.loc[id, 'geometry']
    coords=[a.tolist() for a in line.coords.xy]
    c_x=coords[0]
    c_y=coords[1]
    no=len(c_x)
    new_lines={}
    for n in range(no-1):
        new_lines[n]=LineString([(c_x[n],c_y[n]),(c_x[n+1],c_y[n+1])])
    
    df = pd.DataFrame.from_dict(new_lines, orient="index", columns=["geometry"])
    df.reset_index(inplace=True) 
    df = df.rename(columns={"index":"line_n"})
    df.line_n = df.line_n +1
    df["line"] = id +1
    df["Line_ID"] = df.line.astype(str) + df.line_n.astype(str)

    return df


#*#########################
#! DATA
#*#########################
lines=gpd.read_file(data_lines/'lines_all.shp')
#drop third dimension of geometry that contains no info
lines['geometry']=[ops.transform(nnt._to_2d, line) for line in lines['geometry']]

lines = lines.drop("OID_", axis=1)
lines.reset_index(inplace=True)
lines = lines.rename(columns={"index":"line_id"})
lines.line_id = lines.line_id+1

split = pd.DataFrame()
for i in range(len(lines)):
    df=split_line(lines,i)
    split = split.append(df)

# merge splits to lines
lines_all=lines.merge(split, left_on="line_id", right_on="line")
lines_all=lines_all.drop(["line", "geometry_x"], axis=1)
lines_all=lines_all.rename(columns={"geometry_y":"geometry"})

# export to csv
lines_all.to_csv(data_transformed/"lines_all_split.csv")

test=pd.read_csv(data_transformed/'lines_all_split.csv')