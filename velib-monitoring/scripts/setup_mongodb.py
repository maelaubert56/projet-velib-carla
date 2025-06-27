#!/usr/bin/env python3

"""
Script pour initialiser MongoDB avec les collections et index nécessaires
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Ajouter le chemin src au Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.mongo_utils import MongoManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Fonction principale"""
    # Charger les variables d'environnement
    load_dotenv()
    
    # Configuration MongoDB
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/')
    mongo_db = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
    
    logger.info("=== Initialisation de MongoDB pour Vélib' Monitoring ===")
    logger.info(f"URI MongoDB: {mongo_uri.split('@')[0]}@***")
    logger.info(f"Base de données: {mongo_db}")
    
    try:
        # Initialiser le gestionnaire MongoDB
        mongo_manager = MongoManager(mongo_uri, mongo_db)
        
        logger.info("✅ Connexion à MongoDB établie")
        
        # Créer les collections et index
        logger.info("Création des collections et index...")
        mongo_manager.create_collections_and_indexes()
        
        logger.info("✅ Collections et index créés avec succès")
        
        # Afficher les statistiques
        stats = mongo_manager.get_database_stats()
        if stats:
            logger.info("\n=== Statistiques de la Base de Données ===")
            logger.info(f"📊 Collections: {stats.get('database', {}).get('collections', 0)}")
            logger.info(f"💾 Taille des données: {stats.get('database', {}).get('dataSize', 0)} bytes")
            logger.info(f"🗂️  Taille des index: {stats.get('database', {}).get('indexSize', 0)} bytes")
            
            logger.info("\n=== Collections Créées ===")
            collections = ['stations_realtime', 'station_anomalies', 'usage_patterns']
            for collection in collections:
                if collection in stats:
                    count = stats[collection].get('count', 0)
                    size = stats[collection].get('size', 0)
                    logger.info(f"📝 {collection}: {count} documents ({size} bytes)")
        
        # Insérer des données de test (optionnel)
        if '--with-test-data' in sys.argv:
            logger.info("\n=== Insertion de Données de Test ===")
            insert_test_data(mongo_manager)
        
        logger.info("\n✅ Initialisation MongoDB terminée avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation MongoDB: {e}")
        return False
    finally:
        if 'mongo_manager' in locals():
            mongo_manager.close()

def insert_test_data(mongo_manager: MongoManager):
    """Insère des données de test"""
    from datetime import datetime
    
    # Données de test pour une station
    test_station_data = {
        'station_id': 'test_001',
        'name': 'Station Test - République',
        'lat': 48.8672,
        'lon': 2.3633,
        'capacity': 30,
        'num_bikes_available': 15,
        'num_docks_available': 15,
        'is_installed': 1,
        'is_renting': 1,
        'is_returning': 1,
        'last_reported': int(datetime.now().timestamp()),
        'timestamp': datetime.now().isoformat(),
        'ingestion_time': int(datetime.now().timestamp()),
        'occupancy_rate': 50.0,
        'availability_rate': 50.0,
        'is_full': False,
        'is_empty': False,
        'processing_time': datetime.now()
    }
    
    # Insérer dans stations_realtime
    try:
        mongo_manager.database.stations_realtime.insert_one(test_station_data)
        logger.info("✅ Données de test insérées dans stations_realtime")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion des données de test: {e}")
    
    # Données de test pour une anomalie
    test_anomaly_data = {
        'station_id': 'test_002',
        'name': 'Station Test - Anomalie',
        'anomaly_type': 'station_empty',
        'is_anomaly': True,
        'num_bikes_available': 0,
        'capacity': 25,
        'occupancy_rate': 0.0,
        'processing_time': datetime.now()
    }
    
    # Insérer dans station_anomalies
    try:
        mongo_manager.database.station_anomalies.insert_one(test_anomaly_data)
        logger.info("✅ Données de test insérées dans station_anomalies")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion des anomalies de test: {e}")

def show_usage():
    """Affiche l'aide d'utilisation"""
    print("""
Usage: python setup_mongodb.py [--with-test-data]

Ce script initialise MongoDB pour le monitoring Vélib':
- Crée les collections nécessaires
- Définit les index pour optimiser les performances
- Configure les règles de rétention (TTL)

Options:
--with-test-data    Insère des données de test

Collections créées:
- stations_realtime: Données temps réel des stations (TTL: 30 jours)
- station_anomalies: Anomalies détectées (TTL: 7 jours)  
- usage_patterns: Patterns d'usage agrégés (TTL: 90 jours)

Prérequis:
1. MongoDB doit être démarré: docker-compose up -d
2. Les variables d'environnement doivent être configurées dans .env

Variables d'environnement:
- MONGODB_URI (défaut: mongodb://admin:password123@localhost:27017/)
- MONGODB_DATABASE (défaut: velib_monitoring)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        show_usage()
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)
