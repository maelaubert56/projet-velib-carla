'''
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import TopicAlreadyExistsError
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# je pense fonction inutile à checker si possible
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

# manipuler configs des topics Kafka -> maybe  inutile
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
'''