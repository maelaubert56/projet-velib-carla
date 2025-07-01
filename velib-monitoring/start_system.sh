#!/bin/bash

# Fonction pour démarrer les services Docker
start_docker_services() {
    echo "Démarrage des services Docker..."
    
    # Démarrer les services
    docker-compose up -d
    
    echo "Attente du démarrage des services..."
    sleep 10
    
    # Vérifier que les services sont démarrés
    if docker-compose ps | grep -q "Up"; then
        echo "Services Docker démarrés"
        docker-compose ps
    else
        echo "Erreur lors du démarrage des services Docker"
        exit 1
    fi
}

# Fonction pour créer les topics Kafka
setup_kafka() {
    echo "Configuration des topics Kafka..."
    
    # Attendre que Kafka soit prêt
    sleep 5
    
    run_python scripts/create_kafka_topics.py
    echo "Topics Kafka configurés"
}

# Fonction pour configurer MongoDB
setup_mongodb() {
    echo "Configuration de MongoDB..."
    
    run_python scripts/setup_mongodb.py
    echo "MongoDB configuré"
}

# Fonction pour démarrer le producer
start_producer() {
    echo "Démarrage du producer Vélib'..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/python src/data_ingestion/velib_producer.py > logs/producer.log 2>&1 &
    else
        nohup python3 src/data_ingestion/velib_producer.py > logs/producer.log 2>&1 &
    fi
    PRODUCER_PID=$!
    echo $PRODUCER_PID > logs/producer.pid
    
    echo "Producer démarré (PID: $PRODUCER_PID)"
}

# Fonction pour démarrer le processeur
start_processor() {
    echo "Démarrage du processeur..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/python src/processor.py > logs/processor.log 2>&1 &
    else
        nohup python3 src/processor.py > logs/processor.log 2>&1 &
    fi
    PROCESSOR_PID=$!
    echo $PROCESSOR_PID > logs/processor.pid
    
    echo "Processeur démarré (PID: $PROCESSOR_PID)"
}

# Fonction pour démarrer Streamlit
start_dashboard() {
    echo "Démarrage du dashboard Streamlit..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/streamlit run streamlit.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
    else
        nohup streamlit run streamlit.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
    fi
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > logs/streamlit.pid
    
    echo "Dashboard Streamlit démarré (PID: $STREAMLIT_PID)"
}

# Fonction pour attendre que les données arrivent
wait_for_data() {
    echo "Attente des premières données..."
    
    for i in {1..30}; do
        if [ -d "venv" ]; then
            DATA_COUNT=$(venv/bin/python -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://admin:password123@localhost:27017/')
    db = client['velib_monitoring']
    count = db.stations_realtime.count_documents({})
    print(count)
except:
    print(0)
" 2>/dev/null)
        else
            DATA_COUNT=$(python3 -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://admin:password123@localhost:27017/')
    db = client['velib_monitoring']
    count = db.stations_realtime.count_documents({})
    print(count)
except:
    print(0)
" 2>/dev/null)
        fi
        
        if [ "$DATA_COUNT" -gt 0 ]; then
            echo "Données détectées ($DATA_COUNT stations)"
            break
        fi
        
        echo -n "."
        sleep 2
    done
    
    if [ "$DATA_COUNT" -eq 0 ]; then
        echo "Aucune donnée détectée, mais le système continue"
    fi
}

# Fonction pour afficher le statut final
show_status() {
    echo "Applicationn lancée !"
    echo "Streamlit : http://localhost:8501"
    echo "MongoDB : mongodb://localhost:27017"
    echo "Kafka : localhost:9092"
}

# Fonction pour créer le répertoire logs
create_logs_dir() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
        echo "Répertoire logs créé"
    fi
}

# Fonction de nettoyage en cas d'erreur
cleanup() {
    echo "Erreur détectée, nettoyage..."
    
    # Arrêter les processus si ils existent
    if [ -f "logs/producer.pid" ]; then
        kill $(cat logs/producer.pid) 2>/dev/null || true
        rm logs/producer.pid
    fi
    
    if [ -f "logs/processor.pid" ]; then
        kill $(cat logs/processor.pid) 2>/dev/null || true
        rm logs/processor.pid
    fi
    
    if [ -f "logs/streamlit.pid" ]; then
        kill $(cat logs/streamlit.pid) 2>/dev/null || true
        rm logs/streamlit.pid
    fi
    
    exit 1
}

# Piège pour gérer les erreurs
trap cleanup ERR

# SCRIPT PRINCIPAL
main() {
    
    # Créer le répertoire logs
    create_logs_dir

    # Démarrage des services
    start_docker_services
    
    # Configuration
    setup_kafka
    setup_mongodb
    
    # Démarrage des composants
    start_producer
    sleep 5
    start_processor
    sleep 5
    start_dashboard
    
    # Attendre les données
    wait_for_data
    
    # Afficher le statut final
    show_status
}

# Exécuter le script principal
main
