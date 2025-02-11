from transformers import pipeline
import whisper
import os
from werkzeug.utils import secure_filename
from flask import request, jsonify, url_for
from datetime import datetime
import openai
import re

# Загружаем модели
model = whisper.load_model("medium")
nlp = pipeline("text-classification", model="ProsusAI/finbert")

@app.route('/transcribe-stream', methods=['POST'])
def transcribe_stream():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
        
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Файл не выбран'}), 400

    # Проверяем расширение файла
    allowed_extensions = {'.wav', '.mp3', '.ogg', '.m4a'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Неподдерживаемый формат файла. Разрешены: .wav, .ogg, .m4a, .mp3'}), 400

    try:
        # Сохраняем временный файл
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)

        # Транскрибируем аудио используя Whisper medium
        result = model.transcribe(temp_path, language='ru')
        
        # Извлекаем текст и сегменты
        text = result['text']
        segments = [segment['text'] for segment in result['segments']]

        # Извлекаем термины и определения
        terms = extract_terms_and_definitions(text)
        
        # Создаем MD файл
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'lecture_{timestamp}.md'
        md_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], filename)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('# Конспект лекции\n\n')
            f.write(text + '\n\n')
            
            # Записываем термины
            if terms:
                f.write('\n## Глоссарий\n\n')
                current_letter = ''
                for term, definition in terms:
                    if term[0].upper() != current_letter:
                        current_letter = term[0].upper()
                        f.write(f'\n### {current_letter}\n\n')
                    f.write(f'**{term}**\n: {definition}\n\n')
            
            # Записываем математические формулы
            if result['math']:
                f.write('\n## Математические формулы\n\n')
                for _, formula, description in result['math']:
                    f.write(f'$${formula}$$\n\n')
                    f.write(f'*{description}*\n\n')
            
            # Записываем цитаты
            if result['quotes']:
                f.write('\n## Цитаты\n\n')
                for _, person, quote in result['quotes']:
                    f.write(f'> {quote}\n\n')
                    f.write(f'*— {person}*\n\n')

        # Очищаем временный файл
        os.remove(temp_path)

        return jsonify({
            'segments': segments,
            'terms': terms,
            'md_file': url_for('static', filename=f'transcripts/{filename}')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_terms_and_definitions(text):
    try:
        # Ищем определения с помощью расширенных паттернов
        patterns = [
            # Термины в кавычках с определениями
            r'[«"](?P<term>[^»"]+)[»"]\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
            r'[«"](?P<term>[^»"]+)[»"]\s*—\s*это\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Термины с определениями через тире
            r'(?P<term>\b[A-Za-zА-Яа-я][a-zа-яА-ЯA-Z\s-]+\b)\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
            r'(?P<term>\b[A-Za-zА-Яа-я][a-zа-яА-ЯA-Z\s-]+\b)\s*—\s*это\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Термины с определениями в скобках
            r'(?P<term>\b[A-Za-zА-Яа-я][a-zа-яА-ЯA-Z\s-]+\b)\s*\((?P<definition>[^)]+)\)',
            
            # Технические термины на английском
            r'\b(?P<term>[A-Z][A-Za-z\s-]+)\b\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
            r'\b(?P<term>[A-Z][A-Za-z\s-]+)\b\s*—\s*это\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Многословные термины
            r'термин\s*[«"](?P<term>[^»"]+)[»"]\s*(?:означает|определяется как|это)\s*(?P<definition>[^.!?\n]+[.!?])',
            r'понятие\s*[«"](?P<term>[^»"]+)[»"]\s*(?:означает|определяется как|это)\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Определение через называется/является
            r'(?P<definition>[^.!?\n]+)\s*называется\s*[«"](?P<term>[^»"]+)[»"][.!?]',
            r'(?P<term>\b[A-Za-zА-Яа-я][a-zа-яА-ЯA-Z\s-]+\b)\s*является\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Математические термины и формулы
            r'(?P<term>(?:формула|уравнение|закон|теорема)\s+[А-ЯA-Z][а-яa-z\s-]*)\s*[-—:]\s*(?P<definition>[^.!?\n]+[.!?])',
            r'(?P<term>[А-ЯA-Z][а-яa-z\s-]*(?:формула|уравнение|закон|теорема))\s*[-—:]\s*(?P<definition>[^.!?\n]+[.!?])',
            r'(?P<term>\$[^$]+\$)\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
            
            # Цитаты известных ученых
            r'(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)\s+(?:говорил|сказал|утверждал|писал)[,:]\s*[«"](?P<quote>[^»"]+)[»"]',
            r'[«"](?P<quote>[^»"]+)[»"]\s*[-—]\s*(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)',
            r'(?:Как\s+(?:говорил|сказал|утверждал|писал))\s+(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)[,:]\s*[«"](?P<quote>[^»"]+)[»"]'
        ]
        
        terms = []
        seen_terms = set()
        
        # Ищем определения по паттернам
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                term = match.group('term').strip()
                definition = match.group('definition').strip()
                
                # Проверяем и очищаем термин
                term = clean_term(term)
                if is_valid_term(term) and term.lower() not in seen_terms:
                    terms.append((term, definition))
                    seen_terms.add(term.lower())
        
        # Дополнительный поиск технических терминов
        tech_terms = find_technical_terms(text)
        for term, definition in tech_terms:
            if term.lower() not in seen_terms:
                terms.append((term, definition))
                seen_terms.add(term.lower())
        
        # Добавляем поиск математических выражений и цитат
        math_formulas = find_math_formulas(text)
        quotes = find_quotes(text)
        
        # Объединяем все найденные термины
        all_items = {
            'terms': terms,
            'math': math_formulas,
            'quotes': quotes
        }
        
        return format_content(all_items)
        
    except Exception as e:
        print(f"Ошибка при извлечении терминов: {e}")
        return {'terms': [], 'math': [], 'quotes': []}

def clean_term(term):
    """Очищает и форматирует термин"""
    # Удаляем лишние пробелы и знаки препинания
    term = term.strip('.,;: \'"«»')
    # Приводим первую букву к верхнему регистру
    if term and term[0].isalpha():
        term = term[0].upper() + term[1:]
    return term

def is_valid_term(term):
    """Проверяет валидность термина"""
    if not term or len(term) < 2:
        return False
    # Проверяем, что термин не содержит только цифры
    if term.replace(' ', '').isdigit():
        return False
    # Проверяем минимальную длину слов в многословном термине
    words = term.split()
    return all(len(word) > 1 for word in words)

def find_technical_terms(text):
    """Ищет технические термины и их определения"""
    tech_patterns = [
        # Паттерны для поиска технических терминов
        r'\b(?P<term>[A-Z][A-Za-z0-9]+(?:\s*[A-Z][A-Za-z0-9]+)*)\b\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
        r'\b(?P<term>[A-Z][A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*)\b\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])',
        # Аббревиатуры с расшифровкой
        r'\b(?P<term>[A-Z]{2,})\s*\((?P<definition>[^)]+)\)',
        # Технические термины в кавычках
        r'[«"](?P<term>[A-Za-z][\w\s-]+)[»"]\s*[-—]\s*(?P<definition>[^.!?\n]+[.!?])'
    ]
    
    terms = []
    for pattern in tech_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            term = match.group('term').strip()
            definition = match.group('definition').strip()
            if is_valid_term(term):
                terms.append((term, definition))
    return terms

def find_math_formulas(text):
    """Ищет математические формулы и их описания"""
    math_patterns = [
        # Формулы в LaTeX-подобном формате
        r'\$(?P<formula>[^$]+)\$\s*[-—]\s*(?P<description>[^.!?\n]+[.!?])',
        # Формулы с описанием
        r'формула\s*[:：]\s*(?P<formula>[^.!?\n]+)\s*[-—]\s*(?P<description>[^.!?\n]+[.!?])',
        # Уравнения
        r'уравнение\s*[:：]\s*(?P<formula>[^.!?\n]+)\s*[-—]\s*(?P<description>[^.!?\n]+[.!?])',
    ]
    
    formulas = []
    for pattern in math_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            formula = match.group('formula').strip()
            description = match.group('description').strip()
            formulas.append(('Формула', formula, description))
    return formulas

def find_quotes(text):
    """Ищет цитаты известных ученых"""
    quote_patterns = [
        r'(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)\s+(?:говорил|сказал|утверждал|писал)[,:]\s*[«"](?P<quote>[^»"]+)[»"]',
        r'[«"](?P<quote>[^»"]+)[»"]\s*[-—]\s*(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)',
        r'(?:Как\s+(?:говорил|сказал|утверждал|писал))\s+(?P<person>[А-ЯA-Z][а-яa-zА-ЯA-Z\s-]+)[,:]\s*[«"](?P<quote>[^»"]+)[»"]'
    ]
    
    quotes = []
    for pattern in quote_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            person = match.group('person').strip()
            quote = match.group('quote').strip()
            quotes.append(('Цитата', person, quote))
    return quotes

def format_content(content):
    """Форматирует весь контент для MD файла"""
    result = {
        'terms': format_terms(content['terms']),
        'math': content['math'],
        'quotes': content['quotes']
    }
    return result

def format_terms(terms):
    """Форматирует и сортирует термины"""
    # Сортируем термины по алфавиту
    terms = sorted(terms, key=lambda x: x[0].lower())
    
    # Группируем термины по первой букве
    grouped_terms = {}
    for term, definition in terms:
        first_letter = term[0].upper()
        if first_letter not in grouped_terms:
            grouped_terms[first_letter] = []
        grouped_terms[first_letter].append((term, definition))
    
    # Форматируем результат
    formatted_terms = []
    for letter in sorted(grouped_terms.keys()):
        for term, definition in grouped_terms[letter]:
            formatted_terms.append((term, definition))
    
    return formatted_terms 