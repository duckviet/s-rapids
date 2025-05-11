import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import cuspatial
import cudf
import time
from haversine import haversine
import numpy as np

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
    """Tính toán metrics sử dụng cuSpatial với các thao tác vector hóa"""
    start_time = time.time()
    
    # Chuyển đổi DataFrame thành cuDF DataFrame
    cudf_gps = cudf.DataFrame(gps_data)
    
    # Sắp xếp dữ liệu theo trip_id và timestamp để đảm bảo thứ tự các điểm
    cudf_gps = cudf_gps.sort_values(['trip_id', 'timestamp'])
    
    # Tạo các cột cho điểm tiếp theo
    cudf_gps['next_lat'] = cudf_gps.groupby('trip_id')['latitude'].shift(-1)
    cudf_gps['next_lon'] = cudf_gps.groupby('trip_id')['longitude'].shift(-1)
    
    # Loại bỏ các hàng có giá trị null (điểm cuối của mỗi chuyến đi)
    cudf_gps = cudf_gps.dropna(subset=['next_lat', 'next_lon'])
    
    # Tính khoảng cách giữa các điểm liên tiếp sử dụng haversine
    def haversine_vectorized(lat1, lon1, lat2, lon2):
        # Chuyển đổi độ sang radian
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        
        # Công thức haversine vector hóa
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371  # Bán kính trái đất tính bằng km
        return c * r
    
    # Tính khoảng cách cho mỗi cặp điểm
    cudf_gps['distance'] = haversine_vectorized(
        cudf_gps['latitude'].values,
        cudf_gps['longitude'].values,
        cudf_gps['next_lat'].values,
        cudf_gps['next_lon'].values
    )
    
    # Tính tổng khoảng cách cho mỗi chuyến đi
    trip_distances = cudf_gps.groupby('trip_id')['distance'].sum().reset_index()
    
    # Tính thời gian di chuyển cho mỗi chuyến đi
    trip_times = cudf_gps.groupby('trip_id').agg({
        'timestamp': ['first', 'last']
    })
    
    # Flatten the multi-level columns
    trip_times.columns = ['_'.join(col).strip() for col in trip_times.columns.values]
    trip_times = trip_times.reset_index()
    
    # Tính thời gian di chuyển (giờ)
    trip_times['duration_hours'] = (
        (trip_times['timestamp_last'] - trip_times['timestamp_first'])
        .dt.total_seconds() / 3600
    )
    
    # Kết hợp kết quả
    trip_metrics = trip_distances.merge(
        trip_times[['trip_id', 'duration_hours']],
        on='trip_id'
    )
    
    # Tính tốc độ trung bình
    trip_metrics['avg_speed_kmh'] = (
        trip_metrics['distance'] / trip_metrics['duration_hours']
    ).round(2)
    
    # Làm tròn các giá trị
    trip_metrics['total_distance_km'] = trip_metrics['distance'].round(2)
    trip_metrics['duration_hours'] = trip_metrics['duration_hours'].round(2)
    
    # Chọn và sắp xếp các cột cần thiết
    result = trip_metrics[['trip_id', 'total_distance_km', 'duration_hours', 'avg_speed_kmh']]
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return result.to_pandas(), execution_time 