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
    # Utilisation de asyncio.to_thread pour effectuer la traduction dans un thread séparé
    translated = await asyncio.to_thread(translator.translate, text, dest=target_lang)
    return translated.text

# Fonction principale qui gère l'appel de la traduction
async def main(text):
    translated_text = await translate_text(text, target_lang='en')
    return translated_text



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
