#!/bin/bash

# Script de lancement unique pour le système Vélib' Monitoring
# Démarre tous les composants nécessaires

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${GREEN}"
    echo "🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️"
    echo "    VÉLIB' PARIS MONITORING - DÉMARRAGE AUTOMATIQUE"
    echo "    Surveillance temps réel des stations Vélib'"
    echo "🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️🚴‍♂️"
    echo -e "${NC}"
}

# Fonction pour vérifier les prérequis
check_requirements() {
    print_status "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé"
        exit 1
    fi
    print_success "Docker trouvé"
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose n'est pas installé"
        exit 1
    fi
    print_success "Docker Compose trouvé"
    
    # Vérifier Python
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        print_error "Python n'est pas installé"
        exit 1
    fi
    print_success "Python trouvé"
    
    # Vérifier le fichier .env
    if [ ! -f ".env" ]; then
        print_warning "Fichier .env manquant, création..."
        cat > .env << EOF
VELIB_API_URL=https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MONGODB_URI=mongodb://admin:password123@localhost:27017/
MONGODB_DATABASE=velib_monitoring
UPDATE_INTERVAL=30
EOF
        print_success "Fichier .env créé"
    fi
}

# Fonction pour installer les dépendances Python
install_python_dependencies() {
    print_status "Installation des dépendances Python..."
    
    # Créer un environnement virtuel s'il n'existe pas
    if [ ! -d "venv" ]; then
        print_status "Création de l'environnement virtuel Python..."
        python3 -m venv venv
        print_success "Environnement virtuel créé"
    fi
    
    # Activer l'environnement virtuel et installer les dépendances
    print_status "Installation des packages dans l'environnement virtuel..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    print_success "Dépendances Python installées dans l'environnement virtuel"
}

# Fonction helper pour exécuter Python avec l'environnement virtuel
run_python() {
    if [ -d "venv" ]; then
        source venv/bin/activate
        python "$@"
    else
        python3 "$@"
    fi
}

# Fonction pour démarrer les services Docker
start_docker_services() {
    print_status "Démarrage des services Docker..."
    
    # Démarrer les services
    docker-compose up -d
    
    print_status "Attente du démarrage des services..."
    sleep 10
    
    # Vérifier que les services sont démarrés
    if docker-compose ps | grep -q "Up"; then
        print_success "Services Docker démarrés"
        docker-compose ps
    else
        print_error "Erreur lors du démarrage des services Docker"
        exit 1
    fi
}

# Fonction pour créer les topics Kafka
setup_kafka() {
    print_status "Configuration des topics Kafka..."
    
    # Attendre que Kafka soit prêt
    sleep 5
    
    run_python scripts/create_kafka_topics.py
    print_success "Topics Kafka configurés"
}

# Fonction pour configurer MongoDB
setup_mongodb() {
    print_status "Configuration de MongoDB..."
    
    run_python scripts/setup_mongodb.py
    print_success "MongoDB configuré"
}

# Fonction pour démarrer le producer
start_producer() {
    print_status "Démarrage du producer Vélib'..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/python src/data_ingestion/velib_producer.py > logs/producer.log 2>&1 &
    else
        nohup python3 src/data_ingestion/velib_producer.py > logs/producer.log 2>&1 &
    fi
    PRODUCER_PID=$!
    echo $PRODUCER_PID > logs/producer.pid
    
    print_success "Producer démarré (PID: $PRODUCER_PID)"
}

# Fonction pour démarrer le processeur
start_processor() {
    print_status "Démarrage du processeur..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/python src/processor.py > logs/processor.log 2>&1 &
    else
        nohup python3 src/processor.py > logs/processor.log 2>&1 &
    fi
    PROCESSOR_PID=$!
    echo $PROCESSOR_PID > logs/processor.pid
    
    print_success "Processeur démarré (PID: $PROCESSOR_PID)"
}

# Fonction pour démarrer Streamlit
start_dashboard() {
    print_status "Démarrage du dashboard Streamlit..."
    
    # Démarrer en arrière-plan avec l'environnement virtuel
    if [ -d "venv" ]; then
        nohup venv/bin/streamlit run streamlit.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
    else
        nohup streamlit run streamlit.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
    fi
    STREAMLIT_PID=$!
    echo $STREAMLIT_PID > logs/streamlit.pid
    
    print_success "Dashboard Streamlit démarré (PID: $STREAMLIT_PID)"
}

# Fonction pour attendre que les données arrivent
wait_for_data() {
    print_status "Attente des premières données..."
    
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
            print_success "Données détectées ($DATA_COUNT stations)"
            break
        fi
        
        echo -n "."
        sleep 2
    done
    
    if [ "$DATA_COUNT" -eq 0 ]; then
        print_warning "Aucune donnée détectée, mais le système continue"
    fi
}

# Fonction pour afficher le statut final
show_status() {
    echo ""
    print_success "🎉 SYSTÈME VÉLIB' DÉMARRÉ AVEC SUCCÈS !"
    echo ""
    echo -e "${BLUE}📊 Interfaces disponibles :${NC}"
    echo "   🌐 Dashboard Streamlit : http://localhost:8501"
    echo "   🗄️  MongoDB           : mongodb://localhost:27017"
    echo "   📡 Kafka             : localhost:9092"
    echo ""
    echo -e "${BLUE}📝 Fichiers de logs :${NC}"
    echo "   🔍 Producer  : logs/producer.log"
    echo "   ⚙️  Processeur: logs/processor.log"
    echo "   📊 Streamlit : logs/streamlit.log"
    echo ""
    echo -e "${BLUE}🛠️  Commandes utiles :${NC}"
    echo "   📊 Voir logs producer  : tail -f logs/producer.log"
    echo "   ⚙️  Voir logs processeur: tail -f logs/processor.log"
    echo "   🛑 Arrêter le système  : ./stop_system.sh"
    echo ""
    echo -e "${GREEN}✨ Ouvrez http://localhost:8501 dans votre navigateur !${NC}"
}

# Fonction pour créer le répertoire logs
create_logs_dir() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
        print_success "Répertoire logs créé"
    fi
}

# Fonction de nettoyage en cas d'erreur
cleanup() {
    print_error "Erreur détectée, nettoyage..."
    
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
    print_header
    
    # Créer le répertoire logs
    create_logs_dir
    
    # Vérifications
    check_requirements
    
    # Installation des dépendances
    install_python_dependencies
    
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
