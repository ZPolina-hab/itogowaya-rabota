from flask import Flask, render_template, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agency.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_name = db.Column(db.String(200), nullable=False)
    seats = db.Column(db.String(100), nullable=False)
    card_last4 = db.Column(db.String(4), nullable=True)
    amount = db.Column(db.Float, default=1500.0)
    status = db.Column(db.String(20), default='paid')
    ticket_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(), EqualTo('password', message='Пароли не совпадают')
    ])
    submit = SubmitField('Создать аккаунт')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Этот email уже зарегистрирован')


class PaymentForm(FlaskForm):
    card_number = StringField('Номер карты', validators=[DataRequired(), Length(min=16, max=19)])
    expiry = StringField('Срок действия (MM/YY)', validators=[DataRequired()])
    cvv = StringField('CVV', validators=[DataRequired(), Length(min=3, max=3)])
    seats = HiddenField()
    submit = SubmitField('Оплатить и получить билет')


@app.route('/')
def index():
    return render_template('glawn.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация успешна! Теперь войдите в аккаунт.', 'success')
        return redirect(url_for('login'))
    return render_template('registr.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.name or user.email
            session['user_email'] = user.email
            flash('Вы успешно вошли в аккаунт!', 'success')
            return redirect(url_for('index'))
        flash('Неверный email или пароль', 'error')
    return render_template('vhod.html', form=form)


@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        flash('Для покупки билета необходимо авторизоваться', 'warning')
        return redirect(url_for('login'))

    form = PaymentForm()
    if form.validate_on_submit():
        selected_seats = form.seats.data
        if not selected_seats:
            flash('Пожалуйста, выберите хотя бы одно место', 'error')
            return render_template('book.html', form=form)

        booking = Booking(
            user_id=session['user_id'],
            event_name='Показ "BLOOM"',
            seats=selected_seats,
            card_last4=form.card_number.data[-4:],
            amount=1500.0,
            status='paid'
        )
        db.session.add(booking)
        db.session.commit()

        booking.ticket_sent = True
        db.session.commit()

        flash(
            f'Оплата прошла успешно! Списано с карты ****{booking.card_last4}. '
            f'Электронный билет отправлен на {session.get("user_email")}',
            'success'
        )
        return redirect(url_for('index'))

    return render_template('book.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из аккаунта', 'info')
    return redirect(url_for('index'))


@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()
    print('База данных agency.db успешно создана!')


if __name__ == '__main__':
    app.run(debug=True)