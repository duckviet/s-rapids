import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import cuspatial
import time
from haversine import haversine

def load_gps_data(file_path):
    """Đọc dữ liệu GPS từ file CSV"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def calculate_trip_metrics_traditional(gps_data):
    """Tính toán metrics sử dụng phương pháp thông thường (pandas + haversine)"""
    start_time = time.time()
    
    trip_metrics = []
    for trip_id in gps_data['trip_id'].unique():
        trip_data = gps_data[gps_data['trip_id'] == trip_id]
        
        # Tính khoảng cách di chuyển
        distances = []
        for i in range(len(trip_data) - 1):
            p1 = (trip_data.iloc[i]['latitude'], trip_data.iloc[i]['longitude'])
            p2 = (trip_data.iloc[i+1]['latitude'], trip_data.iloc[i+1]['longitude'])
            distance = haversine(p1, p2)
            distances.append(distance)
        
        total_distance = sum(distances)
        
        # Tính thời gian di chuyển
        time_diff = (trip_data.iloc[-1]['timestamp'] - trip_data.iloc[0]['timestamp']).total_seconds() / 3600  # Giờ
        
        # Tính tốc độ trung bình
        avg_speed = total_distance / time_diff if time_diff > 0 else 0
        
        trip_metrics.append({
            'trip_id': trip_id,
            'total_distance_km': round(total_distance, 2),
            'duration_hours': round(time_diff, 2),
            'avg_speed_kmh': round(avg_speed, 2)
        })
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return pd.DataFrame(trip_metrics), execution_time

def calculate_trip_metrics_cuspatial(gps_data):
    """Tính toán metrics sử dụng cuSpatial"""
    start_time = time.time()
    
    # Chuyển đổi DataFrame thành GeoDataFrame
    geometry = [Point(xy) for xy in zip(gps_data['longitude'], gps_data['latitude'])]
    gdf = gpd.GeoDataFrame(gps_data, geometry=geometry, crs="EPSG:4326")
    
    # Chuyển đổi sang cuSpatial DataFrame
    cudf_gps = cuspatial.from_geopandas(gdf)
    
    # Tính toán khoảng cách cho từng chuyến đi
    trip_metrics = []
    for trip_id in gps_data['trip_id'].unique():
        trip_data = gps_data[gps_data['trip_id'] == trip_id]
        
        # Tính khoảng cách di chuyển
        distances = []
        for i in range(len(trip_data) - 1):
            p1 = Point(trip_data.iloc[i]['longitude'], trip_data.iloc[i]['latitude'])
            p2 = Point(trip_data.iloc[i+1]['longitude'], trip_data.iloc[i+1]['latitude'])
            distance = p1.distance(p2) * 111  # Chuyển đổi độ sang km (ước tính)
            distances.append(distance)
        
        total_distance = sum(distances)
        
        # Tính thời gian di chuyển
        time_diff = (trip_data.iloc[-1]['timestamp'] - trip_data.iloc[0]['timestamp']).total_seconds() / 3600  # Giờ
        
        # Tính tốc độ trung bình
        avg_speed = total_distance / time_diff if time_diff > 0 else 0
        
        trip_metrics.append({
            'trip_id': trip_id,
            'total_distance_km': round(total_distance, 2),
            'duration_hours': round(time_diff, 2),
            'avg_speed_kmh': round(avg_speed, 2)
        })
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return pd.DataFrame(trip_metrics), execution_time 