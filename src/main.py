from pathlib import Path
#from this import d
from zipfile import ZipFile
from get_distances import distances
import geopandas as gpd
import pandas as pd


wd=Path.cwd()

## need to merge data for all counties

#counties = ['1_Kakamega', '2_Kericho', '3_Baringo','4_Nakuru','5_Kitui','6_Taita Taveta']

# calculate distances
hh = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Households edited.shp')
transformer = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Transformers edited.shp')
lines = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Clipped lines.shp')

test = distances(df_hh=hh, df_tr=transformer, df_lines=lines, cols_hh = ('OBJECTID','geometry','Trans_No'), cols_tr=('Trans_No','geometry'), lines_geom='geometry')
df = test.lines_distances()

dist = test.dist_network()

hh_distances = hh.merge(dist, left_on='OBJECTID', right_on='household')

hh_distances.to_csv(wd.parent/'data'/'transformed_data'/'distances_new.csv')
