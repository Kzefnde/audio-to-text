from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message="Это поле обязательно"),
        Length(min=4, max=80, message="Имя должно быть от 4 до 80 символов")
    ])
    email = EmailField('Email', validators=[
        DataRequired(message="Это поле обязательно"),
        Email(message="Введите корректный email")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Это поле обязательно"),
        Length(min=6, message="Пароль должен быть не менее 6 символов")
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message="Это поле обязательно"),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message="Это поле обязательно"),
        Email(message="Введите корректный email")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Это поле обязательно")
    ])
    submit = SubmitField('Войти') 