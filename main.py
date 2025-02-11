import os
from typing import Tuple, List
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from utils.text_processor import TextProcessor
import whisper
import time
from models import db, User, Lecture
from forms import RegisterForm, LoginForm
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

# Конфигурация приложения
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Замените на реальный секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'temp')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24)  # Для форм
app.config['TRANSCRIPTS_FOLDER'] = os.path.join(app.static_folder, 'transcripts')

# Создаем необходимые директории
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'transcripts'), exist_ok=True)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация других компонентов
text_processor = TextProcessor()
model = whisper.load_model("medium")

csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Главная страница - редирект на логин если не авторизован
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Проверяем, существует ли пользователь
        if User.query.filter_by(email=form.email.data).first():
            flash('Этот email уже зарегистрирован')
            return redirect(url_for('register'))
        
        # Создаем нового пользователя
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна! Теперь вы можете войти.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации. Попробуйте позже.')
            print(f"Error during registration: {e}")
            
    return render_template('register.html', form=form)

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        flash('Неверный email или пароль')
    
    return render_template('login.html', form=form)

# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Главная страница после входа
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Страница с лекциями
@app.route('/lectures')
@login_required
def lectures():
    user_lectures = Lecture.query.filter_by(user_id=current_user.id).order_by(Lecture.created_at.desc()).all()
    return render_template('lectures.html', lectures=user_lectures)

# Страница создания новой лекции
@app.route('/new-lecture')
@login_required
def new_lecture():
    return render_template('speech_to_text.html')

@app.route("/transcribe-stream", methods=['POST'])
@login_required
def transcribe_stream():
    print("=== Начало обработки запроса ===")
    print("Content-Type:", request.content_type)
    print("Files:", list(request.files.keys()) if request.files else "No files")
    
    try:
        if 'file' not in request.files:
            print("Файл не найден в запросе")
            response = jsonify({'error': 'Файл не найден в запросе'})
            response.headers['Content-Type'] = 'application/json'
            return response, 400
            
        file = request.files['file']
        print(f"Получен файл: {file.filename}, mimetype: {file.content_type}")
        
        if file.filename == '':
            print("Пустое имя файла")
            response = jsonify({'error': 'Файл не выбран'})
            response.headers['Content-Type'] = 'application/json'
            return response, 400
        
        # Проверяем расширение файла
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            print(f"Неподдерживаемое расширение: {file_ext}")
            response = jsonify({'error': f'Неподдерживаемый формат файла. Разрешены: {", ".join(allowed_extensions)}'})
            response.headers['Content-Type'] = 'application/json'
            return response, 400
        
        # Сохраняем файл
        filename = secure_filename(file.filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"Сохранение файла в: {audio_path}")
        file.save(audio_path)
        
        if not os.path.exists(audio_path):
            print("Файл не был сохранен")
            response = jsonify({'error': 'Ошибка сохранения файла'})
            response.headers['Content-Type'] = 'application/json'
            return response, 500
            
        print(f"Размер файла: {os.path.getsize(audio_path)} байт")
        
        try:
            # Транскрибация
            print("Начало транскрибации...")
            result = model.transcribe(audio_path, language='ru')
            
            if not result or not result.get("text"):
                print("Не удалось получить текст из аудио")
                response = jsonify({'error': 'Не удалось распознать текст'})
                response.headers['Content-Type'] = 'application/json'
                return response, 500
            
            print("Транскрибация успешна")
            
            # Форматируем текст и извлекаем термины
            formatted_text = text_processor.format_transcript(result["text"])
            terms = text_processor.extract_terms(result["text"])
            
            # Сохраняем результат
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            md_filename = f"transcript_{timestamp}.md"
            md_path = os.path.join('static', 'transcripts', md_filename)
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            
            # Создаем запись в БД
            lecture = Lecture(
                filename=md_filename,
                title=f"Лекция от {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                content=formatted_text,
                user_id=current_user.id
            )
            db.session.add(lecture)
            db.session.commit()
            
            response_data = {
                'segments': [result["text"]],
                'md_file': f'/static/transcripts/{md_filename}',
                'terms': terms
            }
            print("Отправка ответа:", response_data)
            response = jsonify(response_data)
            response.headers['Content-Type'] = 'application/json'
            return response
            
        except Exception as e:
            print(f"Ошибка при транскрибации: {str(e)}")
            response = jsonify({'error': f'Ошибка при распознавании аудио: {str(e)}'})
            response.headers['Content-Type'] = 'application/json'
            return response, 500
            
    except Exception as e:
        print(f"Общая ошибка обработки: {str(e)}")
        response = jsonify({'error': f'Ошибка при обработке файла: {str(e)}'})
        response.headers['Content-Type'] = 'application/json'
        return response, 500
        
    finally:
        # Удаляем временный файл
        if 'audio_path' in locals() and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Временный файл удален: {audio_path}")
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {str(e)}")

@app.route("/lecture/<int:lecture_id>")
@login_required
def view_lecture(lecture_id):
    lecture = Lecture.query.get_or_404(lecture_id)
    if lecture.user_id != current_user.id:
        flash('У вас нет доступа к этой лекции')
        return redirect(url_for('lectures'))
    return render_template("lecture.html", content=lecture.content, lecture_id=lecture_id)

@app.route("/edit/<int:lecture_id>", methods=['GET', 'POST'])
@login_required
def edit_lecture(lecture_id):
    lecture = Lecture.query.get_or_404(lecture_id)
    if lecture.user_id != current_user.id:
        flash('У вас нет доступа к этой лекции')
        return redirect(url_for('lectures'))
    
    if request.method == 'POST':
        lecture.content = request.form['content']
        db.session.commit()
        return redirect(url_for('view_lecture', lecture_id=lecture_id))
    
    return render_template("edit_lecture.html", content=lecture.content, lecture_id=lecture_id)

@app.route('/delete_lecture/<int:lecture_id>', methods=['DELETE'])
@login_required
def delete_lecture(lecture_id):
    try:
        # Получаем лекцию
        lecture = Lecture.query.filter_by(id=lecture_id, user_id=current_user.id).first()
        
        if not lecture:
            return jsonify({'error': 'Лекция не найдена'}), 404
            
        # Удаляем файл конспекта, если он существует
        if lecture.filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], lecture.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Удаляем запись из базы данных
        db.session.delete(lecture)
        db.session.commit()
        
        return jsonify({'message': 'Лекция успешно удалена'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route("/delete_all_lectures", methods=['POST'])
@login_required
def delete_all_lectures():
    try:
        # Получаем все лекции пользователя
        user_lectures = Lecture.query.filter_by(user_id=current_user.id).all()
        
        # Удаляем файлы лекций
        for lecture in user_lectures:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], lecture.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Удаляем записи из базы данных
        Lecture.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        flash('Все лекции успешно удалены')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при удалении лекций')
        print(f"Error deleting lectures: {e}")
    
    return redirect(url_for('lectures'))

# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
