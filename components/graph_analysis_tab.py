import streamlit as st
import cugraph
import cudf
import numpy as np
import pandas as pd
import cuml
import geopandas as gpd
from shapely.geometry import Point

def render_graph_analysis_tab(gps_data):
    """Render tab phân tích đồ thị"""
    st.sidebar.subheader("Phân tích đồ thị")
    show_pagerank = st.sidebar.checkbox("Hiển thị PageRank", value=True)
    show_communities = st.sidebar.checkbox("Hiển thị cộng đồng", value=True)
    show_centrality = st.sidebar.checkbox("Hiển thị độ trung tâm", value=True)
    
    st.subheader("Phân tích mẫu di chuyển với cuGraph")
    
    with st.spinner("Đang phân tích mẫu di chuyển..."):
        results = analyze_movement_patterns(gps_data)
    
    if results is None:
        st.error("Không thể phân tích mẫu di chuyển. Vui lòng kiểm tra dữ liệu hoặc tham số (thử giảm eps trong DBSCAN).")
        return
    
    if show_pagerank:
        st.subheader("Top 5 khu vực có ảnh hưởng lớn (PageRank)")
        top_pagerank = get_top_areas(results, 'pagerank')
        st.dataframe(top_pagerank)
    
    if show_communities:
        st.subheader("Phát hiện cộng đồng")
        communities = results['communities'].to_pandas()
        modularity = results['modularity']
        st.write(f"Số lượng cộng đồng phát hiện được: {communities['community_id'].nunique()}")
        st.write(f"Modularity score: {modularity:.4f}")
        st.dataframe(communities)
    
    if show_centrality:
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

def create_movement_graph(gps_data, eps=0.001, min_samples=2):
    """Tạo đồ thị di chuyển từ dữ liệu GPS"""
    st.write(f"Số điểm GPS: {len(gps_data)}")
    st.write(f"Số chuyến đi: {gps_data['trip_id'].nunique()}")
    
    # Tạo GeoDataFrame
    geometry = [Point(xy) for xy in zip(gps_data['longitude'], gps_data['latitude'])]
    gdf = gpd.GeoDataFrame(gps_data, geometry=geometry, crs="EPSG:4326")
    
    # Sử dụng cuml.DBSCAN
    coords = np.column_stack((gdf.geometry.x, gdf.geometry.y))
    coords_cudf = cudf.DataFrame(coords, columns=['longitude', 'latitude'])
    
    clustering = cuml.DBSCAN(eps=eps, min_samples=min_samples).fit(coords_cudf)
    gdf['cluster'] = clustering.labels_.values_host
    
    # Thống kê số cụm
    unique_clusters = np.unique(clustering.labels_)
    num_clusters = len(unique_clusters) - (1 if -1 in unique_clusters else 0)  # Trừ nhiễu
    st.write(f"Số cụm được phát hiện: {num_clusters}")
    st.write(f"Số điểm nhiễu: {(clustering.labels_ == -1).sum()}")
      
    # Tạo cạnh
    edges = []
    for trip_id in gps_data['trip_id'].unique():
        trip_data = gdf[gdf['trip_id'] == trip_id].sort_values('timestamp')
        if len(trip_data) > 1:
            for i in range(len(trip_data) - 1):
                source = trip_data.iloc[i]['cluster']
                target = trip_data.iloc[i + 1]['cluster']
                if source != -1 and target != -1:  # Bỏ qua điểm nhiễu
                    edges.append({
                        'source': int(source),
                        'target': int(target),
                        'weight': 1
                    })
    
    if not edges:
        st.warning("Không tạo được cạnh nào. Nguyên nhân có thể: 1) Chỉ có một cụm duy nhất, thử giảm eps (hiện tại eps=0.001); 2) Không có chuyển động giữa các cụm; 3) Dữ liệu không thay đổi tọa độ giữa các điểm liên tiếp.")
        return None, gdf
    
    st.write(f"Số cạnh được tạo: {len(edges)}")
    st.write(f"Số nút duy nhất: {len(set([e['source'] for e in edges] + [e['target'] for e in edges]))}")
    
    edges_df = cudf.DataFrame(edges)
    G = cugraph.Graph(directed=False)
    G.from_cudf_edgelist(edges_df, source='source', destination='target', edge_attr='weight', store_transposed=True)
    return G, gdf

def calculate_pagerank(G):
    if G is None or G.number_of_vertices() == 0:
        return cudf.DataFrame({'vertex': [], 'pagerank': []})
    pagerank = cugraph.pagerank(G)
    return pagerank

def detect_communities(G):
    if G is None or G.number_of_vertices() == 0:
        return cudf.DataFrame({'node_id': [], 'community_id': []}), 0.0
    communities = cugraph.louvain(G)  # Trả về tuple (DataFrame, modularity)
    communities_df = communities[0]  # Trích xuất DataFrame
    communities_df = communities_df.rename(columns={'vertex': 'node_id', 'partition': 'community_id'})
    modularity = communities[1] if len(communities) > 1 else 0.0
    return communities_df, modularity

def calculate_centrality(G):
    if G is None or G.number_of_vertices() == 0:
        return {
            'betweenness': cudf.DataFrame({'vertex': [], 'betweenness_centrality': []}),
            'eigenvector': cudf.DataFrame({'vertex': [], 'eigenvector_centrality': []}),
            'pagerank': cudf.DataFrame({'vertex': [], 'pagerank': []})
        }
    betweenness = cugraph.betweenness_centrality(G)
    eigenvector = cugraph.eigenvector_centrality(G)
    pagerank = cugraph.pagerank(G)
    return {'betweenness': betweenness, 'eigenvector': eigenvector, 'pagerank': pagerank}

def analyze_movement_patterns(gps_data):
    G, gdf = create_movement_graph(gps_data)
    if G is None:
        return None
    
    pagerank = calculate_pagerank(G)
    communities, modularity = detect_communities(G)
    centrality = calculate_centrality(G)
    
    results = {
        'pagerank': pagerank,
        'communities': communities,
        'modularity': modularity,
        'centrality': centrality,
        'graph': G,
        'gdf': gdf
    }
    return results

def get_top_areas(results, metric='pagerank', top_n=5):
    if results is None:
        return pd.DataFrame()
    if metric == 'pagerank':
        df = results['pagerank'].to_pandas()
        return df.nlargest(top_n, 'pagerank') if not df.empty else pd.DataFrame()
    elif metric == 'betweenness':
        df = results['centrality']['betweenness'].to_pandas()
        return df.nlargest(top_n, 'betweenness_centrality') if not df.empty else pd.DataFrame()
    elif metric == 'eigenvector':
        df = results['centrality']['eigenvector'].to_pandas()
        return df.nlargest(top_n, 'eigenvector_centrality') if not df.empty else pd.DataFrame()