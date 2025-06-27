#!/usr/bin/env python3

"""
Script pour créer les topics Kafka nécessaires au projet Vélib'
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Ajouter le chemin src au Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.kafka_utils import KafkaManager, get_velib_topics_config

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
    
    # Configuration Kafka
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    logger.info("=== Création des Topics Kafka pour Vélib' Monitoring ===")
    logger.info(f"Serveurs Kafka: {bootstrap_servers}")
    
    # Initialiser le gestionnaire Kafka
    kafka_manager = KafkaManager(bootstrap_servers)
    
    try:
        # Vérifier la connexion
        if not kafka_manager.check_connection():
            logger.error("❌ Impossible de se connecter à Kafka")
            logger.error("Assurez-vous que Kafka est démarré: docker-compose up -d")
            return False
        
        logger.info("✅ Connexion à Kafka établie")
        
        # Lister les topics existants
        existing_topics = kafka_manager.list_topics()
        logger.info(f"Topics existants: {existing_topics}")
        
        # Récupérer la configuration des topics Vélib'
        topics_config = get_velib_topics_config()
        
        # Créer les topics
        logger.info(f"Création de {len(topics_config)} topics...")
        
        # Vérifier d'abord quels topics existent déjà
        topics_to_create = []
        topics_existing = []
        
        for topic_config in topics_config:
            topic_name = topic_config['name']
            if topic_name in existing_topics:
                topics_existing.append(topic_name)
            else:
                topics_to_create.append(topic_config)
        
        # Rapport sur les topics existants
        if topics_existing:
            logger.info(f"ℹ️  Topics déjà existants: {topics_existing}")
        
        # Créer uniquement les nouveaux topics
        success = True
        if topics_to_create:
            logger.info(f"🔧 Création de {len(topics_to_create)} nouveaux topics...")
            success = kafka_manager.create_topics(topics_to_create)
        else:
            logger.info("✅ Tous les topics existent déjà")
        
        if success or len(topics_existing) == len(topics_config):
            logger.info("✅ Configuration des topics terminée avec succès")
            
            # Lister les topics après création
            final_topics = kafka_manager.list_topics()
            velib_topics = [t for t in final_topics if 'velib' in t.lower() or any(keyword in t for keyword in ['station', 'bikes', 'docks'])]
            logger.info(f"📋 Topics Vélib' disponibles: {velib_topics}")
            
            # Afficher les détails des topics configurés
            logger.info("\n=== Détails des Topics ===")
            for topic_config in topics_config:
                topic_name = topic_config['name']
                status = "✅ Existant" if topic_name in existing_topics else "🆕 Créé"
                logger.info(f"📝 {topic_name} ({status})")
                logger.info(f"   - Partitions: {topic_config.get('partitions', 1)}")
                logger.info(f"   - Réplication: {topic_config.get('replication_factor', 1)}")
            
            return True
        else:
            logger.error("❌ Erreur lors de la configuration des topics")
            return False
            
    except KeyboardInterrupt:
        logger.info("❌ Interruption par l'utilisateur")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        return False
    finally:
        kafka_manager.close()

def show_usage():
    """Affiche l'aide d'utilisation"""
    print("""
Usage: python create_kafka_topics.py

Ce script crée les topics Kafka nécessaires pour le monitoring Vélib':
- station_status_topic: Données complètes des stations
- available_bikes_topic: Données de vélos disponibles
- available_docks_topic: Données de docks disponibles  
- station_info_topic: Informations statiques des stations

Prérequis:
1. Kafka doit être démarré: docker-compose up -d
2. Les variables d'environnement doivent être configurées dans .env

Variables d'environnement:
- KAFKA_BOOTSTRAP_SERVERS (défaut: localhost:9092)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        show_usage()
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)
