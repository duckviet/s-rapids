import streamlit as st
import pydeck as pdk
import cudf
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
import numpy as np
import pandas as pd

# Hàm từ modules.bus_route_analysis
def create_point_in_polygon_index(districts):
    """Create a spatial index for point-in-polygon queries using GeoPandas"""
    # Chuyển dữ liệu districts["level2s"] thành GeoDataFrame
    districts_gdf = gpd.GeoDataFrame(districts["level2s"])
    
    # Chuyển đổi coordinates thành Polygon hoặc MultiPolygon
    geometries = []
    for coords in districts_gdf['coordinates']:
        # Kiểm tra cấu trúc của coords để xác định Polygon hay MultiPolygon
        # Nếu coords[0][0][0] là số (float/int), thì đây là Polygon (một vòng duy nhất)
        # Nếu coords[0][0][0] là danh sách, thì đây là MultiPolygon (nhiều vòng hoặc nhiều phần)
        if len(coords) == 0:
            # Trường hợp không có tọa độ, gán None
            geometries.append(None)
            continue
        
        if isinstance(coords[0][0][0], (int, float)):
            # Đây là Polygon: coords là [[[...]]]
            outer_ring = coords[0]
            geometries.append(Polygon(outer_ring))
        else:
            # Đây là MultiPolygon: coords là [[[ [...], ... ], ...]]
            polygons = []
            for poly in coords:
                # Mỗi poly là một Polygon, lấy vòng đầu tiên (outer ring)
                outer_ring = poly[0]  # Lấy vòng đầu tiên (bỏ qua các lỗ nếu có)
                polygons.append(Polygon(outer_ring))
            geometries.append(MultiPolygon(polygons))
    
    districts_gdf['geometry'] = geometries
    
    # In thông tin để kiểm tra
    # st.write(f"Số quận được tải: {len(districts_gdf)}")
    # st.write("Tên các quận:", districts_gdf['name'].tolist())
    # st.write("Cấu trúc coordinates mẫu (5 quận đầu tiên):")
    # st.write(districts_gdf[['name', 'coordinates']].head().to_dict())
    
    return districts_gdf

def find_district_for_point(point, districts_gdf):
    """Find which district a point belongs to using GeoPandas"""
    for idx, row in districts_gdf.iterrows():
        # Bỏ qua nếu geometry là None
        if row['geometry'] is None:
            continue
        if row['geometry'].contains(point):
            return row['name']
    return "Unknown"

def analyze_bus_routes(gps_data, districts):
    """Analyze bus routes and determine their districts"""
    # Tạo spatial index bằng GeoPandas
    districts_gdf = create_point_in_polygon_index(districts)
    
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
    
    # Kiểm tra một số tọa độ GPS
    st.write("Tọa độ GPS mẫu (5 dòng đầu):")
    st.write(trip_points_pd.head())
    
    for _, row in trip_points_pd.iterrows():
        start_point = Point(row['longitude_first'], row['latitude_first'])
        end_point = Point(row['longitude_last'], row['latitude_last'])
        
        start_district = find_district_for_point(start_point, districts_gdf)
        end_district = find_district_for_point(end_point, districts_gdf)
        
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

 