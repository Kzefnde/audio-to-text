from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Lecture
from forms import RegisterForm, LoginForm
from utils.text_processor import TextProcessor
import whisper
import os
from datetime import datetime

# Инициализация компонентов
text_processor = TextProcessor()
model = whisper.load_model("medium")

def register_routes(app):
    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data).first():
                flash('Этот email уже зарегистрирован')
                return redirect(url_for('register'))
            
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

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/lectures')
    @login_required
    def lectures():
        user_lectures = Lecture.query.filter_by(user_id=current_user.id).order_by(Lecture.created_at.desc()).all()
        return render_template('lectures.html', lectures=user_lectures)

    @app.route('/new-lecture')
    @login_required
    def new_lecture():
        return render_template('speech_to_text.html')

    @app.route("/transcribe-stream", methods=['POST'])
    @login_required
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
            return jsonify({'error': 'Неподдерживаемый формат файла'}), 400

        try:
            # Сохраняем временный файл
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)

            # Транскрибируем аудио
            result = model.transcribe(temp_path, language='ru')
            text = result['text']

            # Обрабатываем текст
            formatted_text = text_processor.format_transcript(text)
            terms = text_processor.extract_terms(text)

            # Сохраняем в MD файл
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            md_filename = f'lecture_{timestamp}.md'
            md_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], md_filename)
            
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

            return jsonify({
                'segments': [text],
                'terms': terms,
                'md_file': url_for('static', filename=f'transcripts/{md_filename}')
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)

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
            lecture = Lecture.query.filter_by(id=lecture_id, user_id=current_user.id).first()
            
            if not lecture:
                return jsonify({'error': 'Лекция не найдена'}), 404
                
            if lecture.filename:
                file_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], lecture.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
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
            lectures = Lecture.query.filter_by(user_id=current_user.id).all()
            
            for lecture in lectures:
                if lecture.filename:
                    file_path = os.path.join(app.config['TRANSCRIPTS_FOLDER'], lecture.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            Lecture.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            
            flash('Все лекции успешно удалены')
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при удалении лекций')
            print(f"Error deleting lectures: {e}")
        
        return redirect(url_for('lectures')) 