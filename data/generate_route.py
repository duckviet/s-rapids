import pandas as pd
import random

def create_random_bus_routes(csv_file, num_routes=150, min_stops=3, max_stops=10):
    """
    Tạo các tuyến xe buýt ngẫu nhiên và trả về mảng các tuple (lat1, lon1, lat2, lon2).
    csv_file: Đường dẫn đến file CSV (có cột name, latitude, longitude)
    num_routes: Số lượng tuyến xe buýt muốn tạo
    min_stops: Số trạm tối thiểu trên mỗi tuyến
    max_stops: Số trạm tối đa trên mỗi tuyến
    """
    # Đọc file CSV
    df = pd.read_csv(csv_file)
    
    # Lấy danh sách tất cả trạm
    bus_stops = df[['name', 'latitude', 'longitude']].to_dict('records')
    
    # Mảng chứa các tuple (lat1, lon1, lat2, lon2)
    segments = []
    
    # Tạo các tuyến xe buýt ngẫu nhiên
    for route_id in range(1, num_routes + 1):
        # Random số lượng trạm cho tuyến này
        num_stops = random.randint(min_stops, max_stops)
        
        # Random chọn các trạm (không lặp lại)
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
    
    return segments

# Đường dẫn đến file CSV
csv_file = 'bus_stops_osm.csv'

# Tạo các tuyến xe buýt ngẫu nhiên và lấy mảng segments
segments = create_random_bus_routes(csv_file, num_routes=200, min_stops=3, max_stops=5)

# In kết quả
print("Mảng các tuple (lat1, lon1, lat2, lon2):")
for segment in segments:
    print(segment)

# (Tùy chọn) Lưu vào file CSV nếu cần
import pandas as pd
df_segments = pd.DataFrame(segments, columns=['lat1', 'lon1', 'lat2', 'lon2'])
df_segments.to_csv('bus_route_segments.csv', index=False)