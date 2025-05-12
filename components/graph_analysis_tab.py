import streamlit as st
from modules.graph_analysis import analyze_movement_patterns, get_top_areas

def render_graph_analysis_tab(gps_data):
    """Render tab phân tích đồ thị"""
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