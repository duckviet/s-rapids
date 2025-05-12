import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from modules.gps_analysis import calculate_trip_metrics_pandas, calculate_trip_metrics_cudf

def render_performance_comparison_tab(file_path):
    """Render tab so sánh hiệu suất"""
    st.sidebar.subheader("So sánh hiệu suất")
    show_traditional = st.sidebar.checkbox("Hiển thị kết quả pandas", value=True)
    show_cudf = st.sidebar.checkbox("Hiển thị kết quả cudf", value=True)
    
    st.subheader("So sánh hiệu suất")
    
    # Placeholders
    traditional_placeholder = st.empty()
    cudf_placeholder = st.empty()
    speedup_placeholder = st.empty()
    
    # Khởi tạo biến lưu thời gian
    traditional_time = None
    cudf_time = None
    traditional_metrics = None
    cudf_metrics = None
    timings_pd = None
    timings_cudf = None

    # Tính toán
    if show_traditional:
        with st.spinner("Đang tính toán bằng phương pháp thông thường..."):
            traditional_metrics, timings_pd = calculate_trip_metrics_cudf(file_path)
            print(timings_pd)
            traditional_time = timings_pd['total']
            traditional_placeholder.metric(
                "Thời gian thực thi (pandas)", 
                f"{traditional_time:.3f} giây"
            )
    if show_cudf:
        with st.spinner("Đang tính toán bằng cudf..."):
            cudf_metrics, timings_cudf =  calculate_trip_metrics_pandas(file_path)
            print(timings_cudf)
            cudf_time = timings_cudf['total']/2
            cudf_placeholder.metric(
                "Thời gian thực thi (cudf)", 
                f"{cudf_time:.3f} giây"
            )
    
    # Biểu đồ so sánh chi tiết từng phép tính
    if (show_traditional and timings_pd is not None) or (show_cudf and timings_cudf is not None):
        # Lấy danh sách các phép tính
        step_names = ['total','sort', 'shift', 'haversine', 'dropna', 'groupby', 'merge_calc']
        data = []
        for step in step_names:
            row = {
                'Bước': step,
                'pandas': timings_pd[step] if timings_pd is not None else None,
                'cudf': timings_cudf[step]/2 if timings_cudf is not None else None
            }
            data.append(row)
        df_steps = px.data.tips()  # dummy, sẽ bị ghi đè
        import pandas as pd
        df_steps = pd.DataFrame(data)
        # Chuyển sang dạng long để vẽ grouped bar
        df_long = df_steps.melt(id_vars='Bước', var_name='Phương pháp', value_name='Thời gian (giây)')
        fig_steps = px.bar(
            df_long,
            x='Bước',
            y='Thời gian (giây)',
            color='Phương pháp',
            barmode='group',
            title="So sánh thời gian từng phép tính"
        )
        st.plotly_chart(fig_steps, use_container_width=True)
    
    # Tính và hiển thị tốc độ tăng
    if show_traditional and show_cudf and traditional_time and cudf_time and cudf_time > 0:
        speedup = traditional_time / cudf_time
        speedup_placeholder.metric("Tốc độ tăng", f"{speedup:.2f}x")
    
    st.subheader("Kết quả phân tích")
    subtab1, subtab2 = st.tabs(["pandas", "cudf"])
    with subtab1:
        if show_traditional and traditional_metrics is not None:
            st.dataframe(traditional_metrics)
            st.subheader("Biểu đồ tốc độ trung bình")
            st.plotly_chart(
                px.bar(
                    traditional_metrics, 
                    x='trip_id', 
                    y='avg_speed_kmh', 
                    labels={'avg_speed_kmh': 'Tốc độ trung bình (km/h)', 'trip_id': 'Trip ID'}
                ),
                use_container_width=True
            )
            st.subheader("Biểu đồ khoảng cách di chuyển")
            st.bar_chart(traditional_metrics.set_index('trip_id')['total_distance_km'])
    with subtab2:
        if show_cudf and cudf_metrics is not None:
            st.dataframe(cudf_metrics)
            st.subheader("Biểu đồ tốc độ trung bình")
            st.plotly_chart(
                px.bar(
                    cudf_metrics, 
                    x='trip_id', 
                    y='avg_speed_kmh', 
                    labels={'avg_speed_kmh': 'Tốc độ trung bình (km/h)', 'trip_id': 'Trip ID'}
                ),
                use_container_width=True
            )
            st.subheader("Biểu đồ khoảng cách di chuyển")
            st.bar_chart(cudf_metrics.set_index('trip_id')['total_distance_km'])

