# Robotic Farm Domain Generator

Questo progetto è una pipeline automatizzata sviluppata con la libreria **`l2p`** per generare il file `domain.pddl` relativo allo scenario **Robotic Farm**, partendo da una descrizione del problema espressa in linguaggio naturale.

> ⚠️ **Status del Progetto: Work in Progress (WIP)**  
> La pipeline (estrazione Tipi, Predicati, Azioni e ciclo di Self-Correction) è completamente implementata, ma la calibrazione dei prompt e la generazione di un `domain.pddl` sintatticamente e semanticamente valido al 100% sono ancora in fase di perfezionamento.

---

## 🚀 Modalità di Esecuzione e Modelli LLM

Il progetto offre due script di avvio distinti, pensati per ambienti di esecuzione differenti. L'elenco esatto dei modelli supportati è in continua evoluzione.

### 1. Esecuzione Locale (`main.py`)
Script pensato per l'uso su PC. Presenta un menu interattivo nel terminale per la scelta del modello. Possiamo suddividere i modelli a disposizione in due tipologie:
1) LLM caricati in locale: utilizziamo Ollama per per eseguire localmente modelli (esempi: *CodeLlama*, *CodeGemma*, *Mistral*, *Cogito*, *Ornith*, ecc.).
2) LLM in cloud: usufruiamo dei servizi IA offerti da Google Gemini API, che tramite un account ti permette di generare una chiave
per eseguire un loro LLM. In questo modo al tuo pc non verranno richieste risorse per eseguire LLM. Attenzione: un account gratuito
ti concede un utilizzo limitato degli LLM (es: 20 richieste massime al giorno).
Per ora è disponibile un solo LLM di Google:
* **`gemini-3.1-pro-preview`** (Provider: Google Gemini API) - Modello cloud ad alte prestazioni.

### 2. Esecuzione Batch per Server/Cluster (`main_server.py`)
Script progettato specificamente per l'esecuzione su cluster HPC con risorse maggiori, mirato a testare modelli da 30B a 70B di parametri.Non richiede Ollama: scarica e avvia i modelli direttamente tramite l'integrazione nativa Hugging Face.
* **Selezione Modello:** I modelli vengono gestiti dinamicamente tramite argomento a riga di comando. 
* Puoi visualizzare gli alias dei modelli attualmente configurati eseguendo:
  ```bash
  python main_server.py --help
  ``` 
## 🛠️ Requisiti e Configurazione

### 1. Prerequisiti
* **Python 3.12+**
* **Ollama** installato e attivo (necessario se desideri usare un LLM in locale)
* **API Key di Google AI Studio** (necessario solo se desideri usare Gemini)
* **Access Token di Hugging Face** (necessario **solo** se usi `main_server.py` con modelli "gated" come Gemma)

Se intendi usare un LLM tramite Ollama, devi prima scaricare il modello in locale usando:
```bash
ollama run NomeModello
```
Ad esempio:
```bash
ollama run qwen2.5-coder:7b
```

### 2. Installazione delle Dipendenze
Clona la repository e installa i pacchetti necessari tramite il file requirements.txt:
```bash
git clone https://github.com/tuo-utente/robotic-farm-domain-generator.git
cd robotic-farm-domain-generator

# Creazione dell'ambiente virtuale
python3 -m venv .venv

# Attivazione dell'ambiente virtuale
# in Linux
source .venv/bin/activate
# in Windows
.venv\Scripts\activate.bat

# Aggiornamento pip e installazione delle dipendenze
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurazione del File .env
Copia il file di esempio .env.example per creare il tuo file di configurazione d'ambiente .env:
```bash
cp .env.example .env
```

Apri il file .env e inserisci la tua chiave API o il token se usi Gemini o Hugging Face:
```env
LLM_GEMINI_KEY="la_tua_chiave_api_qui"
HF_TOKEN="il_tuo_token_huggingface_qui"
```

## 💻 Guida all'Uso

### Esecuzione Locale
Assicurati che l'ambiente virtuale sia attivo ed esegui:
```bash
python main.py
```

Per l'esecuzione in un cluster i comandi possono cambiare in base alle istruzioni definite dal proprietario del cluster.

