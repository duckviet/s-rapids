import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import random
import datetime
from shapely.geometry import Point, LineString
import os
from osmnx import projection
import geopandas as gpd

# --- Cấu hình ---
place_name = "Ho Chi Minh City, Vietnam"
network_type = "drive"  # Mạng lưới đường cho xe cơ giới
min_speed_kmh = 20  # Tốc độ giả định tối thiểu (km/h)
max_speed_kmh = 50  # Tốc độ giả định tối đa (km/h)
sampling_interval_seconds = 20  # Khoảng thời gian lấy mẫu GPS (giây)
gps_noise_meters = 10  # Mức độ nhiễu GPS giả định (mét)

# Điểm bắt đầu và kết thúc
csv_file = 'bus_route_segments.csv'
df = pd.read_csv(csv_file)
data_points = [(row['lat1'], row['lon1'], row['lat2'], row['lon2']) for _, row in df.iterrows()]
# (lat1, lon1, lat2, lon2) 

# Đường dẫn để lưu và tải đồ thị
graph_file = "hcmc_graph.graphml"
projected_graph_file = "hcmc_graph_projected.graphml"

# Khoảng thời gian tạo dữ liệu (bắt đầu từ 1 tuần trước)
start_time_base = datetime.datetime.now() - datetime.timedelta(days=7)

# --- Hàm hỗ trợ ---
def add_gps_noise(latitude, longitude, noise_meters):
    """Thêm nhiễu ngẫu nhiên vào tọa độ Lat/Lon (ước tính)."""
    lat_noise_deg = noise_meters / 111000 * random.uniform(-1, 1)
    lon_noise_deg = noise_meters / (111000 * abs(np.cos(np.radians(latitude)))) * random.uniform(-1, 1)
    return latitude + lat_noise_deg, longitude + lon_noise_deg

# --- Tải hoặc xử lý mạng lưới đường bộ --- 
print(f"Kiểm tra xem mạng lưới đường bộ đã được lưu chưa...")

if os.path.exists(graph_file) and os.path.exists(projected_graph_file):
    print(f"Đồ thị đã tồn tại. Đang tải từ '{graph_file}' và '{projected_graph_file}'...")
    G = ox.load_graphml(graph_file)
    G_proj = ox.load_graphml(projected_graph_file)
    print(f"Đã tải đồ thị từ file. CRS của đồ thị dự án: {G_proj.graph['crs']}")
else:
    print(f"Đang tải mạng lưới đường bộ '{network_type}' cho '{place_name}'...")
    G = ox.graph_from_place(place_name, network_type=network_type)
    print("Đã tải đồ thị.")

    G_proj = ox.project_graph(G)
    print(f"Đã dự án đồ thị sang hệ tọa độ: {G_proj.graph['crs']}")

    print(f"Lưu đồ thị vào '{graph_file}' và '{projected_graph_file}'...")
    ox.save_graphml(G, graph_file)
    ox.save_graphml(G_proj, projected_graph_file)
    print("Đã lưu đồ thị.")

# --- Tạo dữ liệu GPS giả cho nhiều chuyến đi ---
all_gps_points = []

print(f"\nĐang tạo {len(data_points)} chuyến đi...")

for trip_id, (lat1, lon1, lat2, lon2) in enumerate(data_points, 1):
    print(f"\nChuyến đi {trip_id}: từ ({lat1}, {lon1}) đến ({lat2}, {lon2})")
    
    try:
        # Tìm nút gần nhất với điểm bắt đầu và kết thúc
        origin_node = ox.distance.nearest_nodes(G, lon1, lat1)  # (lon, lat)
        destination_node = ox.distance.nearest_nodes(G, lon2, lat2)  # (lon, lat)

        # Tìm đường đi ngắn nhất (theo độ dài) giữa 2 nút
        route = nx.shortest_path(G_proj, origin_node, destination_node, weight='length')

        # Lấy thông tin chi tiết về các cạnh (đoạn đường) trên tuyến đường
        route_edges = []
        for u, v in zip(route[:-1], route[1:]):
            edge_data = G_proj.get_edge_data(u, v, 0)
            if edge_data:
                # Lưu thêm u, v vào edge_data để sử dụng sau
                edge_data['u'] = u
                edge_data['v'] = v
                route_edges.append(edge_data)

        # Kiểm tra khoảng cách tuyến đường
        route_length_m = sum(edge['length'] for edge in route_edges)
        route_length_km = route_length_m / 1000
        print(f"Khoảng cách tuyến đường: {route_length_km:.2f} km")

        # --- Mô phỏng di chuyển dọc theo tuyến đường ---
        trip_speed_kmh = random.uniform(min_speed_kmh, max_speed_kmh)
        trip_speed_ms = trip_speed_kmh * 1000 / 3600  # Tốc độ theo m/s

        # Ước tính thời lượng chuyến đi (giây)
        estimated_duration_seconds = route_length_m / trip_speed_ms
        num_points = int(estimated_duration_seconds / sampling_interval_seconds)
        if num_points < 2:
            print("Chuyến đi quá ngắn để tạo ít nhất 2 điểm GPS. Bỏ qua.")
            continue

        # Thời gian bắt đầu chuyến đi
        trip_start_time = start_time_base + datetime.timedelta(minutes=(trip_id-1)*5)
        current_time = trip_start_time

        # Lấy tất cả các điểm tọa độ trên tuyến đường (từ geometry của các cạnh)
        route_points_proj = []
        for edge in route_edges:
            if 'geometry' in edge and isinstance(edge['geometry'], LineString):
                route_points_proj.extend(list(edge['geometry'].coords))
            else:
                # Sử dụng u, v đã lưu trong edge_data
                u, v = edge['u'], edge['v']
                if u in G_proj.nodes and v in G_proj.nodes:
                    route_points_proj.append((G_proj.nodes[u]['x'], G_proj.nodes[u]['y']))
                    route_points_proj.append((G_proj.nodes[v]['x'], G_proj.nodes[v]['y']))

        if not route_points_proj:
            print(f"Không có geometry cho tuyến đường {trip_id}. Bỏ qua.")
            continue

        # Xử lý trường hợp các điểm trùng lặp tại các nút giao
        unique_route_points_proj = []
        seen_points = set()
        for p in route_points_proj:
            if p not in seen_points:
                unique_route_points_proj.append(p)
                seen_points.add(p)

        if len(unique_route_points_proj) < 2:
            print(f"Tuyến đường {trip_id} quá ngắn sau khi xử lý điểm trùng. Bỏ qua.")
            continue

        route_line_proj = LineString(unique_route_points_proj)
        total_route_length_proj = route_line_proj.length
        distance_per_interval_m = trip_speed_ms * sampling_interval_seconds
        current_distance_on_line_m = 0

        # Thêm điểm bắt đầu
        origin_gdf = gpd.GeoDataFrame(
            [{'geometry': Point(G_proj.nodes[origin_node]['x'], G_proj.nodes[origin_node]['y'])}],
            crs=G_proj.graph['crs']
        )
        origin_lat_lon = projection.project_gdf(
            origin_gdf,
            to_crs='EPSG:4326'
        ).iloc[0]['geometry']

        noisy_lat, noisy_lon = add_gps_noise(origin_lat_lon.y, origin_lat_lon.x, gps_noise_meters)
        all_gps_points.append({
            'trip_id': trip_id,
            'timestamp': current_time,
            'latitude': noisy_lat,
            'longitude': noisy_lon,
            'simulated_speed_kmh': trip_speed_kmh
        })
        current_time += datetime.timedelta(seconds=sampling_interval_seconds)

        # Mô phỏng di chuyển và tạo các điểm trung gian
        while current_distance_on_line_m < total_route_length_proj:
            target_distance_on_line_m = current_distance_on_line_m + distance_per_interval_m
            if target_distance_on_line_m > total_route_length_proj:
                target_distance_on_line_m = total_route_length_proj

            fraction = target_distance_on_line_m / total_route_length_proj
            if fraction > 1.0:
                fraction = 1.0

            interpolated_point_proj = route_line_proj.interpolate(fraction, normalized=True)
            point_gdf = gpd.GeoDataFrame(
                [{'geometry': interpolated_point_proj}],
                crs=G_proj.graph['crs']
            )
            point_lat_lon = projection.project_gdf(
                point_gdf,
                to_crs='EPSG:4326'
            ).iloc[0]['geometry']

            noisy_lat, noisy_lon = add_gps_noise(point_lat_lon.y, point_lat_lon.x, gps_noise_meters)
            all_gps_points.append({
                'trip_id': trip_id,
                'timestamp': current_time,
                'latitude': noisy_lat,
                'longitude': noisy_lon,
                'simulated_speed_kmh': trip_speed_kmh
            })

            current_distance_on_line_m = target_distance_on_line_m
            current_time += datetime.timedelta(seconds=sampling_interval_seconds)

            if current_distance_on_line_m >= total_route_length_proj:
                break

        # Thêm điểm kết thúc
        dest_gdf = gpd.GeoDataFrame(
            [{'geometry': Point(G_proj.nodes[destination_node]['x'], G_proj.nodes[destination_node]['y'])}],
            crs=G_proj.graph['crs']
        )
        destination_lat_lon = projection.project_gdf(
            dest_gdf,
            to_crs='EPSG:4326'
        ).iloc[0]['geometry']

        if not all_gps_points or (
            abs(all_gps_points[-1]['latitude'] - destination_lat_lon.y) > 1e-5 or
            abs(all_gps_points[-1]['longitude'] - destination_lat_lon.x) > 1e-5
        ):
            noisy_lat, noisy_lon = add_gps_noise(destination_lat_lon.y, destination_lat_lon.x, gps_noise_meters)
            all_gps_points.append({
                'trip_id': trip_id,
                'timestamp': current_time,
                'latitude': noisy_lat,
                'longitude': noisy_lon,
                'simulated_speed_kmh': trip_speed_kmh
            })

        print(
            f"Đã tạo chuyến đi {trip_id} với {len([p for p in all_gps_points if p['trip_id'] == trip_id])} điểm GPS "
            f"(độ dài {route_length_km:.2f} km, tốc độ {trip_speed_kmh:.2f} km/h)."
        )

    except nx.NetworkXNoPath:
        print(f"Không tìm thấy đường đi cho chuyến {trip_id}. Bỏ qua.")
        continue
    except Exception as e:
        print(f"Lỗi khi tạo chuyến đi {trip_id}: {e}. Bỏ qua.")
        continue

# --- Tạo DataFrame và Lưu ---
if all_gps_points:
    gps_df = pd.DataFrame(all_gps_points)
    gps_df = gps_df.sort_values(by=['trip_id', 'timestamp']).reset_index(drop=True)

    print("\nDữ liệu GPS giả tạo (trên mạng lưới đường bộ TP.HCM):")
    print(gps_df.head())
    print("\n...")
    print(gps_df.tail())

    output_filename = 'fake_hcmc_road_gps_data.csv'
    gps_df.to_csv(output_filename, index=False)
    print(f"\nDữ liệu đã được lưu vào file '{output_filename}'")
else:
    print("\nKhông có chuyến đi nào được tạo thành công.")