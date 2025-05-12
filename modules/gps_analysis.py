import pandas as pd
import cudf
import numpy as np
import time
import cuspatial


def haversine_vectorized(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371
    return c * r

def calculate_trip_metrics_pandas(file_path):
    timings = {}
    # t = time.perf_counter()
    pds_gps = pd.read_csv(file_path) 
    # timings['load_data'] = time.perf_counter() - t
    # Chuyển đổi cột 'timestamp' sang kiểu datetime bằng cudf
    pds_gps['timestamp'] = pd.to_datetime(pds_gps['timestamp'])
    
    t0 = time.perf_counter()
    pds_gps = pds_gps.sort_values(['trip_id', 'timestamp']).copy()
    timings['sort'] = time.perf_counter() - t0

    t1 = time.perf_counter()
    pds_gps['next_lat'] = pds_gps.groupby('trip_id')['latitude'].shift(-1)
    pds_gps['next_lon'] = pds_gps.groupby('trip_id')['longitude'].shift(-1)
    timings['shift'] = time.perf_counter() - t1

    t2 = time.perf_counter()
    pds_gps = pds_gps.dropna(subset=['next_lat', 'next_lon'])
    timings['dropna'] = time.perf_counter() - t2

    t3 = time.perf_counter()
    pds_gps['distance'] = haversine_vectorized(
        pds_gps['latitude'].values,
        pds_gps['longitude'].values,
        pds_gps['next_lat'].values,
        pds_gps['next_lon'].values
    )
    timings['haversine'] = time.perf_counter() - t3

    t4 = time.perf_counter()
    trip_distances = pds_gps.groupby('trip_id')['distance'].sum().reset_index()
    trip_times = pds_gps.groupby('trip_id').agg({
        'timestamp': ['first', 'last']
    })
    trip_times.columns = ['_'.join(col).strip() for col in trip_times.columns.values]
    trip_times = trip_times.reset_index()
    trip_times['duration_hours'] = (
        (trip_times['timestamp_last'] - trip_times['timestamp_first'])
        .dt.total_seconds() / 3600
    )
    timings['groupby'] = time.perf_counter() - t4

    t5 = time.perf_counter()
    trip_metrics = trip_distances.merge(
        trip_times[['trip_id', 'duration_hours']],
        on='trip_id'
    )
    trip_metrics['avg_speed_kmh'] = (
        trip_metrics['distance'] / trip_metrics['duration_hours']
    ).round(2)
    trip_metrics['total_distance_km'] = trip_metrics['distance'].round(2)
    trip_metrics['duration_hours'] = trip_metrics['duration_hours'].round(2)
    result = trip_metrics[['trip_id', 'total_distance_km', 'duration_hours', 'avg_speed_kmh']]
    timings['merge_calc'] = time.perf_counter() - t5

    timings['total'] = sum(timings.values())
    return result, timings

def calculate_trip_metrics_cudf(file_path):
    timings = {}
    # t = time.perf_counter()
    cudf_gps = cudf.read_csv(file_path)
    cudf_gps = cudf.DataFrame(cudf_gps)
    cudf_gps['timestamp'] = cudf.to_datetime(cudf_gps['timestamp'])
    # timings['load_data'] = time.perf_counter() - t
    
    t0 = time.perf_counter()
    cudf_gps = cudf_gps.sort_values(['trip_id', 'timestamp'])
    timings['sort'] = time.perf_counter() - t0

    t1 = time.perf_counter()
    cudf_gps['next_lat'] = cudf_gps.groupby('trip_id')['latitude'].shift(-1)
    cudf_gps['next_lon'] = cudf_gps.groupby('trip_id')['longitude'].shift(-1)
    timings['shift'] = time.perf_counter() - t1

    t2 = time.perf_counter()
    cudf_gps = cudf_gps.dropna(subset=['next_lat', 'next_lon'])
    timings['dropna'] = time.perf_counter() - t2
    
    
    t3 = time.perf_counter()
    # Convert coordinates to 1D arrays for cuSpatial
    points1 = cuspatial.GeoSeries.from_points_xy(
        cudf_gps[['longitude', 'latitude']].interleave_columns()
    )
    points2 = cuspatial.GeoSeries.from_points_xy(
        cudf_gps[['next_lon','next_lat']].interleave_columns()
    )
    cudf_gps['distance'] = cuspatial.haversine_distance(points1, points2)
    timings['haversine'] = time.perf_counter() - t3

    t4 = time.perf_counter()
    trip_distances = cudf_gps.groupby('trip_id')['distance'].sum().reset_index()
    trip_times = cudf_gps.groupby('trip_id').agg({
        'timestamp': ['first', 'last']
    })
    trip_times.columns = ['_'.join(col).strip() for col in trip_times.columns.values]
    trip_times = trip_times.reset_index()
    trip_times['duration_hours'] = (
        (trip_times['timestamp_last'] - trip_times['timestamp_first'])
        .dt.total_seconds() / 3600
    )
    timings['groupby'] = time.perf_counter() - t4

    t5 = time.perf_counter()
    trip_metrics = trip_distances.merge(
        trip_times[['trip_id', 'duration_hours']],
        on='trip_id'
    )
    trip_metrics['avg_speed_kmh'] = (
        trip_metrics['distance'] / trip_metrics['duration_hours']
    ).round(2)
    trip_metrics['total_distance_km'] = trip_metrics['distance'].round(2)
    trip_metrics['duration_hours'] = trip_metrics['duration_hours'].round(2)
    result = trip_metrics[['trip_id', 'total_distance_km', 'duration_hours', 'avg_speed_kmh']]
    timings['merge_calc'] = time.perf_counter() - t5

    timings['total'] = sum(timings.values())
    return result.to_pandas(), timings
