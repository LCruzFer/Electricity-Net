import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point, LineString
from shapely import wkt


#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'
plots=wd.parent/'Visualization'

# load data
lines=pd.read_csv(data_transformed/'lines_w_transformernos.csv')
lines=lines.drop('Unnamed: 0', axis=1)
lines['geometry']=lines['geometry'].apply(wkt.loads)
lines = lines.to_crs('epsg:4326')

trans = lines[['Trans_No', 'Trans_Location']]
trans['Trans_Location']=trans['Trans_Location'].apply(wkt.loads)

trans = gpd.GeoDataFrame(trans, geometry='Trans_Location')
trans = trans.drop_duplicates()
lines = gpd.GeoDataFrame(lines, geometry = 'geometry')

treatment_hh=gpd.read_file(data_fieldwork/'Treatment_Households.shp')


# plot
fig, ax = plt.subplots(figsize= (12,12))
lines[lines['Trans_No']==8459].plot(ax=ax)
trans[trans['Trans_No']==8459].plot(ax=ax, color='red', marker='o', markersize=50)
treatment_hh[treatment_hh['Trans_No']==8459].plot(ax=ax, color='grey')
ax.set_axis_off()
plt.show(fig)

fig.savefig(plots/'transformer8459.png')
