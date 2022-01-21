# KAKAMEGA ELECTRICITY NETWORKS 

### what we have:
* data on lines, households and transformers
* we know which household belongs to which transformer
* coordinates of households and transformers
* lines in the electricty net

### what we want:
shortest distance along the electricity net from household to transformer

### how to do:
1. lines can contain edges: split those lines to get only straight lines with unique Line_ID (code: line_splitting.py, output: lines_all_split.csv)
2. find intersection points of lines (code: line_intersections.py, main output: intersection_points.csv) 
3. match a household to the closest line and extract that point (code: household_line_matching.py, output: closest_points_on_lines.csv)
4. match a transformer to the closest line and extract that point (code: transformer_line_matching.py, main output: trans_line_closest.csv)
5. find the distance of points that lie on the same line, then create network graph with weighted edges to find the shortest path from a household to the transformer along the lines. (code: distance_network, output: should be household, transformer, distance)


### orga
* output of files stored in the folder 'transformed_data'.
* files of the code can be found in 'src'
* nearest_neighbor_tools.py contains function that are used in some of the other code files


