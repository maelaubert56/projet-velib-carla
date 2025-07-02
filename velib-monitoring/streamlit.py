import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import pymongo
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="Vélib' Paris - Real Time Monitoring",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

@st.cache_resource
def init_mongodb():
    """Initialize MongoDB connexion"""
    try:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/')
        mongo_db = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
        client = pymongo.MongoClient(mongo_uri)
        database = client[mongo_db]
        return database
    except Exception as e:
        st.error(f"Error of connexion MongoDB: {e}")
        return None

@st.cache_data(ttl=30)
def load_realtime_data():
    """Load real time data from MongoDB"""
    db = init_mongodb()
    if db is None:
        return pd.DataFrame()
    
    try:
        cursor = db.stations_realtime.find({}).limit(1500)
        data = list(cursor)
        
        if data:
            df = pd.DataFrame(data)
            if '_id' in df.columns:
                df = df.drop('_id', axis=1)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error during data loading: {e}")
        return pd.DataFrame()

def create_paris_map(df):
    """Creates a map of Paris with Vélib' stations"""
    if df.empty:
        return None
    
    # Paris centre
    paris_center = [48.8566, 2.3522]
    
    # Map creation
    m = folium.Map(location=paris_center, zoom_start=12)
    
    # Add stations (max 100)
    for idx, row in df.head(100).iterrows():
        if pd.notna(row.get('lat')) and pd.notna(row.get('lon')):
            # CColor depending on availibility 
            if row.get('occupancy_rate', 0) > 70:
                color = 'green'
                icon = 'ok-sign'
            elif row.get('occupancy_rate', 0) < 30:
                color = 'red'
                icon = 'warning-sign'
            else:
                color = 'orange'
                icon = 'info-sign'
            
            popup_text = f"""
            <b>{row.get('name', 'Station inconnue')}</b><br>
            Availables Bikes: {row.get('num_bikes_available', 0)}<br>
            Available Docks: {row.get('num_docks_available', 0)}<br>
            Total Capacity: {row.get('capacity', 0)}<br>
            Occupation Rate: {row.get('occupancy_rate', 0):.1f}%
            """
            
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
    
    return m

def main():
    """Streamlit Interface"""
    
    # En-tête
    st.title("🚴‍♂️ Vélib' Paris - Real Time Monitoring")
    st.markdown("---")
    
    # Sidebar for controls and settings
    st.sidebar.title("Controls")
    
    # Manually refresh the site via button
    if st.sidebar.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner("Data loading..."):
        realtime_df = load_realtime_data()
    
    # Check for data
    if realtime_df.empty:
        st.warning("No real time data is available")
        st.info("Vérifiez que le producer et le processeur sont démarrés.")
        return
    
    st.success(f"{len(realtime_df)} stations loaded successfully !")
    
    # principles metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_stations = len(realtime_df['station_id'].unique())
        st.metric("🚉 Active Stations", total_stations)
    
    with col2:
        total_bikes = int(realtime_df['num_bikes_available'].sum())
        st.metric("🚴 Available Bikes", total_bikes)
    
    with col3:
        total_docks = int(realtime_df['num_docks_available'].sum())
        st.metric("🅿️ Available Docks", total_docks)
    
    with col4:
        avg_occupancy = realtime_df['occupancy_rate'].mean()
        st.metric("📊 Average Occupation Rate", f"{avg_occupancy:.1f}%")
    
    st.markdown("---")
    
    # Onglets principaux
    tab1, tab2 = st.tabs(["🗺️ Map", "📈 Analysis"])
    
    with tab1:
        st.subheader("Velib stations map'")
        
        # Filtres pour la carte
        col1, col2 = st.columns(2)
        with col1:
            min_occupancy = st.slider("Minimum occupancy rate", 0, 100, 0)
        with col2:
            max_occupancy = st.slider("Maximum occupancy rate", 0, 100, 100)
        
        # Filtrer les données
        filtered_df = realtime_df[
            (realtime_df['occupancy_rate'] >= min_occupancy) &
            (realtime_df['occupancy_rate'] <= max_occupancy)
        ]
        
        st.info(f"Display of {len(filtered_df)} stations (max 100 for performance)")
        
        # Créer et afficher la carte
        if not filtered_df.empty:
            paris_map = create_paris_map(filtered_df)
            if paris_map:
                st_folium(paris_map, width=700, height=500)
        else:
            st.warning("No stations fit the corresponding filter.")
    
    with tab2:
        st.subheader("Data Analysis")
        
        # Graphique de distribution des vélos
        fig_hist = px.histogram(
            realtime_df,
            x='num_bikes_available',
            nbins=20,
            title="Distribution of available bikes number",
            labels={'num_bikes_available': 'Available bikes', 'count': 'Stations number'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Top stations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔝 Top 10 - Stations the most occupied")
            top_occupied = realtime_df.nlargest(10, 'occupancy_rate')[['name', 'occupancy_rate', 'num_bikes_available']]
            fig_top = px.bar(
                top_occupied,
                x='occupancy_rate',
                y='name',
                orientation='h',
                title="Occupation Rate (%)"
            )
            fig_top.update_layout(height=400)
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            st.subheader("🔻 Top 10 - Stations the less occupied")
            bottom_occupied = realtime_df.nsmallest(10, 'occupancy_rate')[['name', 'occupancy_rate', 'num_bikes_available']]
            fig_bottom = px.bar(
                bottom_occupied,
                x='occupancy_rate',
                y='name',
                orientation='h',
                title="Occupation Rate (%)",
                color_discrete_sequence=['orange']
            )
            fig_bottom.update_layout(height=400)
            st.plotly_chart(fig_bottom, use_container_width=True)
        
        # Tableau des données
        st.subheader("📊 Stations Data")
        
        # Sélection de colonnes à afficher
        columns_to_show = ['name', 'num_bikes_available', 'num_docks_available', 'capacity', 'occupancy_rate', 'status_category']
        display_df = realtime_df[columns_to_show].copy()
        display_df = display_df.round(1)
        
        st.dataframe(display_df, use_container_width=True, height=400)
    
    # Footer
    st.markdown("---")
    st.markdown("*Dashboard updated automatically every 30 seconds*")
    st.markdown(f"*Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()
