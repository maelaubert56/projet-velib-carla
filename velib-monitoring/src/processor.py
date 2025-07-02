#!/usr/bin/env python3

"""
Python processor to read from Kafka and write to MongoDB
A simple and efficient processor to avoid compatibility issues
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any
from datetime import datetime

# Add the src path to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from kafka import KafkaConsumer
from utils.mongo_utils import MongoManager
from dotenv import load_dotenv

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VelibKafkaToMongoProcessor:
    """Processor Kafka to MongoDB"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration Kafka
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        
        # Configuration MongoDB
        self.mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password123@localhost:27017/?authSource=admin')
        self.mongo_db_name = os.getenv('MONGODB_DATABASE', 'velib_monitoring')
        
        # Topics to process
        self.topics = [
            'station_status_topic',
            'available_bikes_topic',
            'available_docks_topic',
            'station_info_topic'
        ]
        
        # Initialize MongoDB
        self.mongo_manager = MongoManager(self.mongo_uri, self.mongo_db_name)
        
        logger.info(f"Processor initialized - Kafka: {self.kafka_servers}")
        logger.info(f"Monitored topics: {self.topics}")
    
    def create_consumer(self, topics: List[str]) -> KafkaConsumer:
        """Creates a Kafka consumer"""
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
        """Processes and enriches station data"""
        processed = data.copy()
        
        # Add processing timestamp
        processed['processed_timestamp'] = datetime.utcnow().isoformat()
        
        # Calculate metrics
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
        """Data saving in MongoDB depending on topic"""
        try:
            processed_data = self.process_station_data(data)
            
            if topic == 'station_status_topic':
                # Real-time station data
                collection = self.mongo_manager.get_collection('stations_realtime')
                
                # Upsert based on station_id
                filter_query = {'station_id': processed_data.get('station_id')}
                
                collection.replace_one(
                    filter_query,
                    processed_data,
                    upsert=True
                )
                
            elif topic in ['available_bikes_topic', 'available_docks_topic']:
                # Availability data - keep historical records
                collection = self.mongo_manager.get_collection('availability_history')
                
                processed_data['topic_source'] = topic
                collection.insert_one(processed_data)
                
            elif topic == 'station_info_topic':
                # Static station information
                collection = self.mongo_manager.get_collection('stations_info')
                
                filter_query = {'station_id': processed_data.get('station_id')}
                collection.replace_one(
                    filter_query,
                    processed_data,
                    upsert=True
                )
            
            logger.debug(f"Data saved: {topic} - Station {processed_data.get('station_id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error saving to MongoDB for topic {topic}: {e}")
    
    def process_messages(self):
        """Processes Kafka messages continuously"""
        logger.info("Starting Kafka to MongoDB processor")
        
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
                        
                        # Periodic log
                        current_time = time.time()
                        if current_time - last_log_time > 30:  # Each 30 seconds
                            logger.info(f"Processed messages: {message_count}")
                            last_log_time = current_time
                            
                            # Stats MongoDB
                            stats = self.get_mongo_stats()
                            logger.info(f"📄 Documents MongoDB: {stats}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from topic: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Stop requested by the user")
        except Exception as e:
            logger.error(f"Error in the processor: {e}")
        finally:
            logger.info("Closing Kafka consumer")
            consumer.close()
            self.mongo_manager.close()
    
    def get_mongo_stats(self) -> Dict[str, int]:
        """Fetches MongoDB statistics"""
        try:
            stats = {}
            collections = ['stations_realtime', 'availability_history', 'stations_info']
            
            for coll_name in collections:
                collection = self.mongo_manager.get_collection(coll_name)
                count = collection.count_documents({})
                stats[coll_name] = count
                
            return stats
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            return {}

def main():
    """Main function"""
    processor = VelibKafkaToMongoProcessor()
    processor.process_messages()

if __name__ == "__main__":
    main()
