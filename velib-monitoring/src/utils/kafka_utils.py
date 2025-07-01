from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import TopicAlreadyExistsError
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KafkaManager:
    """Gestionnaire pour les opérations Kafka"""
    # Initialisation du gestionnaire Kafka -> client KafkaAdmin
    def __init__(self, bootstrap_servers: str = 'localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='velib_admin'
        )
    # Création des topics Kafka -> Q1
    def create_topics(self, topics: List[Dict[str, Any]]) -> bool:
        #Crée les topics Kafka via une liste
        topic_list = []
        # config des topics -> def
        for topic in topics:
            topic = NewTopic(
                name=topic['name'],
                num_partitions=topic.get('partitions', 3),
                replication_factor=topic.get('replication_factor', 1)
            )
            topic_list.append(topic)

        try:
            fs = self.admin_client.create_topics(new_topics=topic_list, validate_only=False)
            print(f"Topics créés : {[topic.name for topic in topic_list]}")
            return True
        except Exception as e:
            print(f"Erreur lors de la création des topics: {e}")
            return False
    
    # sert à checker si les topics existent déjà -> intéressant pour print
    def list_topics(self) -> List[str]:
        """Liste tous les topics disponibles"""
        try:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(bootstrap_servers=self.bootstrap_servers)
            topics = consumer.topics()
            consumer.close()
            return list(topics)
        except Exception as e:
            print(f"Erreur lors de la récupération des topics: {e}")
            return []
    
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
            print(f"Connexion Kafka OK. Topics disponibles: {len(topics)}")
            return True
        except Exception as e:
            print(f"Erreur de connexion Kafka: {e}")
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
