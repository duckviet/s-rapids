import streamlit as st
import json
import pydeck as pdk
import numpy as np
import pandas as pd
import cuspatial
import geopandas as gpd
from shapely.geometry import Point
import datetime
import time
from haversine import haversine
from modules.gps_analysis import load_gps_data, calculate_trip_metrics_traditional, calculate_trip_metrics_cuspatial
from modules.map_utils import load_geojson, create_district_layer, create_gps_layer, create_heatmap_layer
from modules.graph_analysis import analyze_movement_patterns, get_top_areas

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
    # Tạo layer cho các điểm GPS
    return pdk.Layer(
        "ScatterplotLayer",
        data=gps_data,
        get_position=['longitude', 'latitude'],
        get_radius=50,
        get_fill_color=[0, 0, 255, 180],  # Blue with some transparency
        pickable=True,
        auto_highlight=True,
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
    st.title("Phân tích dữ liệu GPS với cuSpatial và cuGraph")
    
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
        gps_data = load_gps_data("data/fake_hcmc_road_gps_data.csv")
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
    
    # Set initial view state (centered on HCMC)
    view_state = pdk.ViewState(
        latitude=10.7756587,  # Center of HCMC
        longitude=106.7004238,
        zoom=10,
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
    tab1, tab2, tab3 = st.tabs(["Phân tích GPS", "So sánh hiệu suất", "Phân tích đồ thị"])
    
    with tab1:
        # Sidebar controls for GPS analysis
        st.sidebar.subheader("Phân tích GPS")
        selected_trip = st.sidebar.selectbox("Chọn chuyến đi", gps_data['trip_id'].unique())
        
        # Tính toán và hiển thị các chỉ số của chuyến đi
        st.subheader("Phân tích chuyến đi")
        trip_metrics, _ = calculate_trip_metrics_cuspatial(gps_data)
        st.dataframe(trip_metrics)
        
        # Hiển thị biểu đồ tốc độ trung bình
        st.subheader("Biểu đồ tốc độ trung bình")
        st.bar_chart(trip_metrics.set_index('trip_id')['avg_speed_kmh'])
        
        # Hiển thị biểu đồ khoảng cách
        st.subheader("Biểu đồ khoảng cách di chuyển")
        st.bar_chart(trip_metrics.set_index('trip_id')['total_distance_km'])
        
        # Hiển thị thông tin chi tiết về chuyến đi đã chọn
        st.subheader("Chi tiết chuyến đi")
        trip_data = gps_data[gps_data['trip_id'] == selected_trip]
        st.write(f"Thời gian bắt đầu: {trip_data.iloc[0]['timestamp']}")
        st.write(f"Thời gian kết thúc: {trip_data.iloc[-1]['timestamp']}")
        st.write(f"Tốc độ trung bình: {trip_metrics[trip_metrics['trip_id'] == selected_trip]['avg_speed_kmh'].iloc[0]} km/h")
        st.write(f"Khoảng cách di chuyển: {trip_metrics[trip_metrics['trip_id'] == selected_trip]['total_distance_km'].iloc[0]} km")
    
    with tab2:
        # Sidebar controls for performance comparison
        st.sidebar.subheader("So sánh hiệu suất")
        show_traditional = st.sidebar.checkbox("Hiển thị kết quả phương pháp thông thường", value=True)
        show_cuspatial = st.sidebar.checkbox("Hiển thị kết quả cuSpatial", value=True)
        
        # So sánh hiệu suất giữa phương pháp thông thường và cuSpatial
        st.subheader("So sánh hiệu suất")
        
        # Tính toán metrics bằng cả hai phương pháp
        traditional_metrics, traditional_time = calculate_trip_metrics_traditional(gps_data)
        cuspatial_metrics, cuspatial_time = calculate_trip_metrics_cuspatial(gps_data)
        
        # Hiển thị thời gian thực thi
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Thời gian thực thi (phương pháp thông thường)", f"{traditional_time:.2f} giây")
        with col2:
            st.metric("Thời gian thực thi (cuSpatial)", f"{cuspatial_time:.2f} giây")
        
        # Tính toán và hiển thị tốc độ tăng
        speedup = traditional_time / cuspatial_time
        st.metric("Tốc độ tăng", f"{speedup:.2f}x")
        
        # Hiển thị kết quả phân tích
        st.subheader("Kết quả phân tích")
        
        # Tạo subtabs để so sánh kết quả
        subtab1, subtab2 = st.tabs(["Phương pháp thông thường", "cuSpatial"])
        
        with subtab1:
            if show_traditional:
                st.dataframe(traditional_metrics)
                st.bar_chart(traditional_metrics.set_index('trip_id')['avg_speed_kmh'])
        
        with subtab2:
            if show_cuspatial:
                st.dataframe(cuspatial_metrics)
                st.bar_chart(cuspatial_metrics.set_index('trip_id')['avg_speed_kmh'])
    
    with tab3:
        # Sidebar controls for graph analysis
        st.sidebar.subheader("Phân tích đồ thị")
        show_pagerank = st.sidebar.checkbox("Hiển thị PageRank", value=True)
        show_communities = st.sidebar.checkbox("Hiển thị cộng đồng", value=True)
        show_centrality = st.sidebar.checkbox("Hiển thị độ trung tâm", value=True)
        
        st.subheader("Phân tích mẫu di chuyển với cuGraph")
        
        # Phân tích mẫu di chuyển
        with st.spinner("Đang phân tích mẫu di chuyển..."):
            results = analyze_movement_patterns(gps_data)
        
        if show_pagerank:
            # Hiển thị kết quả PageRank
            st.subheader("Top 5 khu vực có ảnh hưởng lớn (PageRank)")
            top_pagerank = get_top_areas(results, 'pagerank')
            st.dataframe(top_pagerank)
        
        if show_communities:
            # Hiển thị kết quả phát hiện cộng đồng
            st.subheader("Phát hiện cộng đồng")
            communities = results['communities'].to_pandas()
            modularity = results['modularity']
            st.write(f"Số lượng cộng đồng phát hiện được: {communities['community_id'].nunique()}")
            st.write(f"Modularity score: {modularity:.4f}")
            st.dataframe(communities)
        
        if show_centrality:
            # Hiển thị kết quả độ trung tâm
            st.subheader("Top 5 khu vực quan trọng (Độ trung tâm)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("Độ trung tâm giữa (Betweenness Centrality)")
                st.write("Đo lường mức độ quan trọng của một khu vực dựa trên số lượng đường đi ngắn nhất đi qua nó")
                top_betweenness = get_top_areas(results, 'betweenness')
                st.dataframe(top_betweenness)
            
            with col2:
                st.write("Độ trung tâm eigenvector")
                st.write("Đo lường tầm quan trọng của một khu vực dựa trên tầm quan trọng của các khu vực kết nối với nó")
                top_eigenvector = get_top_areas(results, 'eigenvector')
                st.dataframe(top_eigenvector)
            
            st.write("PageRank")
            st.write("Đo lường tầm quan trọng của một khu vực dựa trên xác suất một người ngẫu nhiên sẽ đến thăm khu vực đó")
            top_pagerank = get_top_areas(results, 'pagerank')
            st.dataframe(top_pagerank)

if __name__ == "__main__":
    main() 