import streamlit as st
import pydeck as pdk
import cudf
from modules.map_utils import load_geojson, create_district_layer, create_gps_layer, create_heatmap_layer
from components.gps_analysis_tab import render_gps_analysis_tab
from components.performance_comparison_tab import render_performance_comparison_tab
from components.graph_analysis_tab import render_graph_analysis_tab
from components.bus_route_analysis_tab import render_bus_route_analysis_tab

def load_gps_data(file_path):
    """Đọc dữ liệu GPS từ file CSV bằng cudf"""
    # Đọc file CSV bằng cudf
    df = cudf.read_csv(file_path)
    
    # Chuyển đổi cột 'timestamp' sang kiểu datetime bằng cudf
    df['timestamp'] = cudf.to_datetime(df['timestamp'])
    
    return df.to_pandas()

def create_district_layer(districts):
    # Create a list to store polygon data
    polygons = []
    
    # Process each district
    for district in districts["level2s"]:
        # Get coordinates for each polygon in the district
        for polygon in district["coordinates"]:
            # Convert coordinates to the format expected by pydeck
            coords = polygon[0]  # Get the first (and only) ring of coordinates
            polygons.append({
                "name": district["name"],
                "id": district["level2_id"],
                "coordinates": coords
            })
    
    return pdk.Layer(
        "PolygonLayer",
        data=polygons,
        get_polygon="coordinates",
        get_fill_color=[255, 140, 0, 100],  # Orange with some transparency
        get_line_color=[0, 0, 0, 80],  # Black border
        get_line_width=2,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 140, 0, 200],  # Brighter orange when hovered
        extruded=False,
    )

def create_gps_layer(gps_data):
    # Group data by trip_id and create path coordinates
    trip_paths = []
    for trip_id in gps_data['trip_id'].unique():
        trip_points = gps_data[gps_data['trip_id'] == trip_id]
        # Create path coordinates for this trip
        path = trip_points[['longitude', 'latitude']].values.tolist()
        if len(path) > 1:  # Only add paths with more than one point
            trip_paths.append({
                'trip_id': str(trip_id),  # Convert to string to ensure JSON serialization
                'path': path
            })
    
    # Create layer for GPS paths
    return pdk.Layer(
        "PathLayer",
        data=trip_paths,
        get_path="path",
        get_color=[0, 0, 255, 180],  # Blue with some transparency
        get_width=3,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 0, 0, 180],  # Red highlight when hovered
    )

def create_heatmap_layer(gps_data):
    # Tạo layer cho heatmap
    return pdk.Layer(
        "HeatmapLayer",
        data=gps_data,
        get_position=['longitude', 'latitude'],
        aggregation="SUM",
        color_range=[
            [255, 0, 0, 0],
            [255, 0, 0, 255]
        ],
        threshold=0.1,
        pickable=True,
        auto_highlight=True,
    )

def main():
    st.title("Phân tích dữ liệu GPS với cuDf, cuSpatial và cuGraph")
    
    # Sidebar configuration
    st.sidebar.title("Cài đặt")
    
    # Map settings in sidebar
    st.sidebar.subheader("Cài đặt bản đồ")
    show_districts = st.sidebar.checkbox("Hiển thị quận", value=True)
    show_gps = st.sidebar.checkbox("Hiển thị điểm GPS", value=True)
    show_heatmap = st.sidebar.checkbox("Hiển thị heatmap", value=True)
    
    # Layer opacity settings
    st.sidebar.subheader("Độ trong suốt")
    district_opacity = st.sidebar.slider("Độ trong suốt quận", 0, 100, 100)
    gps_opacity = st.sidebar.slider("Độ trong suốt điểm GPS", 0, 100, 180)
    heatmap_opacity = st.sidebar.slider("Độ trong suốt heatmap", 0, 100, 100)
    
    # Load GeoJSON data
    try:
        districts = load_geojson("data/SGDistrict.geo.json")
    except Exception as e:
        st.error(f"Lỗi khi đọc file GeoJSON: {e}")
        return
    
    # Load GPS data
    try:
        gps_data = load_gps_data("data/fake_hcmc_road_gps_data_full.csv")
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu GPS: {e}")
        return
    
    # Create layers based on sidebar settings
    layers = []
    if show_districts:
        district_layer = create_district_layer(districts)
        district_layer.get_fill_color = [255, 140, 0, district_opacity]
        layers.append(district_layer)
    
    if show_gps:
        gps_layer = create_gps_layer(gps_data)
        gps_layer.get_fill_color = [0, 0, 255, gps_opacity]
        layers.append(gps_layer)
    
    if show_heatmap:
        heatmap_layer = create_heatmap_layer(gps_data)
        heatmap_layer.color_range = [
            [255, 0, 0, 0],
            [255, 0, 0, heatmap_opacity]
        ]
        layers.append(heatmap_layer)
    
    # Set initial view state (centered on Q9, HCMC)
    view_state = pdk.ViewState(
        latitude=10.833755,
        longitude=106.818759,
        zoom=13.5,
        pitch=0,
    )
    
    # Create the deck
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{name}</b>",
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "font-family": '"Helvetica Neue", Arial',
                "z-index": "10000"
            }
        }
    )
    
    # Display the map
    st.pydeck_chart(deck)
    
    # Hiển thị thông tin cơ bản về dữ liệu GPS
    st.subheader("Thông tin dữ liệu GPS")
    st.write(f"Tổng số điểm GPS: {len(gps_data)}")
    st.write(f"Tổng số chuyến đi: {gps_data['trip_id'].nunique()}")
    
    # Tạo tabs cho các phân tích khác nhau
    tab1, tab2, tab3 = st.tabs([ "So sánh hiệu suất", "Phân tích đồ thị", "Phân tích tuyến xe buýt"])
    
    with tab1:
        render_performance_comparison_tab("data/fake_hcmc_road_gps_data_full.csv")
    
    with tab2:
        render_graph_analysis_tab(gps_data)
    
    with tab3:
        render_bus_route_analysis_tab(gps_data, districts, layers, deck)

if __name__ == "__main__":
    main() 