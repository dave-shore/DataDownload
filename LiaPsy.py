from openai import OpenAI
import pandas as pd
import numpy as np
from pymongo import MongoClient
from tqdm.auto import tqdm

BASE_PROMPT = """
    Devi generare un diario che copra un intero anno di un utente con sintomi di ansia, depressione e disturbi bipolari.
    L'utente è un uomo di 28 anni di Milano, Italia, attualmente dottorando in intelligenza artificiale.
    Non ha molta fortuna con le donne, non è sportivo ma vorrebbe essere in forma e gli piacciono la letteratura e la musica.
    Gli è stato chiesto di tenere un diario dalla sua psicoterapeuta come modo per tracciare eventi, pensieri, emozioni e sensazioni fisiche.
"""

def read_api_key():
    with open("openai_key.txt", "r") as f:
        key = f.read().strip()
    return key
    
def real_roles(role):
    if role == "assistant":
        return "Utente"
    elif role == "user":
        return "Titolo"
    elif role == "developer":
        return "Base"
    else:
        return role
    
def generate_journal(client, base_prompt):

    date_index = pd.date_range('2025-01-01', '2025-12-31').strftime('%A %d %B').tolist()

    number_of_words = np.random.randint(50, 250)

    messages = [
        {
            "role": "developer",
            "content": base_prompt
        },
        {
            "role": "user",
            "content": f"Genera la pagina di {date_index[0]} in massimo {number_of_words} parole"
        }
    ]

    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = messages,
        temperature = 0.5
    )

    messages.append(
        {
            "role": "assistant",
            "content": response.choices[0].message.content
        }
    )

    for date in tqdm(date_index[1:]):

        number_of_words = np.random.randint(50, 250)

        messages.append(
            {
                "role": "user",
                "content": f"Genera la pagina di {date} in massimo {number_of_words} parole"
            }
        )

        last_messages = messages[-7:] if len(messages) > 7 else messages

        response = client.chat.completions.create(
            model = "gpt-4o-mini",
            messages = [messages[0]] + last_messages,
            temperature = 0.5
        )

        messages.append(
            {
                "role": "assistant",
                "content": response.choices[0].message.content
            }
        )

    messages = list(map(lambda d: {"Role": real_roles(d["role"]), "Text": d["content"]}, messages))

    return messages


def insert_into_mongodb(data):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["LIA-Psy"]
    collection = db["demo"]
    collection.insert_many(data)


if __name__ == "__main__":
    api_key = read_api_key()
    openai = OpenAI(api_key=api_key)
    journal = generate_journal(openai, BASE_PROMPT)
    insert_into_mongodb(journal)
