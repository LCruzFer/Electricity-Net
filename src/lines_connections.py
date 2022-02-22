from line_splitting import lines_all
import nearest_neighbor_tools as nnt
from shapely.geometry.linestring import LineString

lines = lines_all

########## need to construct connection lines
# get start and endpoints
lines_points = lines[['Line_ID', 'geometry']]
lines_points['startpoint'] = lines_points.apply(lambda row: str(199) + str(row.Line_ID), axis=1)
lines_points['endpoint'] = lines_points.apply(lambda row: str(299) + str(row.Line_ID), axis=1)
lines_points['start_geom'] = lines_points.apply(lambda row: row.geometry.boundary[0], axis = 1)
lines_points['end_geom'] = lines_points.apply(lambda row: row.geometry.boundary[1], axis = 1)

# df with all points in lines
lines_start = lines_points[['Line_ID', 'startpoint', 'start_geom']].rename(columns={'startpoint':'p_id', 'start_geom':'geometry'})
lines_end = lines_points[['Line_ID', 'endpoint', 'end_geom']].rename(columns={'endpoint':'p_id', 'end_geom':'geometry'})
lines_points = lines_start.append(lines_end, ignore_index=True)

# find closest point which is not on same line
lines_points['closest'] = lines_points.apply(lambda row: nnt.get_closest_id(row.geometry, lines_points[lines_points.Line_ID != row.Line_ID], ('p_id', 'geometry')), axis = 1)

lines_points['geom_closest'] = lines_points.apply(lambda row: lines_points.loc[lines_points.p_id == row.closest, 'geometry'].reset_index(drop=True)[0], axis = 1)

# construct new line with LINESTRING and new ID
lines_points['line_geom'] = lines_points.apply(lambda row: LineString([row.geometry, row.geom_closest]), axis=1)
lines_points['new_line_id'] = lines_points.apply(lambda row: str(999) + str(row.Line_ID), axis =1).astype(int)

# add list of lines where point lies on
lines_points['lines'] = lines_points.apply(lambda row: lines_points.loc[(lines_points.closest == row.p_id) | (lines_points.p_id == row.p_id), 'new_line_id'].drop_duplicates().tolist(), axis = 1)
lines_points.apply(lambda row: row.lines.append(row.Line_ID), axis=1)

lines_connection = lines_points[['p_id', 'geometry', 'lines']]
lines_connection['p_id'] = lines_connection['p_id'].astype(int)

lines_list=lines['Line_ID'].drop_duplicates().tolist()
# need to extract all lines in lines_connection
for x in lines_connection.lines.explode().drop_duplicates().tolist():
    if x not in lines_list:
        lines_list.append(x)
