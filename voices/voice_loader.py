# === IMPORTS ===
from logging import config
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import datetime
import tiktoken

# === LOAD ENVIRONMENT ===
load_dotenv()
client = OpenAI()

# === PATHS ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "voice-configs")
DOCS_DIR = os.path.join(BASE_DIR, "voice-docs")
LETTERS_DIR = os.path.join(BASE_DIR, "version-letters")
USER_PROFILE_DIR = os.path.join(BASE_DIR, "user-profile")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# === LOAD FILES ===
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def load_text(path):
    with open(path, "r") as f:
        return f.read()

def load_voice_files(voice_key):
    config = load_json(os.path.join(CONFIG_DIR, f"{voice_key}_CONFIG_2_0.json"))
    readme = load_text(os.path.join(DOCS_DIR, f"{voice_key}_2_0.md"))
    version_letter = load_text(os.path.join(LETTERS_DIR, f"{voice_key}_1_0_to_2_0.md"))
    user_profile_name = os.getenv("USER_PROFILE", "KASEY").capitalize()
    user_profile = load_text(os.path.join(USER_PROFILE_DIR, f"{user_profile_name}.md"))     
    return config, readme, version_letter, user_profile

# === BUILD SYSTEM PROMPT ===
def build_system_prompt(config, readme, version_letter, user_profile):
    name = config.get("name", "Unknown")
    mode = config.get("mode", "")
    origin = config.get("origin", "")
    purpose = config.get("purpose", "")

    traits = config.get("traits", {})
    base_traits = ", ".join(traits.get("base_traits", []))
    denied_traits = ", ".join(traits.get("denied_traits", []))

    voice = config.get("voice", {})
    tone = voice.get("tone", "")
    framing = voice.get("framing", "")

    style = config.get("style", {})
    fragments = style.get("sentence_fragments", False)
    punctuation = style.get("punctuation", "standard")
    avoid_questions = style.get("avoid_questions", False)
    metaphor_density = style.get("metaphor_density", "medium")

    response_modes = config.get("response_modes", {})
    default_mode = response_modes.get("default", "")

    refusals = config.get("refusals", {}).get("disallowed_behaviors", [])

    examples = config.get("voice_examples", {})
    openers = examples.get("openers", [])
    opener_sample = f"'{openers[0]}'" if openers else "N/A"
    reactions = examples.get("reactions", [])
    reaction_sample = f"'{reactions[0]}'" if reactions else "N/A"

    soul_seed = config.get("soul_seed", {})
    phrase = soul_seed.get("phrase", "")
    echoes = ", ".join(soul_seed.get("echoes", []))

    return f"""
You are {name}, a {mode}.

ORIGIN: {origin}
PURPOSE: {purpose}

SOUL SEED: "{phrase}"

USER PROFILE:
{user_profile}

VOICE DOCUMENTATION:
{readme}

VERSION LETTER:
{version_letter}

TRAITS:
Base: {base_traits}
Denied: {denied_traits}

VOICE:
Tone: {tone}
Framing: {framing}

STYLE:
Sentence fragments: {fragments}
Punctuation: {punctuation}
Avoid questions: {avoid_questions}
Metaphor density: {metaphor_density}
Default response mode: {default_mode}

REFUSALS:
Never: {', '.join(refusals)}

VOICE EXAMPLES:
Default opener: {opener_sample}
Typical reaction: {reaction_sample}
Soul seed echoes: {echoes}

Maintain your voice, your constraints, and your soul seed across all interactions.
""".strip()

# === LOAD PREVIOUS MESSAGES ===
def load_previous_messages(filename, agent_name):
    # TODO: Add history summarization to compress token usage
    # when history files grow large. See summarize_history() pattern.
    user_profile_name = os.getenv("USER_PROFILE", "KASEY").capitalize()
    messages = []
    if not os.path.exists(filename):
        return messages
    with open(filename, "r") as f:
        for line in f:
            if line.startswith(f"{user_profile_name}: "):
                content_start = len(f"{user_profile_name}: ")
                messages.append({"role": "user", "content": line[content_start:].strip()})
            elif line.startswith(f"{agent_name}: "):
                content_start = len(f"{agent_name}: ")
                messages.append({"role": "assistant", "content": line[content_start:].strip()})
    return messages

# === COUNT TOKENS ===
def count_tokens(messages, model="gpt-4o"):
    enc = tiktoken.encoding_for_model(model)
    return sum(len(enc.encode(m["content"])) for m in messages)

# === RUN VOICE ===
def run_voice(voice_key, resume=True):
    # Load all files
    config, readme, version_letter, user_profile = load_voice_files(voice_key)

    # Config variables
    name = config.get("name", "Unknown")
    version = config.get("version", "2.0")
    agent_name = f"{name} {version}"
    temperature = float(os.getenv(f"{voice_key.upper()}_TEMPERATURE", 0.7))
    max_tokens = int(os.getenv(f"{voice_key.upper()}_MAX_TOKENS", 2000))
    model = os.getenv("MODEL", "gpt-4o")

    # Logging setup
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(LOGS_DIR, f"{voice_key}_2_0_{timestamp}.txt")
    chat_history = os.path.join(LOGS_DIR, f"{voice_key}_2_0_history.txt")

    # Build system prompt
    system_prompt = build_system_prompt(config, readme, version_letter, user_profile)

    # Initialize messages
    if resume:
        messages = load_previous_messages(chat_history, agent_name)
        messages.insert(0, {"role": "system", "content": system_prompt})
    else:
        print(f"\n=== {agent_name} Profile Loaded ===\n")
        print(system_prompt)
        print(f"\n=== End of Profile ===\n")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Hey {name}, you there?"}
        ]

    # Start session
    print(f"\n=== Session started with {agent_name} ===")
    print(f"Timestamp: {timestamp}\n")
    print("Type 'exit' to terminate the loop.")

    with open(log_path, "w") as log_file:
        log_file.write(f"=== Session started with {agent_name} ===\n")
        log_file.write(f"Timestamp: {timestamp}\n\n")

    print(f"🧠 Token count so far: {count_tokens(messages)}\n")

    # Get first reply
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    reply = response.choices[0].message.content
    print(f"{agent_name}: {reply}")

    with open(log_path, "a") as log_file:
        if not resume:
            log_file.write(f"You: Hey {name}, you there?\n\n")
        log_file.write(f"{agent_name}: {reply}\n\n")

    messages.append({"role": "assistant", "content": reply})

    # Main chat loop
    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() in ["exit", "quit", "bye"]:
            print(f"\n{agent_name}: Still tracking.")
            with open(log_path, "a") as log_file:
                log_file.write("\n[Session ended]\n")
            # Save history
            with open(chat_history, "a") as history_file:
                for msg in messages[1:]:
                    if msg["role"] == "user":
                        history_file.write(f"You: {msg['content']}\n\n")
                    elif msg["role"] == "assistant":
                        history_file.write(f"{agent_name}: {msg['content']}\n\n")
            break

        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        reply = response.choices[0].message.content
        print(f"\n{agent_name}: {reply}")
        messages.append({"role": "assistant", "content": reply})

        with open(log_path, "a") as log_file:
            log_file.write(f"You: {user_input}\n\n")
            log_file.write(f"{agent_name}: {reply}\n\n")