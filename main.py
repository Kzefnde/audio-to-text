import os
from typing import Tuple
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify
import whisper

app = Flask(__name__)

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

@app.route("/transcribe-stream", methods=["POST"])
def transcribe_stream():
    """Endpoint для преобразования речи в текст"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Сохраняем временный файл
    temp_path = os.path.join('static/temp', secure_filename(file.filename))
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    file.save(temp_path)
    
    try:
        # Распознаем речь
        result = model.transcribe(
            temp_path,
            language='ru',
            fp16=False
        )
        
        # Разбиваем на сегменты
        text_segments = []
        for segment in result['segments']:
            if segment.get('text'):
                text_segments.append(segment['text'].strip())
        
        full_text = ' '.join(text_segments)
        
        # Сохраняем в MD
        md_path = save_markdown(full_text)
        
        return jsonify({
            'text': full_text,
            'segments': text_segments,
            'md_file': md_path
        })
        
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return jsonify({'error': 'Failed to transcribe audio'}), 500
    
    finally:
        # Очищаем временный файл
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Error removing temp file: {str(e)}")

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

if __name__ == '__main__':
    app.run(debug=True)
