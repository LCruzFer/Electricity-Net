from pathlib import Path
from pydoc import locate
#from this import d
from get_distances import distances
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import numpy as np
import matplotlib.pyplot as plt

wd=Path.cwd()

# calculate distances using fixed lines
hh_old = gpd.read_file(f"{wd.parent}/data\Kakamega Fieldwork Shapefiles\Treatment_Households.shp")
hh = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Households edited.shp')

transformer = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Transformers edited.shp')
lines_old = gpd.read_file(f"{wd.parent}\data\Lines\lines_all.shp")
lines = gpd.read_file(f'zip://{wd.parent}/clean_data/6_fixing_lines.zip!6_fixing_lines/1_Kakamega/Clipped lines.shp')

test = distances(df_hh=hh, df_tr=transformer, df_lines=lines, cols_hh = ('OBJECTID','geometry','Trans_No'), cols_tr=('Trans_No','geometry'), lines_geom='geometry')

dist = test.dist_network()

hh_distances = hh.merge(dist, left_on='OBJECTID', right_on='household')

hh_distances.to_csv(wd.parent/'data'/'transformed_data'/'distances_fixed_lines.csv', index=False)

# using the survey data

hh_survey = pd.read_csv(wd.parent/'data'/'household_coords_survey.csv')

hh_survey['geometry'] = hh_survey.apply(lambda row: Point(row.a1_14longitude,row.a1_14latitude) , axis= 1)

hh_survey['hh_id'] = hh_survey.index +1

hh_survey = hh_survey[hh_survey.county == 'Kakamega']

survey_dist = distances(df_hh=hh_survey, df_tr=transformer, df_lines=lines, cols_hh = ('hh_id','geometry','trans_no'), cols_tr=('Trans_No','geometry'), lines_geom='geometry')

surv_distances = survey_dist.dist_network()

hh_survey = hh_survey.merge(surv_distances, left_on='hh_id', right_on='household')

hh_survey.to_csv(wd.parent/'data'/'transformed_data'/'distances_survey.csv', index=False)


