import docx2txt
from PyPDF2 import PdfReader
import sqlite3
import streamlit as st
import pandas as pd
import nltk
nltk.download('punkt')  # Télécharge le modèle punkt si nécessaire
from nltk import tokenize
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
os.environ['NLTK_DATA'] = '/tmp/nltk_data'
import asyncio
from googletrans import Translator

translator = Translator()

# Fonction asynchrone pour traduire le texte
async def translate_text(text, target_lang='en'):
    translated = await translator.translate(text, dest=target_lang)
    return translated.text

# Fonction principale qui gère l'appel de la traduction
async def main(text):
    translated_text = await translate_text(text, target_lang='en')
    return translated_text

# Partie exécutée lorsque le script est lancé
if __name__ == "__main__":
    # Exemple de texte à traduire
    text = "Bonjour tout le monde"
    # Exécute la fonction main et attend le résultat de la traduction
    translated_text = asyncio.run(main(text))  # Cela renvoie directement le texte traduit
    print(f"Texte traduit : {translated_text}")

# Fonctions pour lire les fichiers
def read_text_file(file):
    content = ""
    try:
        content = file.getvalue().decode('utf-8')  # Premier essai avec UTF-8
    except UnicodeDecodeError:
        try:
            content = file.getvalue().decode('latin-1')  # Essai avec latin-1
        except Exception as e:
            st.error(f"Impossible de lire le fichier {file.name} : {str(e)}")
    return content

def read_docx_file(file):
    return docx2txt.process(file)

def read_pdf_file(file):
    text = ""
    pdf_reader = PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_text_from_file(uploaded_file):
    content = ""
    if uploaded_file is not None:
        st.write(f"Type de fichier: {uploaded_file.type}")  # Affichage du type de fichier
        if uploaded_file.type == "text/plain":
            content = read_text_file(uploaded_file)  # Traitement des fichiers .txt
        elif uploaded_file.type == "application/pdf":
            content = read_pdf_file(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            content = read_docx_file(uploaded_file)
        else:
            st.error("Format de fichier non pris en charge.")
    return content

# Fonction pour calculer la similarité entre deux textes en pourcentage
def get_similarity(text1, text2):
    text_list = [text1, text2]
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(text_list)
    similarity = cosine_similarity(count_matrix)[0][1]
    return similarity * 100  # Conversion en pourcentage

# Fonction pour extraire les phrases d'un texte
def get_sentences(text):
    sentences = tokenize.sent_tokenize(text)
    return sentences

# Fonction de connexion à la base de données SQLite
def connect_db():
    conn = sqlite3.connect("plagiarism.db")
    return conn

# Fonction pour créer les tables dans la base de données
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# Fonction pour insérer un fichier dans la base
def insert_file(filename, content):
    conn = connect_db()
    cursor = conn.cursor()
    # Vérifiez si le fichier existe déjà
    cursor.execute("SELECT id FROM files WHERE filename = ?", (filename,))
    existing_file = cursor.fetchone()

    if existing_file:
        # Si le fichier existe, on le met à jour avec le nouveau contenu
        cursor.execute("UPDATE files SET content = ? WHERE filename = ?", (content, filename))
        conn.commit()
        # st.success(f"Le fichier {filename} a été mis à jour dans la base de données.")
    else:
        # Si le fichier n'existe pas, on l'insère
        cursor.execute("INSERT INTO files (filename, content) VALUES (?, ?)", (filename, content))
        conn.commit() #
        # st.success(f"Le fichier {filename} a été ajouté avec succès.")

    conn.close()

# Fonction pour récupérer tous les fichiers
def get_all_files():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Fonction pour supprimer un fichier par son ID
def delete_file(file_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

# Fonction pour vider la base de données
def clear_database():
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files")  # Supprime tous les enregistrements de la table
        conn.commit()
        conn.close()
        return True  # Indique que l'opération a réussi
    except Exception as e:
        st.error(f"Une erreur est survenue lors du vidage de la base de données : {str(e)}")
        return False

# Fonction pour comparer les fichiers pivots et cibles et retourner les similarités
def get_pivot_similarity(pivot_texts, target_texts, pivot_filenames, target_filenames):
    similarity_list = []
    for i, pivot_text in enumerate(pivot_texts):
        for j, target_text in enumerate(target_texts):
            similarity = get_similarity(pivot_text, target_text)
            similarity_list.append((pivot_filenames[i], target_filenames[j], similarity))
    return similarity_list

def empty_database_button():
    """Renders a checkbox and button to clear the database."""
    confirmation = st.checkbox("Confirmer la suppression de tous les fichiers", value=False)
    if confirmation:
        if st.button("Vider la base de données"):
            if clear_database():
                st.success("La base de données a été vidée avec succès.")
            else:
                st.error("Une erreur est survenue lors du vidage de la base de données.")
    else:
        st.warning("Veuillez cocher la case pour confirmer la suppression.")

# Configure Streamlit page avec un logo personnalisé
st.set_page_config(
    page_title='PlagDetect',
    layout="wide",
    page_icon="logo.png"  # Utilisation du fichier logo comme icône de l'application
)

# Sidebar Menu
menu = ["Accueil", "Vérifier les Similitudes", "Consulter les Documents", "À propos"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Accueil":
    # Ajouter le logo en haut de la page
    st.image("logo.png", width=150)  # Affichez le logo en haut de la page d'accueil
    st.title("🏠 Bienvenue dans PlagDetect")
    st.markdown("Sélectionnez une option dans le menu gauche pour commencer.")

elif choice == "Vérifier les Similitudes":
    st.title(':mag: PlagDetect - Vérification des Similitudes')
    st.write("Vérifiez les similitudes entre les fichiers téléchargés.")

    # File upload in the sidebar
    st.sidebar.title(":file_folder: Importer les fichiers à comparer")
    st.sidebar.write("Téléchargez des fichiers pivots et cibles pour vérifier les similitudes entre eux.")

    pivot_files = st.sidebar.file_uploader("Fichier(s) pivot(s) (.docx, .pdf, .txt)", type=["docx", "pdf", "txt"], accept_multiple_files=True, key="pivot")
    target_files = st.sidebar.file_uploader("Fichier(s) cible(s) (.docx, .pdf, .txt)", type=["docx", "pdf", "txt"], accept_multiple_files=True, key="target")

    # Traitement des fichiers téléchargés
    pivot_texts, pivot_filenames = [], []
    for pivot_file in pivot_files:
        if pivot_file:
            text = get_text_from_file(pivot_file)
            # Traduction en anglais
            text = asyncio.run(main(text))
            pivot_texts.append(text)
            pivot_filenames.append(pivot_file.name)
            insert_file(pivot_file.name, text)

    target_texts, target_filenames = [], []
    for target_file in target_files:
        if target_file:
            text = get_text_from_file(target_file)
            # Traduction en anglais
            text = asyncio.run(main(text))
            target_texts.append(text)
            target_filenames.append(target_file.name)
            insert_file(target_file.name, text)

    if st.button('Vérifier les similitudes entre les fichiers'):
        if not pivot_texts or not target_texts:
            st.error("Aucun fichier trouvé pour la recherche de similitudes.")
            st.stop()

        similarities = get_pivot_similarity(pivot_texts, target_texts, pivot_filenames, target_filenames)
        df = pd.DataFrame(similarities, columns=['Fichier Pivot', 'Fichier Cible', 'Similarité (%)'])
        df = df.sort_values(by=['Similarité (%)'], ascending=False)
        st.dataframe(df)

elif choice == "Consulter les Documents":
    st.title(":open_file_folder: Consulter les Documents Enregistrés")
    files = get_all_files()
    if files:
        df = pd.DataFrame(files, columns=["ID", "Nom du Fichier", "Contenu"])
        st.dataframe(df)

        selected_id = st.number_input("Entrez l'ID du fichier à gérer", min_value=1, step=1)

        if st.button("Afficher le Contenu"):
            selected_file = next((file for file in files if file[0] == selected_id), None)
            if selected_file:
                st.subheader(f"Contenu du fichier : {selected_file[1]}")
                st.text_area("Contenu", selected_file[2], height=300)
            else:
                st.error("Fichier introuvable.")

        if st.button("Supprimer le fichier"):
            delete_file(selected_id)
            st.success(f"Le fichier {selected_id} a été supprimé avec succès.")

        empty_database_button()

    else:
        st.info("Aucun fichier trouvé dans la base de données.")

elif choice == "À propos":
    st.title("📝 À propos")
    st.write("""
        **PlagDetect** est une application conçue pour détecter le plagiat entre différents documents en analysant leurs contenus et en identifiant les similarités.

        ### Fonctionnalités principales :
        - **Comparaison de deux ou plusieurs documents** : Évalue à quel point un document est "inspiré" d'un autre en donnant un pourcentage de similarité.
        - **Analyse de plusieurs documents** : Regroupe les documents par niveaux de similarité détectée.
        - **Interface utilisateur intuitive** : Une interface conviviale qui facilite le téléchargement et l'analyse de vos documents.
        - **Support multi-formats** : Prends en charge divers formats de fichiers (.docx, .pdf, et .txt.)
        - **Comparaison de documents dans différentes langues** : Capacité à comparer des documents rédigés dans différentes langues.

        ### Notre Équipe :
        **PlagDetect** est développé par une équipe d'Ingénieurs en Informatique et Systèmes d'Informations.

        **Merci d'avoir choisi PlagDetect !**
    """)

if __name__ == "__main__":
    create_tables()
