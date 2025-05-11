import streamlit as st
import json
import pydeck as pdk
import numpy as np
import pandas as pd

def load_geojson():
    with open("data/SGDistrict.geo.json", "r", encoding="utf-8") as f:
        return json.load(f)

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

def main():
    st.title("Bản đồ các quận TP.HCM")
    
    # Load GeoJSON data
    try:
        districts = load_geojson()
    except Exception as e:
        st.error(f"Lỗi khi đọc file GeoJSON: {e}")
        return
    
    # Create the district layer
    district_layer = create_district_layer(districts)
    
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
        layers=[district_layer],
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
    
    # Display district information
    st.subheader("Danh sách các quận")
    district_info = pd.DataFrame([
        {
            "ID": d["level2_id"],
            "Tên quận": d["name"]
        }
        for d in districts["level2s"]
    ])
    st.dataframe(district_info)

if __name__ == "__main__":
    main() 