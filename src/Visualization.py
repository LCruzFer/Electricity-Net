import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import geopandas as gpd
from shapely import wkt
from get_distances import distances
import numpy as np

#*set path 
wd=Path.cwd()
data_transformed=wd.parent/'data'/'transformed_data'
data_lines=wd.parent/'data'/'Lines'
data_fieldwork=wd.parent/'data'/'Kakamega Fieldwork Shapefiles'
plots=wd.parent/'Visualization'

############## using fixed lines
hh = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Households edited.shp')

transformer = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Transformers edited.shp')

lines = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Clipped lines.shp')

#test = distances(df_hh=hh, df_tr=transformer, df_lines=lines, cols_hh = ('OBJECTID','geometry','Trans_No'), cols_tr=('Trans_No','geometry'), lines_geom='geometry')

#lines = test.lines_splitting()
#lines = lines.set_crs('epsg:4326')

dist = pd.read_csv(data_transformed/'distances_fixed_lines.csv') 
dist['household_loc'] = dist['household_loc'].apply(wkt.loads)


# for given transformer
trans_no = 40958	#8459

# assign transformer-ID to lines
radius = 2000
for t in transformer.Trans_No:
    trans_loc = transformer.loc[transformer.Trans_No == t, 'geometry'].to_crs(3857).reset_index(drop=True)[0]
    circle = trans_loc.buffer(radius)
    bool = lines['geometry'].to_crs(3857).within(circle)
    lines.loc[bool,'Trans_No'] = t 

lines_trans = lines.loc[lines.Trans_No == str(trans_no),]
trans = transformer.loc[transformer.Trans_No == str(trans_no)]

hh_wd = dist.loc[dist.transformer == trans_no, 'household'].tolist()
hh['nodist'] = np.nan
for h in hh.OBJECTID:
    if h not in hh_wd:
        hh.loc[(hh.OBJECTID == h) & (hh.Trans_No == trans_no),'nodist'] = True
hh_nodist = hh[hh.nodist == True]

# plot
fig, ax = plt.subplots()
lines_trans.plot(ax=ax)
trans.plot(ax=ax, color='red')
gpd.GeoDataFrame(dist[dist.transformer == trans_no], geometry='household_loc').plot(color='green', ax= ax, label='with dist')
hh_nodist.plot(ax=ax, color='violet', label='no dist')
plt.axis('off')
plt.legend(loc='lower right')

#fig.savefig(wd.parent/'Visualization'/f'transformer{trans_no}_hh.png')

###################################
'''
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

#fig.savefig(plots/'transformer8459.png')
'''