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

# Configuration de la page
st.set_page_config(
    page_title="Vélib' Paris - Monitoring Temps Réel",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Charger les variables d'environnement
load_dotenv()

@st.cache_resource
def init_mongodb():
    """Initialise la connexion MongoDB"""
    try:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/')
        mongo_db = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
        client = pymongo.MongoClient(mongo_uri)
        database = client[mongo_db]
        return database
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return None

@st.cache_data(ttl=30)
def load_realtime_data():
    """Charge les données temps réel depuis MongoDB"""
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
        st.error(f"Erreur lors du chargement des données: {e}")
        return pd.DataFrame()

def create_paris_map(df):
    """Crée une carte de Paris avec les stations"""
    if df.empty:
        return None
    
    # Centre de Paris
    paris_center = [48.8566, 2.3522]
    
    # Créer la carte
    m = folium.Map(location=paris_center, zoom_start=12)
    
    # Ajouter les stations (limiter à 100 pour performance)
    for idx, row in df.head(100).iterrows():
        if pd.notna(row.get('lat')) and pd.notna(row.get('lon')):
            # Couleur selon la disponibilité
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
            Vélos disponibles: {row.get('num_bikes_available', 0)}<br>
            Docks disponibles: {row.get('num_docks_available', 0)}<br>
            Capacité totale: {row.get('capacity', 0)}<br>
            Taux d'occupation: {row.get('occupancy_rate', 0):.1f}%
            """
            
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
    
    return m

def main():
    """Interface principale Streamlit"""
    
    # En-tête
    st.title("🚴‍♂️ Vélib' Paris - Monitoring Temps Réel")
    st.markdown("---")
    
    # Sidebar pour les contrôles
    st.sidebar.title("Contrôles")
    
    # Bouton de refresh manuel
    if st.sidebar.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()
    
    # Charger les données
    with st.spinner("Chargement des données..."):
        realtime_df = load_realtime_data()
    
    # Vérifier si on a des données
    if realtime_df.empty:
        st.warning("⚠️ Aucune donnée temps réel disponible.")
        st.info("Vérifiez que le producer et le processeur sont démarrés.")
        return
    
    # Message de succès
    st.success(f"✅ {len(realtime_df)} stations chargées avec succès !")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_stations = len(realtime_df['station_id'].unique())
        st.metric("🚉 Stations actives", total_stations)
    
    with col2:
        total_bikes = int(realtime_df['num_bikes_available'].sum())
        st.metric("🚴 Vélos disponibles", total_bikes)
    
    with col3:
        total_docks = int(realtime_df['num_docks_available'].sum())
        st.metric("🅿️ Docks disponibles", total_docks)
    
    with col4:
        avg_occupancy = realtime_df['occupancy_rate'].mean()
        st.metric("📊 Taux d'occupation moyen", f"{avg_occupancy:.1f}%")
    
    st.markdown("---")
    
    # Onglets principaux
    tab1, tab2 = st.tabs(["🗺️ Carte", "📈 Analyse"])
    
    with tab1:
        st.subheader("Carte des stations Vélib'")
        
        # Filtres pour la carte
        col1, col2 = st.columns(2)
        with col1:
            min_occupancy = st.slider("Taux d'occupation minimum", 0, 100, 0)
        with col2:
            max_occupancy = st.slider("Taux d'occupation maximum", 0, 100, 100)
        
        # Filtrer les données
        filtered_df = realtime_df[
            (realtime_df['occupancy_rate'] >= min_occupancy) &
            (realtime_df['occupancy_rate'] <= max_occupancy)
        ]
        
        st.info(f"Affichage de {len(filtered_df)} stations (max 100 pour performance)")
        
        # Créer et afficher la carte
        if not filtered_df.empty:
            paris_map = create_paris_map(filtered_df)
            if paris_map:
                st_folium(paris_map, width=700, height=500)
        else:
            st.warning("Aucune station ne correspond aux filtres sélectionnés.")
    
    with tab2:
        st.subheader("Analyse des données")
        
        # Graphique de distribution des vélos
        fig_hist = px.histogram(
            realtime_df,
            x='num_bikes_available',
            nbins=20,
            title="Distribution du nombre de vélos disponibles",
            labels={'num_bikes_available': 'Vélos disponibles', 'count': 'Nombre de stations'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Top stations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔝 Top 10 - Stations les plus occupées")
            top_occupied = realtime_df.nlargest(10, 'occupancy_rate')[['name', 'occupancy_rate', 'num_bikes_available']]
            fig_top = px.bar(
                top_occupied,
                x='occupancy_rate',
                y='name',
                orientation='h',
                title="Taux d'occupation (%)"
            )
            fig_top.update_layout(height=400)
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            st.subheader("🔻 Top 10 - Stations les moins occupées")
            bottom_occupied = realtime_df.nsmallest(10, 'occupancy_rate')[['name', 'occupancy_rate', 'num_bikes_available']]
            fig_bottom = px.bar(
                bottom_occupied,
                x='occupancy_rate',
                y='name',
                orientation='h',
                title="Taux d'occupation (%)",
                color_discrete_sequence=['orange']
            )
            fig_bottom.update_layout(height=400)
            st.plotly_chart(fig_bottom, use_container_width=True)
        
        # Tableau des données
        st.subheader("📊 Données des stations")
        
        # Sélection de colonnes à afficher
        columns_to_show = ['name', 'num_bikes_available', 'num_docks_available', 'capacity', 'occupancy_rate', 'status_category']
        display_df = realtime_df[columns_to_show].copy()
        display_df = display_df.round(1)
        
        st.dataframe(display_df, use_container_width=True, height=400)
    
    # Footer
    st.markdown("---")
    st.markdown("*Dashboard mis à jour automatiquement toutes les 30 secondes*")
    st.markdown(f"*Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()
