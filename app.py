#app.py
import streamlit as st
import pandas as pd
import nltk
nltk.download('punkt')
from sklearn.metrics.pairwise import cosine_similarity
import os
from googletrans import Translator

# Configure NLTK data path
os.environ['NLTK_DATA'] = '/tmp/nltk_data'

# Import database-related functions
from main import (
    clear_database, create_tables, delete_file, get_all_files, 
    get_pivot_similarity, get_sentences, get_similarity, 
    get_text_from_file, insert_file, translate_text
)

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
            text = translate_text(text, target_lang='en')
            pivot_texts.append(text)
            pivot_filenames.append(pivot_file.name)
            insert_file(pivot_file.name, text)

    target_texts, target_filenames = [], []
    for target_file in target_files:
        if target_file:
            text = get_text_from_file(target_file)
            # Traduction en anglais
            text = translate_text(text, target_lang='en')
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
