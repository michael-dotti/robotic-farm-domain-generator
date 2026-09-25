# Moduli fondamentali per la gestione di LLM e PDDL
from l2p import DomainBuilder, DomainValidator, HUGGING_FACE
from l2p.feedback_builder import FeedbackBuilder
from l2p.prompt_builder import PromptBuilder

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_format import format_types, format_predicates, format_actions
from l2p.utils.pddl_prompt import load_custom_template, load_default_template

# Librerie di sistema e utilità
import sys
import time
import os
import argparse
from dotenv import load_dotenv

# Caricamento delle variabili d'ambiente dal file .env
load_dotenv()

# Costanti dell'applicazione
DOMAIN_NAME = "CAMPI"
MAX_ATTEMPTS = 5

def termina_programma(message):
    sys.exit(message)

#-----------------------------------------------------
# 0. CONFIGURAZIONE PER IL SERVER REMOTO
#-----------------------------------------------------
parser = argparse.ArgumentParser(description="Esecuzione L2P batch su cluster Slurm")
parser.add_argument(
    "--model", 
    type=str, 
    default="qwen", 
    choices=["qwen", "gemma"], 
    help="Modello Hugging Face da utilizzare (qwen o gemma)"
)
args = parser.parse_args()

# Assicuriamoci che la cartella dei template esista sul server
os.makedirs("custom_template", exist_ok=True)

# Recupera il token HF dal file .env (necessario per Gemma)
hf_token = os.getenv("HF_TOKEN")

# Inizializzazione di HUGGING_FACE
if args.model == "qwen":
    MODEL_ID = "Qwen/Qwen2.5-Coder-3B-Instruct"
    print(f"Inizializzazione Hugging Face, modello: {MODEL_ID}\n")
    llm = HUGGING_FACE(
        model=MODEL_ID,
        model_path=MODEL_ID, # Generalmente coincide con il nome del modello per il download
        config_path="my_llm.yaml",
        api_key=hf_token
    )
elif args.model == "gemma":
    MODEL_ID = "google/gemma-2-2b-it"
    print(f"Inizializzazione Hugging Face, modello: {MODEL_ID}\n")
    llm = HUGGING_FACE(
        model=MODEL_ID,
        model_path=MODEL_ID,
        config_path="my_llm.yaml",
        api_key=hf_token
    )

# =======================================================
# 1. COSTRUZIONE PROMPT
# =======================================================
print("\n[INFO] Salvataggio template...")

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

p_types.save_prompt(filename="custom_template/custom_types_prompt.md")
custom_prompt_types = load_custom_template(filepath="custom_template/custom_types_prompt.md")

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

actions_template = load_default_template("domain","prompt_actions.md")

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
print("\n[INFO] Inizio Generazione Domain PDDL")
domain_builder = DomainBuilder()
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

start_time = time.time()

# =======================================================
# 2. GENERAZIONE INIZIALE
# =======================================================
try:
    types_results, _ = domain_builder.formalize_component(
        model=llm,
        component_class=PDDLType,
        description=domain_desc,
        prompt_template=custom_prompt_types
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore estrazione tipi: {e}")

extracted_types = types_results[PDDLType]
types_str = format_types(extracted_types)

try:
    predicates_results, _ = domain_builder.formalize_component(
        model=llm,
        component_class=Predicate,
        description=domain_desc,
        types=extracted_types,
        prompt_template=custom_predicates_template
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore estrazione predicati: {e}")

extracted_predicates = predicates_results[Predicate]
predicates_str = format_predicates(extracted_predicates)

try:
    actions_results, _ = domain_builder.formalize_component(
        model=llm,
        component_class=Action,
        description=domain_desc,
        types=extracted_types,
        predicates=extracted_predicates,
        prompt_template=actions_template
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore estrazione azioni: {e}")

extracted_actions = actions_results[Action]
actions_str = format_actions(extracted_actions)

# =======================================================
# 3. PRIMA COSTRUZIONE E VALIDAZIONE
# =======================================================
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
# 4. CICLO DI SELF-CORRECTION
# =======================================================
current_attempt = 1

while not domain_result.valid and current_attempt <= MAX_ATTEMPTS:
    print(f"\n[ERRORE] Validazione fallita. Self-Correction {current_attempt}/{MAX_ATTEMPTS}...")
    print(f"Errori: {domain_result.errors}")

    diagnosis_result, _ = feedback_builder.llm_diagnose(
        model=llm,
        artifact=domain_details,
        errors=domain_result.errors,
        description=domain_desc
    )

    try:
        revised_results, _ = feedback_builder.llm_revise(
            model=llm,
            artifact=domain_details,
            component_class=[PDDLType, Predicate, Action],
            diagnosis=diagnosis_result,
            description=domain_desc,
            prompt_template=custom_revise_template
        )
    except (ValueError, RuntimeError) as e:
        termina_programma(f"Errore revisione: {e}")
    
    if PDDLType in revised_results:
        extracted_types = revised_results[PDDLType]
    if Predicate in revised_results:
        extracted_predicates = revised_results[Predicate]
    if Action in revised_results:
        extracted_actions = revised_results[Action]

    types_str = format_types(extracted_types)
    predicates_str = format_predicates(extracted_predicates)
    actions_str = format_actions(extracted_actions)
    
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

    domain_result = domain_validator.validate_domain(domain_details)
    current_attempt += 1

# =======================================================
# 5. RISULTATO FINALE E SALVATAGGIO
# =======================================================
if domain_result.valid:
    print(f"\n[OK] Domain PDDL valido! Generato in {current_attempt} iterazioni.")
    
    # SALVA FISICAMENTE IL FILE (.pddl)
    with open("domain.pddl", "w", encoding="utf-8") as f:
        f.write(domain_pddl_content)
    print("[SUCCESS] File scritto su disco come 'domain.pddl'")
else:
    termina_programma(f"\n[FATAL] Fallito dopo {MAX_ATTEMPTS} tentativi. Errori: {domain_result.errors}")

end_time = time.time()
print(f"\n[TIMER] Tempo totale: {end_time - start_time:.2f} secondi")