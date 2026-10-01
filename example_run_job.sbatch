#!/bin/bash
#SBATCH --job-name=pddl_domain_generator      # Nome del job visualizzato nella coda
#SBATCH --output=logs/job_%j.out       # File dove verranno salvati gli og di output (%j = Job ID)
#SBATCH --error=logs/job_%j.err        # File dove verranno salvati gli errori
#SBATCH --partition=debug              # partizione utilizzata, di default "debug". Scegliere una partizione invece che un altra comporta cambiare il tempo massimo che puoi assegnare al task (es: per debug 30 minuti, per batch fino a 2 ore)
#SBATCH --nodes=1                      # Numero di nodi richiesti
#SBATCH --ntasks=1                     # Numero di processi totali
#SBATCH --cpus-per-task=4              # Numero di core CPU richiesti
#SBATCH --mem=16G                      # Memoria RAM richiesta
#SBATCH --gres=gpu:1                   # Richiesta di 1 GPU per caricare il modello Hugging Face
#SBATCH --time=00:25:00                # Tempo massimo di esecuzione (HH:MM:SS)


# 1. Crea la cartella dei log se non esiste
mkdir -p logs

# 2. Attiva l'ambiente virtuale
source .venv/bin/activate

# 3. Esegue lo script Python
srun python main_server.py --model qwen