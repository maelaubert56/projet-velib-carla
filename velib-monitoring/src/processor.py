#!/usr/bin/env python3

"""
Processeur Python pour lire Kafka et écrire dans MongoDB
Processeur simple et efficace pour éviter les problèmes de compatibilité
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any
from datetime import datetime

# Ajouter le chemin src au Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from kafka import KafkaConsumer
from utils.mongo_utils import MongoManager
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VelibKafkaToMongoProcessor:
    """Processeur simple Kafka vers MongoDB"""
    
    def __init__(self):
        # Charger les variables d'environnement
        load_dotenv()
        
        # Configuration Kafka
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        
        # Configuration MongoDB
        self.mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/?authSource=admin')
        self.mongo_db_name = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
        
        # Topics à traiter
        self.topics = [
            'station_status_topic',
            'available_bikes_topic',
            'available_docks_topic',
            'station_info_topic'
        ]
        
        # Initialiser MongoDB
        self.mongo_manager = MongoManager(self.mongo_uri, self.mongo_db_name)
        
        logger.info(f"Processeur initialisé - Kafka: {self.kafka_servers}")
        logger.info(f"Topics surveillés: {self.topics}")
    
    def create_consumer(self, topics: List[str]) -> KafkaConsumer:
        """Crée un consumer Kafka"""
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.kafka_servers,
            group_id='velib_mongo_processor_v2',  # Nouveau groupe pour relire depuis le début
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest',  # Lire depuis le début
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            # consumer_timeout_ms=None  # Pas de timeout, rester en vie
        )
    
    def process_station_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite et enrichit les données de station"""
        processed = data.copy()
        
        # Ajouter timestamp de traitement
        processed['processed_timestamp'] = datetime.utcnow().isoformat()
        
        # Calculer des métriques
        if 'num_bikes_available' in data and 'capacity' in data:
            bikes = int(data['num_bikes_available'])
            capacity = int(data['capacity'])
            
            processed['availability_rate'] = round(bikes / capacity * 100, 2) if capacity > 0 else 0
            processed['occupancy_rate'] = round((capacity - bikes) / capacity * 100, 2) if capacity > 0 else 0
            
            # Classifications
            if bikes == 0:
                processed['status_category'] = 'empty'
            elif bikes / capacity < 0.2:
                processed['status_category'] = 'low'
            elif bikes / capacity > 0.8:
                processed['status_category'] = 'full'
            else:
                processed['status_category'] = 'normal'
        
        return processed
    
    def save_to_mongo(self, topic: str, data: Dict[str, Any]):
        """Sauvegarde les données dans MongoDB selon le topic"""
        try:
            processed_data = self.process_station_data(data)
            
            if topic == 'station_status_topic':
                # Données temps réel des stations
                collection = self.mongo_manager.get_collection('stations_realtime')
                
                # Upsert basé sur station_id
                filter_query = {'station_id': processed_data.get('station_id')}
                
                collection.replace_one(
                    filter_query,
                    processed_data,
                    upsert=True
                )
                
            elif topic in ['available_bikes_topic', 'available_docks_topic']:
                # Données de disponibilité - garder historique
                collection = self.mongo_manager.get_collection('availability_history')
                
                processed_data['topic_source'] = topic
                collection.insert_one(processed_data)
                
            elif topic == 'station_info_topic':
                # Informations statiques des stations
                collection = self.mongo_manager.get_collection('stations_info')
                
                filter_query = {'station_id': processed_data.get('station_id')}
                collection.replace_one(
                    filter_query,
                    processed_data,
                    upsert=True
                )
            
            logger.debug(f"Données sauvegardées: {topic} - Station {processed_data.get('station_id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde MongoDB pour {topic}: {e}")
    
    def process_messages(self):
        """Traite les messages Kafka en continu"""
        logger.info("🚀 Démarrage du processeur Kafka vers MongoDB")
        
        # Créer le consumer
        consumer = self.create_consumer(self.topics)
        
        message_count = 0
        last_log_time = time.time()
        
        try:
            for message in consumer:
                try:
                    topic = message.topic
                    value = message.value
                    
                    if value:
                        self.save_to_mongo(topic, value)
                        message_count += 1
                        
                        # Log périodique
                        current_time = time.time()
                        if current_time - last_log_time > 30:  # Toutes les 30 secondes
                            logger.info(f"📊 Messages traités: {message_count}")
                            last_log_time = current_time
                            
                            # Statistiques MongoDB
                            stats = self.get_mongo_stats()
                            logger.info(f"📄 Documents MongoDB: {stats}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Erreur décodage JSON: {e}")
                except Exception as e:
                    logger.error(f"Erreur traitement message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur dans le processeur: {e}")
        finally:
            logger.info("🔄 Fermeture du consumer Kafka")
            consumer.close()
            self.mongo_manager.close()
    
    def get_mongo_stats(self) -> Dict[str, int]:
        """Récupère les statistiques MongoDB"""
        try:
            stats = {}
            collections = ['stations_realtime', 'availability_history', 'stations_info']
            
            for coll_name in collections:
                collection = self.mongo_manager.get_collection(coll_name)
                count = collection.count_documents({})
                stats[coll_name] = count
                
            return stats
        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return {}

def main():
    """Fonction principale"""
    processor = VelibKafkaToMongoProcessor()
    processor.process_messages()

if __name__ == "__main__":
    main()
