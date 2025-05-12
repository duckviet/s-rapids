import cudf
import cuspatial
import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np

def create_point_in_polygon_index(districts):
    """Create a spatial index for point-in-polygon queries"""
    # Convert districts to cuSpatial format
    district_polygons = []
    district_names = []
    
    # Process each district from the GeoJSON structure
    for district in districts["level2s"]:
        for polygon in district["coordinates"]:
            # Convert coordinates to the format expected by cuSpatial
            coords = np.array(polygon[0])  # Get the first ring of coordinates
            # Create polygon array with proper structure
            polygon_array = np.array([coords])
            district_polygons.append(polygon_array)
            district_names.append(district["name"])
    
    return district_polygons, district_names

def find_district_for_point(point, district_polygons, district_names):
    """Find which district a point belongs to"""
    # Convert point to numpy array format expected by cuSpatial
    points = np.array([[point.x, point.y]])
    
    # Check each polygon
    for i, polygon in enumerate(district_polygons):
        try:
            # Use cuSpatial's point_in_polygon with properly formatted data
            result = cuspatial.point_in_polygon(points, polygon)
            if result[0]:  # If point is in polygon
                return district_names[i]
        except Exception as e:
            print(f"Error checking polygon {i}: {e}")
            continue
    
    return "Unknown"

def analyze_bus_routes(gps_data, districts):
    """Analyze bus routes and determine their districts"""
    # Create spatial index
    district_polygons, district_names = create_point_in_polygon_index(districts)
    
    # Convert GPS data to cuDF if it's not already
    if not isinstance(gps_data, cudf.DataFrame):
        gps_data = cudf.DataFrame(gps_data)
    
    # Group by trip_id and get first and last points
    trip_points = gps_data.groupby('trip_id').agg({
        'latitude': ['first', 'last'],
        'longitude': ['first', 'last']
    })
    
    # Flatten column names
    trip_points.columns = ['_'.join(col).strip() for col in trip_points.columns.values]
    
    # Reset index to make trip_id a column
    trip_points = trip_points.reset_index()
    
    # Create route analysis results
    route_analysis = []
    
    # Convert to pandas for iteration
    trip_points_pd = trip_points.to_pandas()
    
    for _, row in trip_points_pd.iterrows():
        start_point = Point(row['longitude_first'], row['latitude_first'])
        end_point = Point(row['longitude_last'], row['latitude_last'])
        
        start_district = find_district_for_point(start_point, district_polygons, district_names)
        end_district = find_district_for_point(end_point, district_polygons, district_names)
        
        route_analysis.append({
            'trip_id': row['trip_id'],
            'start_lat': row['latitude_first'],
            'start_lon': row['longitude_first'],
            'end_lat': row['latitude_last'],
            'end_lon': row['longitude_last'],
            'start_district': start_district,
            'end_district': end_district
        })
    
    # Convert to cuDF DataFrame
    route_df = cudf.DataFrame(route_analysis)
    return route_df

def get_route_summary(route_analysis):
    """Generate summary statistics for bus routes"""
    # Convert to pandas if it's a cuDF DataFrame
    if isinstance(route_analysis, cudf.DataFrame):
        route_analysis = route_analysis.to_pandas()
    
    # Count routes by district pairs
    district_pairs = route_analysis.groupby(['start_district', 'end_district']).size().reset_index()
    district_pairs.columns = ['start_district', 'end_district', 'route_count']
    
    # Sort by route count
    district_pairs = district_pairs.sort_values('route_count', ascending=False)
    
    return district_pairs
