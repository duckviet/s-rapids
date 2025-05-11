import cudf
import cugraph
import cuspatial
import numpy as np

def test_cuspatial():
    print("\n=== Testing cuSpatial Point-in-Polygon ===")
    
    # Read data
    try:
        points_df = cudf.read_csv("data/points.csv", header=0, names=["lon", "lat"],
                                 dtype=["float64", "float64"]).dropna()
        poly_df = cudf.read_csv("data/polygon.csv", header=0, 
                               names=["lon", "lat", "ring_id", "poly_id"],
                               dtype=["float64", "float64", "int32", "int32"]).dropna()
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return

    # Print data summary
    print(f"\nPoints data (rows: {len(points_df)}):")
    print(points_df.head().to_pandas())
    print(f"\nPolygon data (rows: {len(poly_df)}):")
    print(poly_df.head().to_pandas())
    
    # Prepare polygon data (stay in cudf)
    x = poly_df["lon"].round(6)  # Round to 6 decimal places
    y = poly_df["lat"].round(6)
    
    # Calculate offsets using cudf
    poly_changes = poly_df["poly_id"].ne(poly_df["poly_id"].shift(1)).fillna(True)
    ring_changes = (poly_df["ring_id"].ne(poly_df["ring_id"].shift(1)) | poly_changes).fillna(True)
    poly_offsets = poly_df.index[poly_changes].to_numpy(dtype=np.int32)
    ring_offsets = poly_df.index[ring_changes].to_numpy(dtype=np.int32)
    
    # Create GeoSeries for polygons
    try:
        polygons_gs = cuspatial.GeoSeries.from_polygons_xy(
            x.to_numpy(), y.to_numpy(),
            ring_offsets, poly_offsets
        )
    except Exception as e:
        print(f"Error creating polygons GeoSeries: {e}")
        return
    
    # Prepare points data (stay in cudf)
    points_df["lon"] = points_df["lon"].round(6)
    points_df["lat"] = points_df["lat"].round(6)
    points_xy = points_df[["lon", "lat"]].values.flatten()  # Interleaved [x1, y1, x2, y2, ...]
    
    # Create GeoSeries for points
    try:
        points_gs = cuspatial.GeoSeries.from_points_xy(points_xy)
    except Exception as e:
        print(f"Error creating points GeoSeries: {e}")
        return
    
    # Run point-in-polygon test
    try:
        pip_result = cuspatial.point_in_polygon(points_gs, polygons_gs)
        pip_result_pd = pip_result.to_pandas()
        
        # Assign polygon_id to each point
        points_pd = points_df.to_pandas()
        points_pd["polygon_id"] = pip_result_pd.apply(
            lambda row: next((i for i, v in enumerate(row) if v), -1), axis=1
        )
        
        print("\nPoint-in-Polygon Results:")
        print(points_pd)
    except Exception as e:
        print(f"Error in point-in-polygon test: {e}")
        return

def test_cugraph():
    print("\n=== Testing cuGraph PageRank ===")
    
    # Read edge list
    try:
        edges_df = cudf.read_csv("data/edgelist.csv", header=0, dtype=["int32", "int32"])
    except Exception as e:
        print(f"Error reading edgelist CSV: {e}")
        return
    
    print("\nEdge list:")
    print(edges_df.to_pandas())
    
    # Create graph
    try:
        G = cugraph.Graph()
        G.from_cudf_edgelist(edges_df, source="src", destination="dst")
        
        # Run PageRank
        pagerank_df = cugraph.pagerank(G)
        
        print("\nPageRank Results:")
        print(pagerank_df.to_pandas())
    except Exception as e:
        print(f"Error in cuGraph PageRank: {e}")
        return

if __name__ == "__main__":
    print("Starting tests...")
    test_cuspatial()
    test_cugraph()
    print("\nAll tests completed!")