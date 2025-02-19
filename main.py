from create_app import create_app
from config import Config
from models import db
from routes import register_routes

app = create_app(Config)
register_routes(app)

# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False)  # Отключаем debug режим для продакшена
