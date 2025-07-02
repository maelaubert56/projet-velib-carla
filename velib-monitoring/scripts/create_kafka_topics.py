#!/usr/bin/env python3

"""
Script to create the Kafka topics required
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the path src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.kafka_utils import KafkaManager, get_velib_topics_config

# Logging configuration
logging.basicConfig(
    filename='../logs/app.log',  # Nom du fichier de log
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to create Kafka topics for Vélib' monitoring."""
    # Load environment variables
    load_dotenv()
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    logger.info("=== Creating Kafka Topics for Vélib' Monitoring ===")
    logger.info(f"Kafka servers: {bootstrap_servers}")
    
    # Initialize the Kafka manager
    kafka_manager = KafkaManager(bootstrap_servers)
    
    try:
        # try the connexion to Kafka
        if not kafka_manager.check_connection():
            logger.error("Unable to connect to Kafka")
            return False
        logger.info("Connected to Kafka successfully")
        
        # List existing topics
        existing_topics = kafka_manager.list_topics() 
        logger.info(f"Existing topics: {existing_topics}") # passer en echo
        
        # Retrieve the configuration of Vélib' topics
        topics_config = get_velib_topics_config()
        
        # Create the topics
        logger.info(f"Creating {len(topics_config)} topics...")
        
        # First check which topics already exist
        topics_to_create = []
        topics_existing = []
        
        for topic_config in topics_config:
            topic_name = topic_config['name']
            if topic_name in existing_topics:
                topics_existing.append(topic_name)
            else:
                topics_to_create.append(topic_config)
        
        # Report on existing topics
        if topics_existing:
            logger.info(f"Already existing topics: {topics_existing}")
        
        # Create only new topics
        success = True
        if topics_to_create:
            logger.info(f"Creation of {len(topics_to_create)} new topics...")
            success = kafka_manager.create_topics(topics_to_create)
        else:
            logger.info("All the topics are already configured, no creation needed.")
        
        if success or len(topics_existing) == len(topics_config):
            logger.info("All the topics are already configured, no creation needed.")
            
            # List all topics after creation
            final_topics = kafka_manager.list_topics()
            velib_topics = [t for t in final_topics if 'velib' in t.lower() or any(keyword in t for keyword in ['station', 'bikes', 'docks'])]
            logger.info(f"Available Vélib' topics: {velib_topics}")
            
            # Display details of configured topics
            logger.info("\n=== Topics Details ===")
            for topic_config in topics_config:
                topic_name = topic_config['name']
                status = "Existing" if topic_name in existing_topics else "Created"
                logger.info(f"📝 {topic_name} ({status})")
                logger.info(f"   - Partitions: {topic_config.get('partitions', 1)}")
                logger.info(f"   - Replication factor: {topic_config.get('replication_factor', 1)}")
            
            return True
        else:
            logger.error("Error during the topics configuration.")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        kafka_manager.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)
