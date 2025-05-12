import osmnx as ox
import geopandas as gpd
import pandas as pd

def get_bus_stops_osm(place_name, distance=5000):
    """
    Lấy danh sách các trạm xe buýt từ OpenStreetMap trong một khu vực.
    place_name: Tên khu vực (ví dụ: "Ho Chi Minh City, Vietnam")
    distance: Khoảng cách từ tâm khu vực (mét), nếu cần giới hạn
    """
    # Thiết lập cấu hình OSMnx
    ox.settings.use_cache = True
    ox.settings.log_console = True

    # Lấy ranh giới khu vực
    try:
        # Tìm kiếm khu vực theo tên
        gdf_area = ox.geocode_to_gdf(place_name)
        
        # Lấy các trạm xe buýt với tag highway=bus_stop
        tags = {'highway': 'bus_stop'}
        gdf_bus_stops = ox.features_from_place(place_name, tags=tags)

        # Lọc dữ liệu để chỉ giữ các cột cần thiết
        bus_stops = []
        for idx, row in gdf_bus_stops.iterrows():
            # Kiểm tra nếu có tọa độ
            if row.geometry and row.geometry.type == 'Point':
                name = row.get('name', 'Unknown')
                lat = row.geometry.y
                lng = row.geometry.x
                bus_stops.append({
                    'name': name,
                    'latitude': lat,
                    'longitude': lng
                })

        return bus_stops

    except Exception as e:
        print(f"Lỗi: {e}")
        return []

# Ví dụ: Lấy trạm xe buýt ở TP.HCM
place_name = "Ho Chi Minh City, Vietnam"
bus_stops = get_bus_stops_osm(place_name)

# In kết quả
for stop in bus_stops:
    print(f"Trạm: {stop['name']}, Tọa độ: ({stop['latitude']}, {stop['longitude']})")

# Lưu vào file CSV
df = pd.DataFrame(bus_stops)
df.to_csv('bus_stops_osm_full.csv', index=False)
 