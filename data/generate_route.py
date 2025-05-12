import cudf as cd  # Sử dụng cudf thay vì pandas
import random
import osmnx as ox
import geopandas as gpd  # Vẫn cần cho osmnx
import pandas as pd  # Có thể cần để chuyển đổi nếu osmnx yêu cầu

def create_random_bus_routes(csv_file, num_routes=150, min_stops=3, max_stops=10):
    """
    Tạo các tuyến xe buýt ngẫu nhiên và trả về mảng các tuple (lat1, lon1, lat2, lon2).
    csv_file: Đường dẫn đến file CSV (có cột name, latitude, longitude)
    num_routes: Số lượng tuyến xe buýt muốn tạo
    min_stops: Số trạm tối thiểu trên mỗi tuyến
    max_stops: Số trạm tối đa trên mỗi tuyến
    """
    # Đọc file CSV bằng cudf để tăng tốc
    df = cd.read_csv(csv_file)
    
    # Chuyển đổi sang list để sử dụng random.sample
    bus_stops = df[['name', 'latitude', 'longitude']].to_pandas().to_dict('records')
    
    # Mảng chứa các tuple (lat1, lon1, lat2, lon2)
    segments = []
    
    # Tạo các tuyến xe buýt ngẫu nhiên
    for route_id in range(1, num_routes + 1):
        # Random số lượng trạm cho tuyến này
        num_stops = random.randint(min_stops, max_stops)
        
        # Random chọn các trạm (không lặp lại) - vẫn dùng random vì cudf không hỗ trợ
        selected_stops = random.sample(bus_stops, k=min(num_stops, len(bus_stops)))
        
        # Tạo các đoạn tuyến (lat1, lon1, lat2, lon2) từ các trạm liên tiếp
        for i in range(len(selected_stops) - 1):
            stop1 = selected_stops[i]
            stop2 = selected_stops[i + 1]
            segment = (
                stop1['latitude'],
                stop1['longitude'],
                stop2['latitude'],
                stop2['longitude']
            )
            segments.append(segment)
    
    # Chuyển segments thành cudf DataFrame để trả về
    return cd.DataFrame(segments, columns=['lat1', 'lon1', 'lat2', 'lon2'])

# Đường dẫn đến file CSV
csv_file = 'bus_stops_osm_full.csv'

# Tạo các tuyến xe buýt ngẫu nhiên và lấy DataFrame segments
segments_df = create_random_bus_routes(csv_file, num_routes=2000, min_stops=3, max_stops=5)

# In kết quả (chuyển sang pandas để in dễ dàng, vì cudf có thể không hiển thị tốt)
print("Mảng các tuple (lat1, lon1, lat2, lon2):")
print(segments_df.to_pandas().head())  # In vài hàng đầu

# (Tùy chọn) Lưu vào file CSV
segments_df.to_pandas().to_csv('bus_route_segments_full.csv', index=False)  # Chuyển sang pandas để lưu
