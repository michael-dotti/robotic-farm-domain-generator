# Moduli fondamentali per la gestione di LLM e PDDL
from l2p import DomainBuilder, UnifiedLLM, DomainValidator # fondamentali per generare un file domain.pddl e rilevare evenuali errori
from l2p.feedback_builder import FeedbackBuilder # per correggere eventuali errori nel dominio
from l2p.prompt_builder import PromptBuilder # per aiutare LLM nel comprendere come eseguire correttamente il suo compito

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_format import format_types, format_predicates, format_actions
from l2p.utils.pddl_prompt import load_custom_template, load_default_template # per caricare i template custom o quelli di default di l2p (legati a PromptBuilder)

# Librerie di sistema e utilità
import sys # per far terminare prima il programam in caso di errori
import time # calcola tempo di esecuzioen del programma
import questionary # genera un menu a scelta
from dotenv import load_dotenv # per caricare le variabili d'ambiente

# Caricamento delle variabili d'ambiente dal file .env
load_dotenv()

# Costanti dell'applicazione
DOMAIN_NAME = "CAMPI"
QWEN_NAME = "qwen2.5-coder:7b"
GEMINI_NAME = "gemini-3.1-pro-preview"
MAX_ATTEMPTS = 5

def termina_programma(message):
    sys.exit(message)


# Menu interattivo sul terminale per la selezione del modello LLM
response = questionary.select(
    "Quale intelligenza artificiale vuoi utilizzare?",
    choices=[QWEN_NAME,GEMINI_NAME],
    instruction="", # Rimuove l'indicazione "(Use arrow keys)"
).ask()


# Inizializzazione del provider LLM selezionato dall'utente
if response == QWEN_NAME:
    llm = UnifiedLLM(
        provider="ollama",
        model=QWEN_NAME,
        config_path="my_llm.yaml"
    )
elif response == GEMINI_NAME:
    llm = UnifiedLLM(
        provider="gemini",
        model=GEMINI_NAME,
        config_path="my_llm.yaml"
    )
else:
    raise ValueError(f"Hai selezionato un LLM non supportato: {response}")


print("\nSalvataggio template di default")
# Costruzione del prompt basato sul template l2p + regole personalizzate per gli errori specifici riscontrati
p_types = (
    PromptBuilder()
    .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain types (:types).")
    .set_format("Wrap a VALID JSON ARRAY inside the <types> ... </types> XML tags.")
    .add_rule("CRITICAL: Do NOT create inner XML tags like <type>...</type>.")
    .add_rule("CRITICAL: The content inside <types> MUST be ONLY a raw JSON array [ ... ].")
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
    .add_rule("""EXACT OUTPUT FORMAT REQUIRED:
<predicates>
[
  {
    "name": "at",
    "parameters": [
      {"name": "?x", "type": "contadino"},
      {"name": "?y", "type": "CAMPO"}
    ],
    "desc": "The farmer ?x is at field ?y"
  },
  {
    "name": "innaffiato",
    "parameters": [
      {"name": "?c", "type": "CAMPO"}
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
actions_template = load_default_template("domain","prompt_actions.md")

# Costruzione del prompt per la REVISIONE (FeedbackBuilder)
pb_revise = (
    PromptBuilder()
    .set_role("You are an expert PDDL Revision Agent. Your job is to fix failed PDDL component generations based on diagnostic feedback.")
    .set_format("You MUST output the corrected components wrapped in their exact XML tags: <types> for types, <predicates> for predicates, and <actions> for actions.")
    .add_rule("CRITICAL: You MUST wrap the JSON output in the correct XML tags (e.g., <types> ... </types>). Do NOT use generic markdown like ```json.")
    .add_rule("CRITICAL PDDL RULE: Types and Predicates CANNOT share the same names. If the error says a name is already in use, rename or remove the duplicate predicate.")
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

# =======================================================
# 1. GENERAZIONE INIZIALE (Fuori da qualsiasi ciclo)
# =======================================================
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
        prompt_template=actions_template
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
    print(f"\n[OK] Domain PDDL valido e pronto! Generato in {current_attempt} iterazioni.")
    print("--- ANTEPRIMA DEL FILE DOMAIN.PDDL ---\n")
    print(domain_pddl_content)
else:
    termina_programma(f"\n[FATAL] L'LLM ha fallito la generazione dopo {MAX_ATTEMPTS} tentativi. Ultimi errori: {domain_result.errors}")

end_time = time.time()
print(f"\n[TIMER] Tempo totale di esecuzione: {end_time - start_time:.2f} secondi")
