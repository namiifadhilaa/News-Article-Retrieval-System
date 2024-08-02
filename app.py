from flask import Flask, request, render_template, redirect, url_for, send_file
import os
import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string
import json
from datetime import datetime
import math

# Menginisialisasi Flask App
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CORPUS_FOLDER'] = 'corpus'
app.config['CORPUS_DATA'] = 'corpus.json'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['STOPWORDS_FOLDER'] = 'stopwords'

# Membuat direktori
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CORPUS_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
os.makedirs(app.config['STOPWORDS_FOLDER'], exist_ok=True)

# Menginisialisasi Stemmer Sastrawi
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# Mendefinisikan Stopwords
stop_words = set(stopwords.words('indonesian'))

# Dictionary Normalisasi
normalization_dict = {
    'ga': 'tidak',
    'gak': 'tidak',
    'nggak': 'tidak',
    'kamu': 'anda',
    'aku': 'saya',
    'tapi': 'tetapi',
    'dgn': 'dengan',
    'dg': 'dengan'
}

def normalize_text(text, normalization_dict):
    words = text.split()
    normalized_words = [normalization_dict.get(word, word) for word in words]
    return ' '.join(normalized_words)

def preprocess_text(text):
    # Mengubah ke bentuk lowercase
    text = text.lower()
    # Mengnormalisasi teks
    text = normalize_text(text, normalization_dict)
    # Menghilangkan tanda baca
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Tokenisasi
    tokens = word_tokenize(text)
    # Menghilangkan stopwords
    tokens = [word for word in tokens if word.isalpha() and word not in stop_words]
    # Mengaplikasikan stemmer
    tokens = [stemmer.stem(word) for word in tokens]
    # Menggabungkan token kembali ke dalam satu string
    preprocessed_text = ' '.join(tokens)
    return preprocessed_text, tokens

def extract_stopwords(text):
    tokens = word_tokenize(text)
    stopword_tokens = [word for word in tokens if word in stop_words]
    return stopword_tokens

def update_corpus(filename, original_content, preprocessed_content):
    if not os.path.exists(app.config['CORPUS_DATA']):
        corpus = []
    else:
        with open(app.config['CORPUS_DATA'], 'r', encoding='utf-8') as f:
            try:
                corpus = json.load(f)
            except json.JSONDecodeError:
                corpus = []

    entry = {
        'filename': filename,
        'original_content': original_content,
        'preprocessed_content': preprocessed_content,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    corpus.append(entry)

    with open(app.config['CORPUS_DATA'], 'w', encoding='utf-8') as f:
        json.dump(corpus, f, ensure_ascii=False, indent=4)

def create_inverted_index(corpus):
    inverted_index = {}
    for i, doc in enumerate(corpus):
        terms = doc['preprocessed_content'].split()
        for term in terms:
            if term not in inverted_index:
                inverted_index[term] = set()
            inverted_index[term].add(i)
    return inverted_index

def calculate_bim_score(query_terms, doc_index, inverted_index, corpus_size):
    # Assume binary weights for terms
    score = 0
    for term in query_terms:
        if term in inverted_index:
            df = len(inverted_index[term])
            idf = math.log((corpus_size - df + 0.5) / (df + 0.5))
            if doc_index in inverted_index[term]:
                score += idf
    return score


@app.route('/', methods=['GET', 'POST'])
def search_corpus():
    query = ''
    results = []
    if request.method == 'POST':
        query = request.form['query']
        preprocessed_query, _ = preprocess_text(query)
        query_terms = preprocessed_query.split()
        
        if os.path.exists(app.config['CORPUS_DATA']):
            with open(app.config['CORPUS_DATA'], 'r', encoding='utf-8') as f:
                try:
                    corpus_data = json.load(f)
                except json.JSONDecodeError:
                    corpus_data = []

            corpus_size = len(corpus_data)
            inverted_index = create_inverted_index(corpus_data)

            scores = []
            for i, doc in enumerate(corpus_data):
                # Only calculate score if document contains query terms
                if any(term in doc['preprocessed_content'].split() for term in query_terms):
                    score = calculate_bim_score(query_terms, i, inverted_index, corpus_size)
                    if score > 0:
                        scores.append((score, doc))

            # Sort by score in descending order
            scores.sort(reverse=True, key=lambda x: x[0])
            results = [doc for score, doc in scores]
    
    return render_template('search.html', query=query, results=results)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file and file.filename.endswith('.txt'):
            original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(original_file_path)
            
            with open(original_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            preprocessed_content, tokens = preprocess_text(original_content)
            stopword_tokens = extract_stopwords(original_content)
            
            preprocessed_file_path = os.path.join(app.config['CORPUS_FOLDER'], file.filename)
            with open(preprocessed_file_path, 'w', encoding='utf-8') as f:
                f.write(preprocessed_content)
            
            update_corpus(file.filename, original_content, preprocessed_content)

            processed_file_path = os.path.join(app.config['PROCESSED_FOLDER'], f'processed_{file.filename}')
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                word_counts = {word: tokens.count(word) for word in set(tokens)}
                for word, count in word_counts.items():
                    f.write(f'{word}: {count}\n')
            
            stopwords_file_path = os.path.join(app.config['STOPWORDS_FOLDER'], f'stopwords_{file.filename}')
            with open(stopwords_file_path, 'w', encoding='utf-8') as f:
                stopword_counts = {word: stopword_tokens.count(word) for word in set(stopword_tokens)}
                for word, count in stopword_counts.items():
                    f.write(f'{word}: {count}\n')

            return send_file(processed_file_path, as_attachment=True)
    return render_template('upload.html')

@app.route('/corpus')
def view_corpus():
    if not os.path.exists(app.config['CORPUS_DATA']):
        corpus_data = []
    else:
        with open(app.config['CORPUS_DATA'], 'r', encoding='utf-8') as f:
            try:
                corpus_data = json.load(f)
            except json.JSONDecodeError:
                corpus_data = []
    
    return render_template('corpus.html', corpus_data=corpus_data)

if __name__ == '__main__':
    app.run(debug=True)

