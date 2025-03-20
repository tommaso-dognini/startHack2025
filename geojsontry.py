import geopandas as gpd
import geoplot
import geoplot.crs as gcrs

data = gpd.read_file(
    r"D:\Utente\Download\hotosm_bfa_roads_lines_geojson\hotosm_bfa_roads_lines_geojson.geojson"
)

geoplot.polyplot(
    data,
    projection=gcrs.AlbersEqualArea(),
    edgecolor='darkgrey',
    facecolor='lightgrey',
    linewidth=.3,
    figsize=(12, 8)
)

print(type(data))