import streamlit as st
from modules.gps_analysis import calculate_trip_metrics_traditional, calculate_trip_metrics_cuspatial

def render_performance_comparison_tab(gps_data):
    """Render tab so sánh hiệu suất"""
    # Sidebar controls for performance comparison
    st.sidebar.subheader("So sánh hiệu suất")
    show_traditional = st.sidebar.checkbox("Hiển thị kết quả phương pháp thông thường", value=True)
    show_cuspatial = st.sidebar.checkbox("Hiển thị kết quả cuSpatial", value=True)
    
    # So sánh hiệu suất giữa phương pháp thông thường và cuSpatial
    st.subheader("So sánh hiệu suất")
    
    # Create placeholders for results
    traditional_placeholder = st.empty()
    cuspatial_placeholder = st.empty()
    speedup_placeholder = st.empty()
    
    # Calculate traditional metrics first
    if show_traditional:
        with st.spinner("Đang tính toán bằng phương pháp thông thường..."):
            traditional_metrics, traditional_time = calculate_trip_metrics_traditional(gps_data)
            traditional_placeholder.metric("Thời gian thực thi (phương pháp thông thường)", f"{traditional_time:.2f} giây")
    
    # Calculate cuSpatial metrics
    if show_cuspatial:
        with st.spinner("Đang tính toán bằng cuSpatial..."):
            cuspatial_metrics, cuspatial_time = calculate_trip_metrics_cuspatial(gps_data)
            cuspatial_placeholder.metric("Thời gian thực thi (cuSpatial)", f"{cuspatial_time:.2f} giây")
    
    # Calculate and show speedup if both methods are enabled
    if show_traditional and show_cuspatial:
        speedup = traditional_time / cuspatial_time
        speedup_placeholder.metric("Tốc độ tăng", f"{speedup:.2f}x")
    
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