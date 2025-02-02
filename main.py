import os
from typing import Tuple, List
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, redirect, url_for
import whisper

app = Flask(__name__)

# Добавляем конфигурацию для загрузки файлов
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'temp')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

model = whisper.load_model("medium")

def save_files() -> str:
    """
    Функция save_files() используется для сохранения аудиофайлов.
    :return: Возвращает путь к сохраненному аудиофайлу.
    """
    path = os.path.join('static/temp')
    os.makedirs(path, exist_ok=True)
    
    files_name = os.listdir(path)
    num = len(files_name)
    new_name = f'audio_{num}.mp3'
    
    return os.path.join(path, new_name)

def get_file(file) -> Tuple[str, str]:
    """
    Функция принимает загруженный файл и выполняет преобразование в текст.
    :param file: Загруженный файл для преобразования в текст.
    :return: Кортеж с текстом и путем к файлу.
    """
    if file.filename == '':
        return 'Файл не выбран', ''

    file_path = save_files()
    file.save(file_path)

    result = model.transcribe(file_path)
    text = result["text"]

    return text, file_path

@app.route("/", methods=["GET"])
def index():
    """Главная страница"""
    return render_template("speech_to_text.html")

@app.route("/transcribe-stream", methods=['POST'])
def transcribe_stream():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        # Создаем имя файла с текущей датой и временем
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"transcript_{timestamp}.md"
        
        # Сохраняем аудиофайл временно
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(audio_path)
        
        try:
            # Транскрибация
            result = model.transcribe(audio_path, language='ru')
            
            # Сохраняем результат в MD файл
            md_path = os.path.join('static', 'transcripts', filename)
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Транскрипция от {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
                f.write(result["text"])
            
            # Удаляем временный аудиофайл
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return jsonify({
                'segments': [result["text"]],
                'md_file': f'/static/transcripts/{filename}'
            })
            
        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            return jsonify({'error': str(e)}), 500

def save_markdown(text: str) -> str:
    """Сохраняет текст в формате Markdown"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{timestamp}.md"
    path = os.path.join('static', 'transcripts', filename)
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# Транскрипция {timestamp}\n\n")
        f.write(text)
    
    return f"/static/transcripts/{filename}"

@app.route("/lectures")
def lectures():
    """Страница со списком лекций"""
    lectures_list = get_lectures()
    return render_template("lectures.html", lectures=lectures_list)

@app.route("/lecture/<lecture_id>")
def view_lecture(lecture_id):
    """Просмотр отдельной лекции"""
    lectures_dir = os.path.join('static', 'transcripts')
    filepath = os.path.join(lectures_dir, f"{lecture_id}.md")
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template("lecture.html", content=content, lecture_id=lecture_id)
    
    return redirect(url_for('lectures'))

@app.route("/lecture/<lecture_id>/edit", methods=['GET', 'POST'])
def edit_lecture(lecture_id):
    """Редактирование лекции"""
    if request.method == 'POST':
        content = request.form.get('content')
        lectures_dir = os.path.join('static', 'transcripts')
        filepath = os.path.join(lectures_dir, f"{lecture_id}.md")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return redirect(url_for('view_lecture', lecture_id=lecture_id))
    
    lectures_dir = os.path.join('static', 'transcripts')
    filepath = os.path.join(lectures_dir, f"{lecture_id}.md")
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template("edit_lecture.html", content=content, lecture_id=lecture_id)
    
    return redirect(url_for('lectures'))

@app.route("/lecture/<lecture_id>/delete", methods=['POST'])
def delete_lecture(lecture_id):
    """Удаление отдельной лекции"""
    lectures_dir = os.path.join('static', 'transcripts')
    filepath = os.path.join(lectures_dir, f"{lecture_id}.md")
    
    if os.path.exists(filepath):
        os.remove(filepath)
    
    return redirect(url_for('lectures'))

@app.route("/lectures/delete-all", methods=['POST'])
def delete_all_lectures():
    """Удаление всех лекций"""
    lectures_dir = os.path.join('static', 'transcripts')
    
    if os.path.exists(lectures_dir):
        for filename in os.listdir(lectures_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(lectures_dir, filename)
                os.remove(filepath)
    
    return redirect(url_for('lectures'))

def get_lectures() -> List[dict]:
    """Получает список всех сохраненных лекций"""
    lectures_dir = os.path.join('static', 'transcripts')
    lectures = []
    
    if os.path.exists(lectures_dir):
        for filename in os.listdir(lectures_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(lectures_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        # Получаем дату из имени файла (формат: transcript_YYYYMMDDHHMMSS.md)
                        date_str = filename.split('_')[1].split('.')[0]
                        date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        
                        lectures.append({
                            'id': filename.split('.')[0],
                            'date': date.strftime('%d.%m.%Y %H:%M'),
                            'filename': filename,
                            'content': content,
                            'path': f'/static/transcripts/{filename}'
                        })
                    except (IndexError, ValueError):
                        # Если не удалось распарсить дату, используем текущую
                        date = datetime.now()
                        lectures.append({
                            'id': filename.split('.')[0],
                            'date': date.strftime('%d.%m.%Y %H:%M'),
                            'filename': filename,
                            'content': content,
                            'path': f'/static/transcripts/{filename}'
                        })
    
    return sorted(lectures, key=lambda x: x['date'], reverse=True)

if __name__ == '__main__':
    app.run(debug=True)
