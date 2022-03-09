from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from get_distances import deg_to_km

wd = Path.cwd()

match = pd.read_stata(wd.parent/'data'/'transformed_data'/'household_matching.dta')
match = match.loc[match.county == 'Kakamega',]
match = match[['fid','objectid', 'pathdistance']]


calc = pd.read_csv(wd.parent/'data'/'transformed_data'/'distances_fixed_lines.csv')

old = pd.read_csv(wd.parent/'data'/'transformed_data'/'distances_old_data.csv')

old = old[['household', 'total_bf','total_bf_km']]


calc_dist = calc[['OBJECTID','distance']]
calc_dist['dist_m'] = calc_dist.apply(lambda row: deg_to_km(row.distance, 'm'), axis=1)

comp = match.merge(calc_dist,left_on='objectid', right_on='OBJECTID', how='left' )

comp['comp'] = comp.pathdistance - comp.dist_m

comp.loc[comp.comp == comp.comp.max(),]

(comp.pathdistance - comp.dist_m).describe()
