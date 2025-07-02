#!/usr/bin/env python3

"""
Script to initialize MongoDB with the necessary collections and indexes
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the src path to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.mongo_utils import MongoManager

# Logging configuration
logging.basicConfig(
    filename='../logs/app.log',  # Nom du fichier de log
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to initialize MongoDB for Vélib' monitoring"""
    # Load environment variables from .env file
    load_dotenv()
    
    # MongoDB configuration
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/')
    mongo_db = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
    
    logger.info("=== Initializing MongoDB for Vélib' Monitoring ===")
    logger.info(f"URI MongoDB: {mongo_uri.split('@')[0]}@***")
    logger.info(f"Database: {mongo_db}")
    
    try:
        # Initialize MongoDB manager
        mongo_manager = MongoManager(mongo_uri, mongo_db)
        logger.info("Establish MongoDB connection...")
        
        # Create collections and indexes
        mongo_manager.create_collections_and_indexes()
        logger.info("Collections and indexes created successfully !")
        
        # Display statistics
        stats = mongo_manager.get_database_stats()
        if stats:
            logger.info("\n=== Stats of the database ===")
            logger.info(f"* Collections: {stats.get('database', {}).get('collections', 0)}")
            logger.info(f"* Data size: {stats.get('database', {}).get('dataSize', 0)} bytes")
            logger.info(f"* Index size: {stats.get('database', {}).get('indexSize', 0)} bytes")
            
            logger.info("\n=== Created Collections ===")
            collections = ['stations_realtime']
            for collection in collections:
                if collection in stats:
                    count = stats[collection].get('count', 0)
                    size = stats[collection].get('size', 0)
                    logger.info(f"📝 {collection}: {count} documents ({size} bytes)")
        
        # Insérer des données de test (optionnel)
        if '--with-test-data' in sys.argv:
            logger.info("\n=== Insertion of test data ===")
            insert_test_data(mongo_manager)
        
        logger.info("\nInitialization of MongoDB completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during MongoDB initialization: {e}")
        return False
    finally:
        if 'mongo_manager' in locals():
            mongo_manager.close()

def insert_test_data(mongo_manager: MongoManager):
    """Insert test data into the MongoDB collection"""
    from datetime import datetime
    
    # Test data for a station
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
    
    # Insert into stations_realtime
    try:
        mongo_manager.database.stations_realtime.insert_one(test_station_data)
        logger.info("Test data inserted into stations_realtime")
    except Exception as e:
        logger.error(f"Error while inserting test data: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)
