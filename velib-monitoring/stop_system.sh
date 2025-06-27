#!/bin/bash

# Script pour arrêter proprement le système Vélib' Monitoring

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${RED}"
    echo "🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑"
    echo "    ARRÊT DU SYSTÈME VÉLIB' MONITORING"
    echo "🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑"
    echo -e "${NC}"
}

# Fonction pour arrêter un processus
stop_process() {
    local process_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            print_status "Arrêt de $process_name (PID: $pid)..."
            kill $pid
            sleep 2
            
            # Vérifier si le processus est vraiment arrêté
            if ps -p $pid > /dev/null 2>&1; then
                print_warning "Forçage de l'arrêt de $process_name..."
                kill -9 $pid
            fi
            
            print_success "$process_name arrêté"
        else
            print_warning "$process_name n'était pas en cours d'exécution"
        fi
        
        rm "$pid_file"
    else
        print_warning "Fichier PID de $process_name non trouvé"
    fi
}

# Fonction pour arrêter les processus par nom
stop_by_name() {
    local process_name=$1
    local pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        print_status "Arrêt des processus $process_name..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 2
        
        # Vérifier et forcer si nécessaire
        local remaining_pids=$(pgrep -f "$process_name" 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            print_warning "Forçage de l'arrêt de $process_name..."
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
        fi
        
        print_success "Processus $process_name arrêtés"
    fi
}

main() {
    print_header
    
    # Arrêter les processus Python
    print_status "Arrêt des composants Python..."
    
    # Arrêter par fichiers PID
    stop_process "Producer" "logs/producer.pid"
    stop_process "Processeur" "logs/processor.pid" 
    stop_process "Streamlit" "logs/streamlit.pid"
    
    # Arrêter par nom de processus (au cas où)
    stop_by_name "velib_producer.py"
    stop_by_name "processor.py"
    stop_by_name "streamlit.*streamlit_simple.py"
    
    # Arrêter les services Docker
    print_status "Arrêt des services Docker..."
    docker-compose down
    print_success "Services Docker arrêtés"
    
    # Nettoyage
    print_status "Nettoyage des fichiers temporaires..."
    rm -f logs/*.pid 2>/dev/null || true
    print_success "Nettoyage terminé"
    
    echo ""
    print_success "🎉 SYSTÈME VÉLIB' ARRÊTÉ AVEC SUCCÈS !"
    echo ""
    echo -e "${BLUE}Pour redémarrer le système :${NC}"
    echo "   ./start_system.sh"
    echo ""
}

main
