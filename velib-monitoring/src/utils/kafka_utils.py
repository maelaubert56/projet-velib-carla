from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import TopicAlreadyExistsError
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KafkaManager:
    """Gestionnaire pour les opérations Kafka"""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='velib_admin'
        )
    
    def create_topics(self, topics: List[Dict[str, Any]]) -> bool:
        """Crée les topics Kafka"""
        topic_list = []
        
        for topic_config in topics:
            topic = NewTopic(
                name=topic_config['name'],
                num_partitions=topic_config.get('partitions', 3),
                replication_factor=topic_config.get('replication_factor', 1)
            )
            topic_list.append(topic)
        
        try:
            fs = self.admin_client.create_topics(new_topics=topic_list, validate_only=False)
            
            # Compteurs pour le reporting
            created_count = 0
            existing_count = 0
            error_count = 0
            
            # Attendre la création de tous les topics
            for topic, f in fs.items():
                try:
                    f.result()  # The result itself is None
                    logger.info(f"✅ Topic {topic} créé avec succès")
                    created_count += 1
                except TopicAlreadyExistsError:
                    logger.info(f"ℹ️  Topic {topic} existe déjà")
                    existing_count += 1
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la création du topic {topic}: {e}")
                    error_count += 1
            
            # Summary
            total_topics = len(topic_list)
            logger.info(f"📊 Résumé: {total_topics} topics traités")
            if created_count > 0:
                logger.info(f"   ✅ {created_count} créés")
            if existing_count > 0:
                logger.info(f"   ℹ️  {existing_count} existaient déjà")
            if error_count > 0:
                logger.error(f"   ❌ {error_count} erreurs")
            
            # Considérer comme succès si au moins aucune erreur grave
            return error_count == 0
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création des topics: {e}")
            return False
    
    def list_topics(self) -> List[str]:
        """Liste tous les topics disponibles"""
        try:
            # Utiliser la méthode correcte sans timeout parameter
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(bootstrap_servers=self.bootstrap_servers)
            topics = consumer.topics()
            consumer.close()
            return list(topics)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des topics: {e}")
            return []
    
    def delete_topics(self, topics: List[str]) -> bool:
        """Supprime les topics spécifiés"""
        try:
            fs = self.admin_client.delete_topics(topics, timeout=30)
            
            for topic, f in fs.items():
                try:
                    f.result()
                    logger.info(f"Topic {topic} supprimé avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression du topic {topic}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des topics: {e}")
            return False
    
    def get_topic_config(self, topics: List[str]) -> Dict[str, Dict]:
        """Récupère la configuration des topics"""
        try:
            resources = [ConfigResource(ConfigResourceType.TOPIC, topic) for topic in topics]
            configs = self.admin_client.describe_configs(config_resources=resources)
            
            result = {}
            for resource, config_response in configs.items():
                if resource.resource_type == ConfigResourceType.TOPIC:
                    result[resource.name] = {
                        config.name: config.value 
                        for config in config_response.configs.values()
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la configuration: {e}")
            return {}
    
    def create_producer(self, **kwargs) -> KafkaProducer:
        """Crée un producer Kafka avec la configuration par défaut"""
        default_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
            'retry_backoff_ms': 100,
            'request_timeout_ms': 20000,
            'max_in_flight_requests_per_connection': 1
        }
        
        # Fusionner avec la configuration personnalisée
        default_config.update(kwargs)
        
        return KafkaProducer(**default_config)
    
    def create_consumer(self, topics: List[str], group_id: str, **kwargs) -> KafkaConsumer:
        """Crée un consumer Kafka avec la configuration par défaut"""
        default_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': group_id,
            'value_deserializer': lambda v: json.loads(v.decode('utf-8')),
            'key_deserializer': lambda k: k.decode('utf-8') if k else None,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000
        }
        
        # Fusionner avec la configuration personnalisée
        default_config.update(kwargs)
        
        return KafkaConsumer(*topics, **default_config)
    
    def check_connection(self) -> bool:
        """Vérifie la connexion au cluster Kafka"""
        try:
            topics = self.list_topics()
            logger.info(f"Connexion Kafka OK. Topics disponibles: {len(topics)}")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion Kafka: {e}")
            return False
    
    def close(self):
        """Ferme les connexions"""
        try:
            self.admin_client.close()
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")

def get_velib_topics_config() -> List[Dict[str, Any]]:
    """Retourne la configuration des topics Vélib'"""
    return [
        {
            'name': 'station_status_topic',
            'partitions': 6,
            'replication_factor': 1,
            'configs': {
                'retention.ms': '604800000',  # 7 jours
                'compression.type': 'snappy'
            }
        },
        {
            'name': 'available_bikes_topic',
            'partitions': 3,
            'replication_factor': 1,
            'configs': {
                'retention.ms': '259200000',  # 3 jours
                'compression.type': 'snappy'
            }
        },
        {
            'name': 'available_docks_topic',
            'partitions': 3,
            'replication_factor': 1,
            'configs': {
                'retention.ms': '259200000',  # 3 jours
                'compression.type': 'snappy'
            }
        },
        {
            'name': 'station_info_topic',
            'partitions': 1,
            'replication_factor': 1,
            'configs': {
                'retention.ms': '2592000000',  # 30 jours
                'compression.type': 'snappy'
            }
        }
    ]
