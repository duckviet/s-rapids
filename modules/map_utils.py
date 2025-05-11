import json
import pydeck as pdk

def load_geojson(file_path):
    """Đọc dữ liệu GeoJSON từ file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_district_layer(districts):
    """Tạo layer cho các quận"""
    polygons = []
    
    for district in districts["level2s"]:
        for polygon in district["coordinates"]:
            coords = polygon[0]
            polygons.append({
                "name": district["name"],
                "id": district["level2_id"],
                "coordinates": coords
            })
    
    return pdk.Layer(
        "PolygonLayer",
        data=polygons,
        get_polygon="coordinates",
        get_fill_color=[255, 140, 0, 100],
        get_line_color=[0, 0, 0, 80],
        get_line_width=2,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 140, 0, 200],
        extruded=False,
    )

def create_gps_layer(gps_data):
    """Tạo layer cho các điểm GPS"""
    return pdk.Layer(
        "ScatterplotLayer",
        data=gps_data,
        get_position=['longitude', 'latitude'],
        get_radius=50,
        get_fill_color=[0, 0, 255, 180],
        pickable=True,
        auto_highlight=True,
    )

def create_heatmap_layer(gps_data):
    """Tạo layer heatmap cho các điểm GPS"""
    return pdk.Layer(
        "HeatmapLayer",
        data=gps_data,
        get_position=['longitude', 'latitude'],
        get_weight='simulated_speed_kmh',
        radius_pixels=50,
        intensity=1,
        threshold=0.05,
        pickable=True,
    ) 