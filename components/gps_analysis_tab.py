import streamlit as st
from modules.gps_analysis import calculate_trip_metrics_cuspatial

def render_gps_analysis_tab(gps_data):
    """Render tab phân tích GPS"""
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