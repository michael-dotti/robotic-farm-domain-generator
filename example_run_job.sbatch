#!/bin/bash
#SBATCH --job-name=pddl_domain_generator      # Nome del job visualizzato nella coda
#SBATCH --output=server_logs/job_%j.out       # File dove verranno salvati gli og di output (%j = Job ID)
#SBATCH --error=server_logs/job_%j.err        # File dove verranno salvati gli errori
#SBATCH --partition=batch              # partizione utilizzata, di default "batch". Scegliere una partizione invece che un altra comporta cambiare il tempo massimo che puoi assegnare al task (es: per debug 30 minuti, per batch fino a 2 ore)
#SBATCH --nodes=1                      # Numero di nodi richiesti
#SBATCH --ntasks=1                     # Numero di processi totali
#SBATCH --cpus-per-task=16              # Numero di core CPU richiesti
#SBATCH --mem=120G                      # Memoria RAM richiesta
#SBATCH --gres=gpu:1                   # Richiesta di 1 GPU per caricare il modello Hugging Face
#SBATCH --time=02:00:00                # Tempo massimo di esecuzione (HH:MM:SS)


mkdir -p server_logs

# --- 1. INSTALLAZIONE E SETUP DI OLLAMA (User-space) ---
# Scarica l'eseguibile di Ollama nella tua cartella home se non esiste
if [ ! -f "$HOME/bin/ollama" ]; then
    echo "Scaricamento di Ollama in corso..."
    mkdir -p $HOME/bin
    curl -L https://ollama.com/download/ollama-linux-amd64 -o $HOME/bin/ollama
    chmod +x $HOME/bin/ollama
fi
# Aggiunge la cartella bin al PATH
export PATH=$HOME/bin:$PATH

# Imposta dove Ollama salverà i modelli pesanti (GGUF)
# Puoi cambiare questo percorso se hai una cartella "scratch" nel cluster più capiente
export OLLAMA_MODELS=$HOME/ollama_models
mkdir -p $OLLAMA_MODELS

# --- 2. AVVIO DI OLLAMA IN BACKGROUND ---
echo "Avvio del server Ollama..."
ollama serve &
OLLAMA_PID=$!

# Attendi 10 secondi per assicurarti che il server sia pronto a ricevere richieste
sleep 10 

# Scarica preventivamente il modello (cambia il nome in base a quello che vuoi usare)
echo "Download del modello in corso (potrebbe richiedere tempo)..."
ollama pull llama3.3:70b

# --- 3. ESECUZIONE DEL CODICE PYTHON ---
source .venv/bin/activate
# Passa il nome dell'alias che configureremo in main_server.py
srun python main_server.py --model llama-70b

# --- 4. SPEGNIMENTO ---
echo "Spegnimento di Ollama..."
kill $OLLAMA_PID