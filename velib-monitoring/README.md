# 🚴‍♂️ Vélib' Paris Real-Time Monitoring

Système de monitoring temps réel des stations Vélib' à Paris avec ingestion de données, traitement en streaming, et visualisation interactive.

## 🚀 Démarrage Rapide

### Option 1: Démarrage Automatique (Recommandé)

```bash
# Démarrage intelligent avec résolution automatique des problèmes
python3 simple_start.py
```

### Option 2: Démarrage Manuel

```bash
# 1. Corriger l'environnement (résout PEP 668 + Docker)
python3 fix_environment.py

# 2. Activer l'environnement virtuel
source venv/bin/activate

# 3. Démarrer les services
make start

# 4. Configurer Kafka et MongoDB
make setup

# 5. Lancer le monitoring
make run-producer    # Terminal 1
make run-dashboard   # Terminal 2
```

### Option 3: Installation Complète

```bash
make full-install
```

## 🔧 Diagnostic

En cas de problème, utilisez le diagnostic :

```bash
python3 diagnostic.py
```

## 📊 Interfaces Disponibles

Une fois le système démarré :

- **📈 Dashboard Streamlit**: http://localhost:8501
- **📊 Grafana**: http://localhost:3000 (admin/admin123)
- **🗄️ MongoDB**: mongodb://admin:password123@localhost:27017

## 🛠️ Commandes Utiles

```bash
# Gestion des services
make start           # Démarrer Docker
make stop            # Arrêter Docker
make status          # État des services
make logs            # Logs en temps réel

# Monitoring
make run-producer    # Producteur de données
make run-dashboard   # Dashboard Streamlit

# Maintenance
make clean          # Nettoyer les fichiers temporaires
make clean-docker   # Nettoyer Docker
make test          # Lancer les tests
```

## 🐍 Problèmes Python (PEP 668)

Sur macOS avec Homebrew Python, vous pourriez avoir des erreurs "externally-managed-environment".

**Solution automatique :**

```bash
python3 fix_environment.py
```

**Solution manuelle :**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🐳 Problèmes Docker

Si vous avez des erreurs d'authentification Docker Hub :

1. **Solution automatique :** `make fix-env`
2. **Solution manuelle :** Utiliser `docker-compose-local.yml`

```bash
docker-compose -f docker-compose-local.yml up -d
```

```
VELIB_API_URL=https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MONGODB_URI=mongodb://admin:password123@localhost:27017/
MONGODB_DATABASE=velib_monitoring
```

### Initialisation des topics Kafka

```bash
python scripts/create_kafka_topics.py
```

## Utilisation

### 1. Démarrer l'ingestion de données

```bash
python src/data_ingestion/velib_producer.py
```

### 2. Démarrer le processeur

```bash
python src/processor.py
```

### 3. Démarrer le dashboard

```bash
streamlit run streamlit.py
```

## Accès aux services

- **Kafka UI**: http://localhost:9092
- **MongoDB**: localhost:27017
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Streamlit Dashboard**: http://localhost:8501

## Structure du projet

```
velib-monitoring/
├── docker-compose.yml
├── requirements.txt
├── README.md
├── .env
├── src/
│   ├── data_ingestion/
│   │   ├── velib_producer.py
│   │   └── api_client.py
│   ├── processor.py
│   └── utils/
│       ├── kafka_utils.py
│       └── mongo_utils.py
├── streamlit.py
├── scripts/
│   ├── create_kafka_topics.py
│   └── setup_mongodb.py
├── config/
└── tests/
    ├── test_producer.py
    └── test_processor.py
```

## Monitoring

### Métriques disponibles

- Nombre de vélos disponibles par station
- Taux d'occupation des stations
- Anomalies détectées
- Patterns d'usage par heure/jour

### Alertes

- Stations toujours vides (< 5% vélos)
- Stations toujours pleines (< 5% docks)
- Pannes de stations

## Développement

### Tests

```bash
pytest tests/
```

### Logs

```bash
docker-compose logs -f kafka
```

## Troubleshooting

### Problèmes courants

1. **Kafka ne démarre pas**

   - Vérifier que le port 9092 n'est pas utilisé
   - Augmenter la mémoire Docker si nécessaire

2. **Processeur Python échoue**

   - Vérifier la connectivité Kafka
   - Contrôler les logs: `tail -f logs/processor.log`

3. **MongoDB connexion error**
   - Vérifier les credentials dans `.env`
   - S'assurer que MongoDB est démarré

## Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit les changements
4. Push vers la branche
5. Créer une Pull Request

## License

MIT License
