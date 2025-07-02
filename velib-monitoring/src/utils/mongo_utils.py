import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoManager:
    """Manager for MongoDB operations"""
    
    def __init__(self, uri: str, database_name: str):
        self.uri = uri
        self.database_name = database_name
        self.client = None
        self.database = None
        self.connect()
    
    def connect(self):
        """Establishes the connection to MongoDB"""
        try:
            self.client = MongoClient(self.uri)
            self.database = self.client[self.database_name]
            
            # Test de connexion
            self.client.admin.command('ping')
            logger.info(f"Connexion MongoDB established to {self.database_name}")
            
        except Exception as e:
            logger.error(f"Error of connexion MongoDB: {e}")
            raise
    
    def get_collection(self, collection_name: str):
        """Returns a MongoDB collection"""
        return self.database[collection_name]
    
    def create_collections_and_indexes(self):
        """Creates the necessary collections and indexes"""
        try:
            # Collection stations_realtime
            stations_realtime = self.database.stations_realtime
            
            # Index for temporal queries
            stations_realtime.create_index([
                ("station_id", pymongo.ASCENDING),
                ("processing_time", pymongo.DESCENDING)
            ])
            
            stations_realtime.create_index([
                ("processing_time", pymongo.DESCENDING)
            ])
            
            # Geospatial index
            stations_realtime.create_index([
                ("lat", pymongo.ASCENDING),
                ("lon", pymongo.ASCENDING)
            ])
            
            # TTL index to automatically delete old data (30 days)
            stations_realtime.create_index(
                "processing_time",
                expireAfterSeconds=30 * 24 * 60 * 60  # 30 jours
            )
            
        except Exception as e:
            logger.error(f"Error while creating collections/indexes: {e}")
            raise
    
    
    def cleanup_old_data(self, days: int = 30):
        """Cleans up old data (older than 30 days)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clean up stations_realtime
            result1 = self.database.stations_realtime.delete_many(
                {"processing_time": {"$lt": cutoff_date}}
            )
            
        except Exception as e:
            logger.error(f"Cleaning error: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la base de données"""
        try:
            stats = {}
            
            # Statistiques générales
            db_stats = self.database.command("dbStats")
            stats['database'] = {
                'collections': db_stats.get('collections', 0),
                'dataSize': db_stats.get('dataSize', 0),
                'indexSize': db_stats.get('indexSize', 0),
                'storageSize': db_stats.get('storageSize', 0)
            }
            
            # Comptage des documents par collection
            collections = ['stations_realtime', 'station_anomalies', 'usage_patterns']
            for collection in collections:
                stats[collection] = {
                    'count': self.database[collection].count_documents({}),
                    'size': self.database.command("collStats", collection).get('size', 0)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Connexion MongoDB fermée")
