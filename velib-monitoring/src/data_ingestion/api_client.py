import requests
import json
import time
from typing import Dict, List, Optional
import logging
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VelibAPIClient:
    """Client for the Vélib' Métropole API"""
    
    def __init__(self, base_url: str = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"):
        self.base_url = base_url
        self.session = requests.Session()
        
        self.session.verify = False  # Disable strict SSL verification
        
        # Headers
        self.session.headers.update({
            'User-Agent': 'VelibMonitoring/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Configure retries for handling transient errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.alternative_urls = [
            "https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole",
            "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
        ]
    
    def get_station_information(self) -> Optional[Dict]:
        """Fetches static information about stations from the API"""
        # retrieve all data per station of status_information.json
        for base_url in [self.base_url] + self.alternative_urls:
            try:
                url = f"{base_url}/station_information.json" 
                logger.info(f"Attempting to fetch from: {base_url}")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Success: {len(data.get('data', {}).get('stations', []))} stations retrieved")
                return data
            except Exception as e:
                logger.warning(f"Failed to fetch from {base_url}: {e}")
                continue
        
        logger.error("Unable to retrieve station information from all URLs")
        return None
    
    def get_station_status(self) -> Optional[Dict]:
        """Fetches real-time status of stations"""
        for base_url in [self.base_url] + self.alternative_urls:
            try:
                url = f"{base_url}/station_status.json"
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Status retrieved: {len(data.get('data', {}).get('stations', []))} stations")
                return data
            except Exception as e:
                logger.warning(f"Failed to fetch status from {base_url}: {e}")
                continue
        
        logger.error("Unable to retrieve status from all URLs")
        return None
    
    def get_all_stations_data(self) -> Optional[Dict]:
        """"Fetches all station data (information + status)"""
        try:
            station_info = self.get_station_information()
            station_status = self.get_station_status()
            
            if not station_info or not station_status:
                logger.error("Unable to retrieve station_info or station_status data")
                return None
            
            # Verify the structure of the data
            info_data = station_info.get('data', {})
            status_data = station_status.get('data', {})
            
            if not info_data.get('stations') or not status_data.get('stations'):
                logger.error("Invalid data structure in API response")
                return None
            
            # Create a dictionary of station information by station_id
            stations_info_dict = {
                station['station_id']: station 
                for station in info_data['stations']
            }
            
            # Enrich status data with static information
            enriched_data = []
            current_timestamp = int(time.time())
            
            for status in status_data['stations']:
                station_id = status.get('station_id')
                if station_id and station_id in stations_info_dict:
                    combined_data = {
                        **stations_info_dict[station_id],
                        **status,
                        'timestamp': current_timestamp,
                        'last_updated': status.get('last_updated', current_timestamp)
                    }
                    enriched_data.append(combined_data)
            
            logger.info(f"Enriched data for {len(enriched_data)} stations")
            
            return {
                'last_updated': station_status.get('last_updated', current_timestamp),
                'ttl': station_status.get('ttl', 60),
                'data_timestamp': current_timestamp,
                'stations': enriched_data
            }
            
        except Exception as e:
            logger.error(f"Error in get_all_stations_data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def monitor_stations(self, callback, interval: int = 30):
        """Monitors stations and calls the callback with new data"""
        logger.info(f"Starting station monitoring (interval: {interval}s)")
        
        while True:
            try:
                data = self.get_all_stations_data()
                if data and 'stations' in data and len(data['stations']) > 0:
                    callback(data)
                    logger.info(f"Data sent for {len(data['stations'])} stations")
                else:
                    logger.warning("No valid data retrieved")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                # Attendre un peu avant de réessayer
                time.sleep(min(interval, 10))
