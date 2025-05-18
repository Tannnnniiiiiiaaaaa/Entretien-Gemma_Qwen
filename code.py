import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI
import time
import json

# 1. Charger les variables d'environnement (.env)
load_dotenv()

# 2. Lire chemins vers les fichiers PDF
pdf_keys = [f"PDF_{i}" for i in range(1, 30)]  # 29 entretiens
pdf_paths = [os.getenv(k) for k in pdf_keys]

# 3. Vérifier que les fichiers existent
for idx, path in enumerate(pdf_paths, 1):
    if not path or not os.path.exists(path):
        raise ValueError(f"❌ Fichier PDF introuvable pour Entretien {idx} : {path}")

# 4. Initialiser le client Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# 5. Fonction pour lire un PDF
def lire_pdf(chemin):
    texte = ""
    with fitz.open(chemin) as doc:
        for page in doc:
            texte += page.get_text()
    return texte

# 6. Fonction pour analyser un morceau de texte
def analyser_entretien_texte(entretien_texte, idx):
    prompt = f"""
Tu es un sociologue expert en analyse qualitative.

Voici un extrait d'entretien réalisé avec un étudiant :

\"\"\"{entretien_texte}\"\"\"

Ta tâche :
- Identifie des thèmes généraux pertinents,
- Pour chaque thème, donne un sous-thème spécifique,
- Et pour chaque sous-thème, donne un verbatim exact (citation tirée du texte).

Réponds uniquement avec le format suivant (sans introduction, sans analyse), 3 à 5 blocs maximum :

Thème : [nom du thème]  
Sous-thème : [nom du sous-thème]  
Verbatim : "Phrase complète tirée du texte, sans la tronquer, même si elle est longue."

Important :
- N'utilise pas de format JSON.
- Ne dépasse pas 500 tokens.
- Reste concis et clair.
"""
    try:
        response = client.chat.completions.create(
            model="qwen-qwq-32b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"⛔ Erreur API pour Entretien {idx} : {e}")
        if "rate limit" in str(e).lower():
            print("⏳ Attente 65 sec (limite atteinte)")
            time.sleep(65)
        return f"[Erreur lors de l'analyse : {e}]"

# 7. Créer dossier de résultats
os.makedirs("resultats_qwen", exist_ok=True)

# 8. Boucle sur les entretiens
#for idx, path in enumerate(pdf_paths, 1):
for idx, path in [(27, pdf_paths[26])]:
    print(f"\n🔍 Analyse de l'entretien {idx}...")

    texte = lire_pdf(path)

    # Diviser en morceaux de 1000 caractères
    morceaux = [texte[i:i+1500] for i in range(0, len(texte), 1500)]
    # Limiter le nombre de morceaux à 3 maximum
    morceaux = morceaux[:5]
    analyses = []

    for i, morceau in enumerate(morceaux):
        print(f"→ Analyse du morceau {i+1} / {len(morceaux)}")
        reponse = analyser_entretien_texte(morceau, idx)

        # Séparer chaque bloc (par thème) en listant proprement
        blocs = [bloc.strip() for bloc in reponse.split("Thème : ") if bloc.strip()]
        for bloc in blocs:
            lignes = bloc.splitlines()
            theme = sous_theme = verbatim = None
            for ligne in lignes:
                if ligne.startswith("Sous-thème"):
                    sous_theme = ligne.replace("Sous-thème :", "").strip()
                elif ligne.startswith("Verbatim"):
                    verbatim = ligne.replace("Verbatim :", "").strip().strip('"')
                else:
                    theme = ligne.strip()
            if theme and sous_theme and verbatim:
                analyses.append({
                    "theme": theme,
                    "sous_theme": sous_theme,
                    "verbatim": verbatim
                })
        time.sleep(17)

    # Enregistrer dans un fichier JSON
    fichier_resultat = f"resultats_qwen/Entretien_{idx}.json"
    with open(fichier_resultat, "w", encoding="utf-8") as f:
        json.dump(analyses, f, indent=2, ensure_ascii=False)

    print(f"✅ Résultat enregistré dans : {fichier_resultat}")

print("\n🎉 Tous les entretiens ont été analysés et enregistrés dans le dossier 'resultats'.")