# Robotic Farm Domain Generator

Questo progetto è una pipeline automatizzata sviluppata con la libreria **`l2p`** per generare il file `domain.pddl` relativo allo scenario **Robotic Farm**, partendo da una descrizione del problema espressa in linguaggio naturale.

> ⚠️ **Status del Progetto: Work in Progress (WIP)**  
> La pipeline (estrazione Tipi, Predicati, Azioni e ciclo di Self-Correction) è completamente implementata, ma la calibrazione dei prompt e la generazione di un `domain.pddl` sintatticamente e semanticamente valido al 100% sono ancora in fase di perfezionamento.

---

## 🚀 Modelli LLM Supportati

All'avvio, la script presenta un menu interattivo che permette di scegliere tra due modelli:

1. **`qwen2.5-coder:7b`**  
   * **Provider:** Ollama (Locale)  
   * **Descrizione:** Modello open source eseguito interamente sulla macchina locale, ottimizzato per il codice.
2. **`gemini-3.1-pro-preview`**  
   * **Provider:** Google Gemini API (Cloud)  
   * **Descrizione:** Modello cloud ad alte prestazioni tramite API key.

---

## 🛠️ Requisiti e Configurazione

### 1. Prerequisiti
* **Python 3.10+**
* **Ollama** installato e attivo (necessario solo se desideri usare Qwen)
* **API Key di Google AI Studio** (necessario solo se desideri usare Gemini)

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
