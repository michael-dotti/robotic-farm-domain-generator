# Robotic Farm Domain Generator

Questo progetto è una pipeline automatizzata sviluppata con la libreria **`l2p`** per generare il file `domain.pddl` relativo allo scenario **Robotic Farm**, partendo da una descrizione del problema espressa in linguaggio naturale.

> ⚠️ **Status del Progetto: Work in Progress (WIP)**  
> La pipeline (estrazione Tipi, Predicati, Azioni e ciclo di Self-Correction) è completamente implementata, ma la calibrazione dei prompt e la generazione di un `domain.pddl` sintatticamente e semanticamente valido al 100% sono ancora in fase di perfezionamento.

---

## 🚀 Modalità di Esecuzione e Modelli LLM

Il progetto offre due script di avvio distinti, pensati per ambienti di esecuzione differenti.

### 1. Esecuzione Locale (`main.py`)
Script pensato per l'uso su PC. Presenta un menu interattivo nel terminale per la scelta del modello.
* **`qwen2.5-coder:7b`** (Provider: Ollama locale) - Modello open source ottimizzato per il codice.
* **`gemini-3.1-pro-preview`** (Provider: Google Gemini API) - Modello cloud ad alte prestazioni.

### 2. Esecuzione Batch per Server/Cluster (`main_server.py`)
Script  progettato specificamente per l'esecuzione su cluster HPC. Non richiede Ollama: scarica e avvia i modelli direttamente in VRAM tramite l'integrazione nativa Hugging Face.
* **`Qwen/Qwen2.5-Coder-3B-Instruct`** (Provider: Hugging Face) - Versione leggera da 3 miliardi di parametri, ideale per VRAM limitate.
* **`google/gemma-2-2b-it`** (Provider: Hugging Face) - Modello Google ultra-leggero da 2 miliardi di parametri.

## 🛠️ Requisiti e Configurazione

### 1. Prerequisiti
* **Python 3.12+**
* **Ollama** installato e attivo (necessario solo se desideri usare Qwen)
* **API Key di Google AI Studio** (necessario solo se desideri usare Gemini)
* * **Access Token di Hugging Face** (necessario **solo** se usi `main_server.py` con modelli "gated" come Gemma)

Se intendi usare Qwen2.5 Coder, scarica prima il modello locale con:
```bash
ollama run qwen2.5-coder:7b
```

### 2. Installazione delle Dipendenze
Clona la repository e installa i pacchetti necessari tramite il file requirements.txt:
```bash
git clone https://github.com/tuo-utente/robotic-farm-domain-generator.git
cd robotic-farm-domain-generator
pip install -r requirements.txt
```

### 3. Configurazione del File .env
Copia il file di esempio .env.example per creare il tuo file di configurazione d'ambiente .env:
```bash
cp .env.example .env
```

Apri il file .env e inserisci la tua chiave API se usi Gemini:
```env
LLM_GEMINI_KEY="la_tua_chiave_api_qui"
```
