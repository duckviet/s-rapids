import streamlit as st
import pydeck as pdk
from modules.bus_route_analysis import analyze_bus_routes, get_route_summary

def render_bus_route_analysis_tab(gps_data, districts, layers, deck):
    """Render tab phân tích tuyến xe buýt"""
    st.subheader("Phân tích tuyến xe buýt")
    
    # Phân tích tuyến xe buýt
    with st.spinner("Đang phân tích tuyến xe buýt..."):
        route_analysis = analyze_bus_routes(gps_data, districts)
        route_summary = get_route_summary(route_analysis)
    
    # Hiển thị tổng quan về các tuyến xe buýt
    st.subheader("Tổng quan các tuyến xe buýt")
    st.write(f"Tổng số tuyến xe buýt: {len(route_analysis)}")
    
    # Hiển thị bảng thống kê các tuyến theo quận
    st.subheader("Thống kê tuyến xe buýt theo quận")
    st.dataframe(route_summary)
    
    # Hiển thị chi tiết từng tuyến
    st.subheader("Chi tiết các tuyến xe buýt")
    st.dataframe(route_analysis)
    
    # Tạo bản đồ hiển thị các tuyến xe buýt
    st.subheader("Bản đồ các tuyến xe buýt")
    
    # Tạo layer cho các tuyến xe buýt
    bus_routes = []
    # Convert cuDF DataFrame to pandas before iteration
    route_analysis_pd = route_analysis.to_pandas()
    for _, row in route_analysis_pd.iterrows():
        bus_routes.append({
            'trip_id': str(row['trip_id']),
            'path': [[row['start_lon'], row['start_lat']], [row['end_lon'], row['end_lat']]],
            'start_district': row['start_district'],
            'end_district': row['end_district']
        })
    
    # Tạo layer cho các tuyến xe buýt
    bus_route_layer = pdk.Layer(
        "PathLayer",
        data=bus_routes,
        get_path="path",
        get_color=[255, 0, 0, 180],  # Red with some transparency
        get_width=3,
        pickable=True,
        auto_highlight=True,
        highlight_color=[0, 0, 255, 180],  # Blue highlight when hovered
    )
    
    # Thêm layer vào bản đồ
    layers.append(bus_route_layer)
    
    # Cập nhật bản đồ
    deck.layers = layers
    st.pydeck_chart(deck) 