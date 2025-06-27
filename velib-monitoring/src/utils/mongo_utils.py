import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MongoManager:
    """Gestionnaire pour les opérations MongoDB"""
    
    def __init__(self, uri: str, database_name: str):
        self.uri = uri
        self.database_name = database_name
        self.client = None
        self.database = None
        self.connect()
    
    def connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(self.uri)
            self.database = self.client[self.database_name]
            
            # Test de connexion
            self.client.admin.command('ping')
            logger.info(f"Connexion MongoDB établie vers {self.database_name}")
            
        except Exception as e:
            logger.error(f"Erreur de connexion MongoDB: {e}")
            raise
    
    def get_collection(self, collection_name: str):
        """Retourne une collection MongoDB"""
        return self.database[collection_name]
    
    def create_collections_and_indexes(self):
        """Crée les collections et les index nécessaires"""
        try:
            # Collection stations_realtime
            stations_realtime = self.database.stations_realtime
            
            # Index pour les requêtes temporelles
            stations_realtime.create_index([
                ("station_id", pymongo.ASCENDING),
                ("processing_time", pymongo.DESCENDING)
            ])
            
            stations_realtime.create_index([
                ("processing_time", pymongo.DESCENDING)
            ])
            
            # Index géospatial
            stations_realtime.create_index([
                ("lat", pymongo.ASCENDING),
                ("lon", pymongo.ASCENDING)
            ])
            
            # TTL index pour supprimer automatiquement les vieilles données (30 jours)
            stations_realtime.create_index(
                "processing_time",
                expireAfterSeconds=30 * 24 * 60 * 60  # 30 jours
            )
            
            # Collection station_anomalies
            station_anomalies = self.database.station_anomalies
            
            station_anomalies.create_index([
                ("station_id", pymongo.ASCENDING),
                ("processing_time", pymongo.DESCENDING)
            ])
            
            station_anomalies.create_index([
                ("anomaly_type", pymongo.ASCENDING),
                ("processing_time", pymongo.DESCENDING)
            ])
            
            # TTL index pour les anomalies (7 jours)
            station_anomalies.create_index(
                "processing_time",
                expireAfterSeconds=7 * 24 * 60 * 60  # 7 jours
            )
            
            # Collection usage_patterns
            usage_patterns = self.database.usage_patterns
            
            usage_patterns.create_index([
                ("station_id", pymongo.ASCENDING),
                ("window_start", pymongo.DESCENDING)
            ])
            
            usage_patterns.create_index([
                ("window_start", pymongo.DESCENDING)
            ])
            
            # TTL index pour les patterns (90 jours)
            usage_patterns.create_index(
                "window_start",
                expireAfterSeconds=90 * 24 * 60 * 60  # 90 jours
            )
            
            logger.info("Collections et index créés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des collections/index: {e}")
            raise
    
    def get_latest_station_data(self, limit: int = 1000) -> List[Dict]:
        """Récupère les données les plus récentes des stations"""
        try:
            cursor = self.database.stations_realtime.find(
                {},
                sort=[("processing_time", -1)]
            ).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données: {e}")
            return []
    
    def get_station_history(self, station_id: str, hours: int = 24) -> List[Dict]:
        """Récupère l'historique d'une station sur les N dernières heures"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            cursor = self.database.stations_realtime.find(
                {
                    "station_id": station_id,
                    "processing_time": {"$gte": start_time}
                },
                sort=[("processing_time", 1)]
            )
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}")
            return []
    
    def get_anomalies(self, hours: int = 24, anomaly_type: Optional[str] = None) -> List[Dict]:
        """Récupère les anomalies des N dernières heures"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = {"processing_time": {"$gte": start_time}}
            if anomaly_type:
                query["anomaly_type"] = anomaly_type
            
            cursor = self.database.station_anomalies.find(
                query,
                sort=[("processing_time", -1)]
            )
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des anomalies: {e}")
            return []
    
    def get_usage_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Calcule les statistiques d'usage des N dernières heures"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            pipeline = [
                {"$match": {"processing_time": {"$gte": start_time}}},
                {"$group": {
                    "_id": None,
                    "total_stations": {"$addToSet": "$station_id"},
                    "avg_bikes": {"$avg": "$num_bikes_available"},
                    "avg_docks": {"$avg": "$num_docks_available"},
                    "avg_occupancy": {"$avg": "$occupancy_rate"},
                    "total_capacity": {"$sum": "$capacity"},
                    "total_bikes": {"$sum": "$num_bikes_available"},
                    "total_docks": {"$sum": "$num_docks_available"}
                }},
                {"$project": {
                    "total_stations": {"$size": "$total_stations"},
                    "avg_bikes": 1,
                    "avg_docks": 1,
                    "avg_occupancy": 1,
                    "total_capacity": 1,
                    "total_bikes": 1,
                    "total_docks": 1
                }}
            ]
            
            result = list(self.database.stations_realtime.aggregate(pipeline))
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {}
    
    def get_top_stations(self, metric: str = "occupancy_rate", limit: int = 10, ascending: bool = False) -> List[Dict]:
        """Récupère le top des stations selon une métrique"""
        try:
            sort_order = 1 if ascending else -1
            
            pipeline = [
                {"$group": {
                    "_id": "$station_id",
                    "name": {"$first": "$name"},
                    "avg_metric": {"$avg": f"${metric}"},
                    "lat": {"$first": "$lat"},
                    "lon": {"$first": "$lon"},
                    "capacity": {"$first": "$capacity"}
                }},
                {"$sort": {"avg_metric": sort_order}},
                {"$limit": limit}
            ]
            
            return list(self.database.stations_realtime.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du top stations: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """Nettoie les données anciennes (au-delà de N jours)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Nettoyer stations_realtime
            result1 = self.database.stations_realtime.delete_many(
                {"processing_time": {"$lt": cutoff_date}}
            )
            
            # Nettoyer station_anomalies (7 jours)
            anomaly_cutoff = datetime.now() - timedelta(days=7)
            result2 = self.database.station_anomalies.delete_many(
                {"processing_time": {"$lt": anomaly_cutoff}}
            )
            
            logger.info(f"Nettoyage terminé: {result1.deleted_count} documents realtime, "
                       f"{result2.deleted_count} anomalies supprimées")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
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
