import json
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.api_client import VelibAPIClient

# Charger les variables d'environnement
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VelibKafkaProducer:
    """Producer Kafka pour les données Vélib'"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.api_url = os.getenv('VELIB_API_URL')
        self.update_interval = int(os.getenv('UPDATE_INTERVAL', '30'))
        
        # Initialiser le client API
        self.api_client = VelibAPIClient(self.api_url)
        
        # Initialiser le producer Kafka
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            retry_backoff_ms=100,
            request_timeout_ms=20000,
            max_in_flight_requests_per_connection=1
        )
        
        # Topics Kafka
        self.topics = {
            'station_status': 'station_status_topic',
            'available_bikes': 'available_bikes_topic',
            'available_docks': 'available_docks_topic',
            'station_info': 'station_info_topic'
        }
        
        logger.info("VelibKafkaProducer initialisé")
    
    def send_to_kafka(self, topic: str, key: str, value: Dict[Any, Any]):
        """Envoie un message vers Kafka"""
        try:
            future = self.producer.send(topic, key=key, value=value)
            self.producer.flush()  # Assure l'envoi immédiat
            return True
        except KafkaError as e:
            logger.error(f"Erreur Kafka pour topic {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur générale pour topic {topic}: {e}")
            return False
    
    def process_station_data(self, stations_data: Dict):
        """Traite et envoie les données des stations vers Kafka"""
        timestamp = datetime.now().isoformat()
        
        for station in stations_data['stations']:
            station_id = station['station_id']
            
            # Données complètes de la station
            station_status = {
                'station_id': station_id,
                'name': station.get('name', ''),
                'lat': station.get('lat', 0),
                'lon': station.get('lon', 0),
                'capacity': station.get('capacity', 0),
                'num_bikes_available': station.get('num_bikes_available', 0),
                'num_docks_available': station.get('num_docks_available', 0),
                'is_installed': station.get('is_installed', 0),
                'is_renting': station.get('is_renting', 0),
                'is_returning': station.get('is_returning', 0),
                'last_reported': station.get('last_reported', 0),
                'timestamp': timestamp,
                'ingestion_time': int(time.time())
            }
            
            # Envoyer vers le topic principal
            self.send_to_kafka(
                self.topics['station_status'],
                station_id,
                station_status
            )
            
            # Envoyer vers les topics spécialisés
            bikes_data = {
                'station_id': station_id,
                'available_bikes': station.get('num_bikes_available', 0),
                'capacity': station.get('capacity', 0),
                'occupancy_rate': (station.get('num_bikes_available', 0) / max(station.get('capacity', 1), 1)) * 100,
                'timestamp': timestamp
            }
            
            docks_data = {
                'station_id': station_id,
                'available_docks': station.get('num_docks_available', 0),
                'capacity': station.get('capacity', 0),
                'availability_rate': (station.get('num_docks_available', 0) / max(station.get('capacity', 1), 1)) * 100,
                'timestamp': timestamp
            }
            
            self.send_to_kafka(
                self.topics['available_bikes'],
                station_id,
                bikes_data
            )
            
            self.send_to_kafka(
                self.topics['available_docks'],
                station_id,
                docks_data
            )
    
    def run(self):
        """Démarre la boucle principale de production"""
        logger.info("Démarrage du producer Vélib'")
        
        def data_callback(stations_data):
            """Callback appelé quand de nouvelles données arrivent"""
            try:
                self.process_station_data(stations_data)
                logger.info(f"Données traitées pour {len(stations_data['stations'])} stations")
            except Exception as e:
                logger.error(f"Erreur lors du traitement des données: {e}")
        
        try:
            # Démarrer le monitoring avec callback
            self.api_client.monitor_stations(data_callback, self.update_interval)
        except KeyboardInterrupt:
            logger.info("Arrêt du producer")
        finally:
            self.producer.close()
            logger.info("Producer fermé")

def main():
    """Fonction principale"""
    producer = VelibKafkaProducer()
    producer.run()

if __name__ == "__main__":
    main()
