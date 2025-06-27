import requests
import json
import time
from typing import Dict, List, Optional
import logging
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Désactiver les warnings SSL pour les certificats auto-signés
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VelibAPIClient:
    """Client pour l'API Vélib' Métropole avec gestion SSL flexible"""
    
    def __init__(self, base_url: str = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Configuration SSL flexible
        self.session.verify = False  # Désactiver la vérification SSL stricte
        
        # Headers
        self.session.headers.update({
            'User-Agent': 'VelibMonitoring/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Configuration des retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # URLs alternatives si l'URL principale ne fonctionne pas
        self.alternative_urls = [
            "https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole",
            "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
        ]
    
    def get_station_information(self) -> Optional[Dict]:
        """Récupère les informations statiques des stations"""
        for base_url in [self.base_url] + self.alternative_urls:
            try:
                url = f"{base_url}/station_information.json"
                logger.info(f"Tentative de récupération depuis: {base_url}")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()
                logger.info(f"✅ Succès: {len(data.get('data', {}).get('stations', []))} stations récupérées")
                return data
            except Exception as e:
                logger.warning(f"⚠️ Échec avec {base_url}: {e}")
                continue
        
        logger.error("❌ Impossible de récupérer les informations stations depuis toutes les URLs")
        return None
    
    def get_station_status(self) -> Optional[Dict]:
        """Récupère le statut en temps réel des stations"""
        for base_url in [self.base_url] + self.alternative_urls:
            try:
                url = f"{base_url}/station_status.json"
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()
                logger.info(f"✅ Statut récupéré: {len(data.get('data', {}).get('stations', []))} stations")
                return data
            except Exception as e:
                logger.warning(f"⚠️ Échec statut avec {base_url}: {e}")
                continue
        
        logger.error("❌ Impossible de récupérer le statut depuis toutes les URLs")
        return None
    
    def get_all_stations_data(self) -> Optional[Dict]:
        """Récupère toutes les données des stations (infos + statut)"""
        try:
            station_info = self.get_station_information()
            station_status = self.get_station_status()
            
            if not station_info or not station_status:
                logger.error("❌ Impossible de récupérer les données station_info ou station_status")
                return None
            
            # Vérifier la structure des données
            info_data = station_info.get('data', {})
            status_data = station_status.get('data', {})
            
            if not info_data.get('stations') or not status_data.get('stations'):
                logger.error("❌ Structure de données invalide dans la réponse API")
                return None
            
            # Créer un dictionnaire des informations par station_id
            stations_info_dict = {
                station['station_id']: station 
                for station in info_data['stations']
            }
            
            # Enrichir les données de statut avec les informations statiques
            enriched_data = []
            current_timestamp = int(time.time())
            
            for status in status_data['stations']:
                station_id = status.get('station_id')
                if station_id and station_id in stations_info_dict:
                    combined_data = {
                        **stations_info_dict[station_id],
                        **status,
                        'timestamp': current_timestamp,
                        'last_updated': status.get('last_updated', current_timestamp)
                    }
                    enriched_data.append(combined_data)
            
            logger.info(f"✅ Données enrichies pour {len(enriched_data)} stations")
            
            return {
                'last_updated': station_status.get('last_updated', current_timestamp),
                'ttl': station_status.get('ttl', 60),
                'data_timestamp': current_timestamp,
                'stations': enriched_data
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur dans get_all_stations_data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def monitor_stations(self, callback, interval: int = 30):
        """Monitore les stations et appelle le callback avec les nouvelles données"""
        logger.info(f"Démarrage du monitoring des stations (intervalle: {interval}s)")
        
        while True:
            try:
                data = self.get_all_stations_data()
                if data and 'stations' in data and len(data['stations']) > 0:
                    callback(data)
                    logger.info(f"✅ Données envoyées pour {len(data['stations'])} stations")
                else:
                    logger.warning("⚠️ Aucune donnée valide récupérée")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt du monitoring (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans le monitoring: {e}")
                logger.error(f"Type d'erreur: {type(e).__name__}")
                # Attendre un peu avant de réessayer
                time.sleep(min(interval, 10))
