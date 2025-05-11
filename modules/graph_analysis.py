import cugraph
import cudf
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
import cuml
import geopandas as gpd
from shapely.geometry import Point

def create_movement_graph(gps_data, eps=0.01, min_samples=5):
    """Tạo đồ thị di chuyển từ dữ liệu GPS"""
    # Tạo GeoDataFrame (giữ nguyên vì cần cho geospatial)
    geometry = [Point(xy) for xy in zip(gps_data['longitude'], gps_data['latitude'])]
    gdf = gpd.GeoDataFrame(gps_data, geometry=geometry, crs="EPSG:4326")
    
    # Sử dụng cuml.DBSCAN thay vì sklearn
    coords = np.column_stack((gdf.geometry.x, gdf.geometry.y))
    coords_cudf = cudf.DataFrame(coords, columns=['longitude', 'latitude'])
    
    clustering = cuml.DBSCAN(eps=eps, min_samples=min_samples).fit(coords_cudf)
    # Convert labels to numpy array directly
    gdf['cluster'] = clustering.labels_.values_host
    
    # Phần còn lại giữ nguyên, nhưng thêm kiểm tra
    edges = []
    for trip_id in gps_data['trip_id'].unique():
        trip_data = gdf[gdf['trip_id'] == trip_id].sort_values('timestamp')
        
        for i in range(len(trip_data) - 1):
            source = trip_data.iloc[i]['cluster']
            target = trip_data.iloc[i+1]['cluster']
            if source != -1 and target != -1:  # Bỏ qua các điểm nhiễu
                edges.append({
                    'source': int(source),  # Đảm bảo là số nguyên
                    'target': int(target),
                    'weight': 1
                })
    
    # Kiểm tra xem edges có dữ liệu không trước khi tạo cuDF
    if not edges:
        raise ValueError("Không có cạnh nào được tạo. Kiểm tra dữ liệu đầu vào.")
    
    edges_df = cudf.DataFrame(edges)
    
    # Tạo đồ thị với store_transposed=True để tối ưu hiệu suất
    G = cugraph.Graph(directed=False)
    G.from_cudf_edgelist(edges_df, source='source', destination='target', edge_attr='weight', store_transposed=True)
    
    return G, gdf

def calculate_pagerank(G):
    """Tính toán PageRank cho các nút trong đồ thị"""
    pagerank = cugraph.pagerank(G)
    return pagerank

def detect_communities(G):
    """Phát hiện cộng đồng trong đồ thị"""
    communities, modularity = cugraph.louvain(G)
    # Đổi tên cột để dễ hiểu hơn
    communities = communities.rename(columns={'vertex': 'node_id', 'partition': 'community_id'})
    return communities, modularity

def calculate_centrality(G):
    """Tính toán các độ đo trung tâm"""
    # Tính độ trung tâm giữa (Betweenness Centrality)
    betweenness = cugraph.betweenness_centrality(G)
    
    # Tính độ trung tâm eigenvector
    eigenvector = cugraph.eigenvector_centrality(G)
    
    # Tính PageRank (có thể được sử dụng như một độ đo trung tâm)
    pagerank = cugraph.pagerank(G)
    
    return {
        'betweenness': betweenness,
        'eigenvector': eigenvector,
        'pagerank': pagerank
    }

def analyze_movement_patterns(gps_data):
    """Phân tích mẫu di chuyển sử dụng cuGraph"""
    # Tạo đồ thị
    G, gdf = create_movement_graph(gps_data)
    
    # Tính toán các metrics
    pagerank = calculate_pagerank(G)
    communities, modularity = detect_communities(G)
    centrality = calculate_centrality(G)
    
    # Kết hợp kết quả
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
    """Lấy top N khu vực theo metric"""
    if metric == 'pagerank':
        df = results['pagerank'].to_pandas()
        return df.nlargest(top_n, 'pagerank')
    elif metric == 'betweenness':
        df = results['centrality']['betweenness'].to_pandas()
        return df.nlargest(top_n, 'betweenness_centrality')
    elif metric == 'eigenvector':
        df = results['centrality']['eigenvector'].to_pandas()
        return df.nlargest(top_n, 'eigenvector_centrality') 