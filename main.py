# Moduli fondamentali per la gestione di LLM e PDDL
from l2p import DomainBuilder, UnifiedLLM, DomainValidator # fondamentali per generare un file domain.pddl e rilevare evenuali errori
from l2p.feedback_builder import FeedbackBuilder # per correggere eventuali errori nel dominio
from l2p.prompt_builder import PromptBuilder # per aiutare LLM nel comprendere come eseguire correttamente il suo compito

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_format import format_types, format_predicates, format_actions
from l2p.utils.pddl_prompt import load_custom_template, load_default_template # per caricare i template custom o quelli di default di l2p (legati a PromptBuilder)

# Librerie di sistema e utilità
import sys # per far terminare prima il programma in caso di errori
import time # calcola tempo di esecuzione del programma
import questionary # genera un menu a scelta
from dotenv import load_dotenv # per caricare le variabili d'ambiente

# Caricamento delle variabili d'ambiente dal file .env
load_dotenv()

# Costanti dell'applicazione
DOMAIN_NAME = "CAMPI"
MAX_ATTEMPTS = 5
# Modelli in locale
QWEN_NAME = "qwen2.5-coder:7b"
CODE_LAMA = "codellama:latest"
CODE_GEMMA = "codegemma:latest"
MISTRAL_ORCA = "mistral-openorca:7b"
ORNITH = "ornith-1.5:9b"
COGITO = "cogito:8b"
# Modelli in cloud
GEMINI_3_FLASH  = "gemini-3-flash-preview"
GEMINI_25_LITE = "gemini-2.5-flash-lite"
GEMINI_31_LITE  = "gemini-3.1-flash-lite"
GEMINI_35_LITE  = "gemini-3.5-flash-lite"
GEMINI_38_FLASH = "gemini-3.8-flash"

def termina_programma(message):
    sys.exit(message)

# dizionario per la manutenibilità del codice
PROVIDERS = {
    QWEN_NAME: "ollama",
    CODE_LAMA: "ollama",
    CODE_GEMMA: "ollama",
    MISTRAL_ORCA: "ollama",
    ORNITH: "ollama",
    COGITO: "ollama",
    GEMINI_3_FLASH: "gemini",
    GEMINI_25_LITE: "gemini",
    GEMINI_31_LITE: "gemini",
    GEMINI_35_LITE: "gemini",
    GEMINI_38_FLASH: "gemini",
}

# Menu interattivo sul terminale per la selezione del modello LLM
response = questionary.select(
    "Quale intelligenza artificiale vuoi utilizzare?",
    choices=[QWEN_NAME, CODE_LAMA, CODE_GEMMA, MISTRAL_ORCA, ORNITH, COGITO, GEMINI_3_FLASH, GEMINI_25_LITE, GEMINI_31_LITE, GEMINI_35_LITE, GEMINI_38_FLASH ],
    instruction="", # Rimuove l'indicazione "(Use arrow keys)"
).ask()


# Inizializzazione del provider LLM selezionato dall'utente (qui utilizzo il dizionario)
if response not in PROVIDERS:
    raise ValueError(f"Hai selezionato un LLM non supportato: {response}")

llm = UnifiedLLM(
    provider=PROVIDERS[response],
    model=response,
    config_path="my_llm.yaml"
)

print("\nSalvataggio template di default")
# Costruzione del prompt basato sul template l2p + regole personalizzate per gli errori specifici riscontrati
p_types = (
    PromptBuilder()
    .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain types (:types).")
    .set_format("Wrap a VALID JSON ARRAY inside the <types> ... </types> XML tags.")
    .add_rule("CRITICAL LANGUAGE RULE: All type names MUST be written strictly in ITALIAN to match the problem file objects.")
    .add_rule("CRITICAL: Do NOT create inner XML tags like <type>...</type>.")
    .add_rule("CRITICAL: The content inside <types> MUST be ONLY a raw JSON array [ ... ].")
    .add_rule("CRITICAL PDDL RULE: Do NOT include 'object' as a type. 'object' is a reserved PDDL keyword and is implicit. Start your hierarchy directly from user types (parent: 'object').")
    .add_rule("""EXACT OUTPUT FORMAT REQUIRED:
        <types>
        [
            {"name": "contadino", "parent": "object"},
            {"name": "campo", "parent": "object"}
        ]
        </types>""")
    .add_rule("Do NOT reuse type names as predicate names.")
    .set_task("Please process the domain description provided.")
)

# carico il template personalizzato per i tipi
p_types.save_prompt(filename="custom_template/custom_types_prompt.md")
custom_prompt_types = load_custom_template(filepath="custom_template/custom_types_prompt.md")

# Costruzione del prompt per i PREDICATI
pb_predicates = (
    PromptBuilder()
    .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain predicates (:predicates).")
    .set_format("Wrap a VALID JSON ARRAY inside the <predicates> ... </predicates> XML tags.")
    .add_rule("CRITICAL: Do NOT create inner XML tags like <predicate>...</predicate>.")
    .add_rule("CRITICAL: The content inside <predicates> MUST be ONLY a raw JSON array [ ... ]. Do not use markdown syntax block like ```json.")
    .add_rule("CRITICAL LANGUAGE RULE: All predicate names, descriptions, and type references MUST be strictly in ITALIAN.")
    .add_rule("CRITICAL COMPATIBILITY RULE: Carefully read the Problem file snippet included in the description. Ensure your predicates match the entities and initial states provided (e.g., how tools or tractor types are defined).") # 
    .add_rule("""EXACT OUTPUT FORMAT REQUIRED:
<predicates>
[
  {
    "name": "at",
    "params": [
      {"variable": "?x", "type": "contadino"}, 
      {"variable": "?y", "type": "campo"}
    ],
    "desc": "The farmer ?x is at field ?y"
  },
  {
    "name": "innaffiato",
    "params": [
      {"variable": "?c", "type": "campo"}
    ],
    "desc": "Field ?c is watered"
  }
]
</predicates>""")
    .add_rule("CRITICAL: Look at the types provided in the context. DO NOT create unary predicates for concepts that are already defined as types (e.g., do NOT create a predicate named 'campo', 'contadino', etc.).")
    .add_rule("All predicate names must be completely UNIQUE and different from any type name.")
    .set_task("Extract the necessary predicates for the domain.")
)

pb_predicates.save_prompt(filename="custom_template/custom_predicates_prompt.md")
custom_predicates_template = load_custom_template(filepath="custom_template/custom_predicates_prompt.md")

# carico invece il template di default per generare le azioni
pb_actions = (
    PromptBuilder()
    .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain actions (:actions).")
    .set_format("Wrap a VALID JSON ARRAY inside the <actions> ... </actions> XML tags.")
    .add_rule("CRITICAL: The content inside <actions> MUST be ONLY a raw JSON array [ ... ] containing action objects, NOT raw PDDL code.")
    .add_rule("CRITICAL LANGUAGE RULE: All action names, parameters, descriptions, and type constraints MUST be strictly in ITALIAN.")
    .add_rule("CRITICAL NAMING RULE: Action names must be clean, grammatically correct Italian verbs/phrases. Do NOT create distorted words or duplicate syllables like 'arara-campo' or 'depona-'.")
    .add_rule("""EXACT JSON STRUCTURE REQUIRED PER ACTION:
    {
        "name": "action-name",
        "params": [
            {"variable": "?c", "type": "contadino"},
            {"variable": "?t", "type": "trattore"}
        ],
        "preconditions": {
            "conditions": ["(at ?c ?loc)", "(at ?t ?loc)"]
        },
        "effects": {
            "add": ["(a-bordo ?c ?t)"],
            "delete": ["(at ?c ?loc)"]
        },
        "desc": "Description of the action"
    }""")
    .add_rule("CRITICAL RULE FOR DRIVING (guida-trattore): When a farmer is `a-bordo` of a tractor and drives it, ONLY the tractor changes its position. Do NOT add an independent `at` effect for the farmer at the destination, because they move implicitly while `a-bordo`.")
    .add_rule("CRITICAL COMPATIBILITY: Ensure action parameters and types strictly match the objects and initial state definitions from the Problem file snippet.")
    .set_task("Extract the necessary actions for the domain in JSON format.")
)

pb_actions.save_prompt(filename="custom_template/custom_actions_prompt.md")
custom_actions_template = load_custom_template(filepath="custom_template/custom_actions_prompt.md")

# Costruzione del prompt per la REVISIONE (FeedbackBuilder)
pb_revise = (
    PromptBuilder()
    .set_role("You are an expert PDDL Revision Agent. Your job is to fix failed PDDL component generations based on diagnostic feedback.")
    .set_format("You MUST output the components wrapped in their exact XML tags.")
    .add_rule("CRITICAL FORMAT FOR <types>: Must be a VALID JSON ARRAY of objects (e.g., [{'name': '...', 'parent': '...'}]. NEVER write native PDDL text here. Do NOT include 'object' as a type).")
    .add_rule("CRITICAL FORMAT FOR <predicates>: Must be a VALID JSON ARRAY of objects with keys 'name', 'params' (containing a list of objects with 'variable' and 'type'), and 'desc'. NEVER write native PDDL text like '(?c - contadino)' inside predicates.")
    .add_rule("CRITICAL FORMAT FOR <actions>: Can use standard PDDL action blocks.")
    .add_rule("CRITICAL PDDL RULE: Types and Predicates CANNOT share the same names.")
    .add_rule("Output ONLY the requested XML blocks. No conversational text.")
    .set_task("Revise the following PDDL component(s) based on the diagnostic feedback.\n{context}")
)

pb_revise.save_prompt(filename="custom_template/custom_revise_prompt.md")
custom_revise_template = load_custom_template(filepath="custom_template/custom_revise_prompt.md")

#-----------------------------------------------------
# INIZIO CREAZIONE DOMAIN.PDDL
#-----------------------------------------------------
print("\n\nInizio Generazione Domain PDDL")
# istanzio le classi necessarie
# istanza del DomainBuilder: classe che permette di creare a partire da una descrizione in linguaggio umano il dominio del problema PDDL
domain_builder = DomainBuilder()

# Istanza del FeedbackBuilder
feedback_builder = FeedbackBuilder()

domain_desc = """

Ci sono K1 trattori per arare, K2 trattori per seminare, K3 contadini, N campi, un certo numero di aratri e seminatori. Un trattore per l'aratura potrebbe essere adatto anche per la semina e viceversa. Ogni campo deve essere prima arato, poi seminato ed infine innaffiato.
Per innaffiare e' sufficiente che una contadino si trovi sul campo, ad es: se vale  (at contadino1 campo5), allora il campo 5 puo' essere innaffiato (ammesso che prima sia stato seminato - condizione NECESSARIA).
NOTA: un trattore non si sposta da solo: il contadino deve essere a bordo del trattore. Ovviamente un contadino deve anche poter scendere da un trattore....
 
File problema di test:

(define (problem Dieci-Campi)
  (:domain CAMPI)
  (:objects traA1 traA2 traS1 traS2 aratro1 aratro2 seminatore1 seminatore2
     contadino1 contadino2
     cam1 cam2 cam3 cam4 cam5
     cam6 cam7 cam8 cam9 cam10)
  (:init
   (contadino contadino1)
   (contadino contadino2)
   (CAMPO cam1)
   (CAMPO cam2)
   (CAMPO cam3)
   (CAMPO cam4)
   (CAMPO cam5)
   (CAMPO cam6)
   (CAMPO cam7)
   (CAMPO cam8)
   (CAMPO cam9)
   (CAMPO cam10)
   (TRA traA1)
   (TRA traA2)
   (TRA traS1)
   (TRA traS2)
   (TRA-ARA traA1)
   (TRA-ARA traA2)
   (TRA-SEMINA traS1)
   (TRA-SEMINA traS2)
   (ARATRO aratro1)
   (ARATRO aratro2)
   (SEMINATORE seminatore1)
   (SEMINATORE seminatore2)
   (CONNESSO cam1 cam2)
   (CONNESSO cam2 cam1)
   (CONNESSO cam2 cam3)
   (CONNESSO cam3 cam2)
   (CONNESSO cam3 cam4)
   (CONNESSO cam4 cam3)
   (CONNESSO cam4 cam5)
   (CONNESSO cam5 cam4)
   (CONNESSO cam5 cam2)
   (CONNESSO cam2 cam5)
   (CONNESSO cam5 cam6)
   (CONNESSO cam6 cam5)
   (CONNESSO cam6 cam7)
   (CONNESSO cam7 cam6)
   (CONNESSO cam7 cam8)
   (CONNESSO cam8 cam7)
   (CONNESSO cam8 cam1)
   (CONNESSO cam1 cam8)
   (CONNESSO cam8 cam9)
   (CONNESSO cam9 cam8)
   (CONNESSO cam9 cam10)
   (CONNESSO cam10 cam9)
   (CONNESSO cam5 cam1)
   (CONNESSO cam1 cam5)
   (at traA1 cam1);; dynamic predicates
   (at traA2 cam5)
   (at traS1 cam1)
   (at traS2 cam4)
   (at aratro1 cam3)
   (at aratro2 cam8)
   (at seminatore1 cam2)
   (at seminatore2 cam6)
   (at contadino1 cam1)
   (at contadino2 cam5)
   )
 
  (:goal (and
   (innaffiato cam6)
   (innaffiato cam7)
   (innaffiato cam8)
   (innaffiato cam9)
   (innaffiato cam10)
   (seminato cam1)
   (seminato cam1)
   (seminato cam2)
   (seminato cam3)
   (seminato cam4)
   (seminato cam5)))
  )

"""

# inizio da qui a contare il tempo impiegato dall'LLM per risolvere il problema.
start_time = time.time()

# ============================================================
# 1. GENERAZIONE INIZIALE DEI COMPONENT DEL FILE DOMAIN.PDDL
# ============================================================
print("[INFO] Generazione iniziale dei componenti (Tipi, Predicati, Azioni)...")

# Tipi
try:
    types_results, llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=PDDLType,
        description=domain_desc,
        prompt_template=custom_prompt_types
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione dei tipi: {e}")

extracted_types = types_results[PDDLType]
types_str = format_types(extracted_types)
print("--- TIPI GENERATI ---\n")
print(types_str)  # stampa i tipi estratti dall'LLM

# Predicati
try:
    predicates_results, predicates_llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=Predicate,   # Specifichiamo di voler estrarre i predicati
        description=domain_desc,     # Usiamo la stessa descrizione
        types=extracted_types,        # Passiamo i tipi all'LLM per garantirne la coerenza
        prompt_template=custom_predicates_template
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione dei predicati: {e}")

extracted_predicates = predicates_results[Predicate] #  Estraiamo la lista dei predicati dal dizionario dei risultati
predicates_str = format_predicates(extracted_predicates)  # Formattiamo i predicati in sintassi PDDL standard usando le utils della libreria
print("--- PREDICATI GENERATI ---\n")
print(predicates_str)

# Azioni
try:
    actions_results, actions_llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=Action,
        description=domain_desc,
        types=extracted_types,
        predicates=extracted_predicates,
        prompt_template=custom_actions_template
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione delle azioni: {e}")

extracted_actions = actions_results[Action]  # Estraiamo la lista delle azioni
actions_str = format_actions(extracted_actions) # Formattiamo le azioni in sintassi PDDL standard
print("\n--- AZIONI GENERATE ---")
print(actions_str)


# =======================================================
# 2. PRIMA COSTRUZIONE E VALIDAZIONE
# =======================================================
# Costruisco il contenuto del file
domain_pddl_content = f"""(define (domain {DOMAIN_NAME})
  (:requirements :typing :strips :negative-preconditions)

  (:types
{types_str}
  )

  (:predicates
{predicates_str}
  )

{actions_str}
)"""

domain_details = DomainDetails(
    name=DOMAIN_NAME,
    types=extracted_types,
    predicates=extracted_predicates,
    actions=extracted_actions,
    domain_pddl=domain_pddl_content
)

domain_validator = DomainValidator()
domain_result = domain_validator.validate_domain(domain_details)

# =======================================================
# 3. CICLO DI SELF-CORRECTION (Si attiva SOLO se fallisce)
# =======================================================
current_attempt = 1

while not domain_result.valid and current_attempt <= MAX_ATTEMPTS:
    print(f"\n[ERRORE] Validazione semantica PDDL fallita. Avvio Self-Correction {current_attempt}/{MAX_ATTEMPTS}...")
    print(f"Errori: {domain_result.errors}\n")

    # Fase A: Diagnosi dell'errore PDDL
    diagnosis_result, raw_text_diag = feedback_builder.llm_diagnose(
        model=llm,
        artifact=domain_details,
        errors=domain_result.errors,
        description=domain_desc
    )

    # Fase B: Revisione intelligente dei componenti
    # (Qui max_retries interverrà automaticamente se sbaglia l'XML)
    try:
        revised_results, raw_text_rev = feedback_builder.llm_revise(
            model=llm,
            artifact=domain_details,
            component_class=[PDDLType, Predicate, Action],
            diagnosis=diagnosis_result,
            description=domain_desc,
            prompt_template=custom_revise_template
        )
    except (ValueError, RuntimeError) as e:
        termina_programma(f"Errore durante la revisione dei componenti PDDL: {e}")

    
    # Aggiorna i componenti corretti
    if PDDLType in revised_results:
        extracted_types = revised_results[PDDLType]
    if Predicate in revised_results:
        extracted_predicates = revised_results[Predicate]
    if Action in revised_results:
        extracted_actions = revised_results[Action]

    types_str = format_types(extracted_types)
    predicates_str = format_predicates(extracted_predicates)
    actions_str = format_actions(extracted_actions)
    
    # Ricostruisci il file PDDL con i componenti aggiornati
    domain_pddl_content = f"""(define (domain {DOMAIN_NAME})
        (:requirements :typing :strips :negative-preconditions)

        (:types
        {types_str}
        )

        (:predicates
        {predicates_str}
        )

        {actions_str}
        )"""

    domain_details.domain_pddl = domain_pddl_content
    domain_details.types = extracted_types
    domain_details.predicates = extracted_predicates
    domain_details.actions = extracted_actions

    # Determinare se il dominio e' corretto o se e' necessario correggerlo nuovamente
    domain_result = domain_validator.validate_domain(domain_details)
    current_attempt += 1


# =======================================================
# 4. RISULTATO FINALE
# =======================================================
if domain_result.valid:
    print(f"\n[OK] Domain PDDL valido e pronto! Generato in {current_attempt} iterazione/i.")
    print("--- ANTEPRIMA DEL FILE DOMAIN.PDDL ---\n")
    print(domain_pddl_content)

    # --- SALVATAGGIO DEL FILE SU DISCO ---
    filename_output = "domain.pddl"
    with open(filename_output, "w", encoding="utf-8") as f:
        f.write(domain_pddl_content)
    print(f"\n[SALVATAGGIO] File scritto correttamente come: '{filename_output}' nella cartella di lavoro.")
else:
    termina_programma(f"\n[FATAL] L'LLM ha fallito la generazione dopo {MAX_ATTEMPTS} tentativi. Ultimi errori: {domain_result.errors}")

end_time = time.time()
print(f"\n[TIMER] Tempo totale di esecuzione: {end_time - start_time:.2f} secondi")
