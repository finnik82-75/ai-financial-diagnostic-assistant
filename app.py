import logging
import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import EmailField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length

from config import Config


app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)
os.makedirs(app.instance_path, exist_ok=True)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "admin_login"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)


class ContactForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField("Телефон", validators=[DataRequired(), Length(min=6, max=30)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    message = TextAreaField(
        "Комментарий",
        validators=[DataRequired(), Length(min=5, max=2000)],
    )


class AdminLoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=120)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=3, max=120)])


class AdminUser(UserMixin):
    def __init__(self, user_id: str):
        self.id = user_id


@login_manager.user_loader
def load_user(user_id):
    if user_id == app.config["ADMIN_USERNAME"]:
        return AdminUser(user_id)
    return None


@app.context_processor
def inject_year():
    return {"current_year": datetime.now().year}


@app.route("/", methods=["GET", "POST"])
def index():
    form = ContactForm()
    if form.validate_on_submit():
        contact_request = ContactRequest(
            name=form.name.data.strip(),
            phone=form.phone.data.strip(),
            email=form.email.data.strip().lower(),
            message=form.message.data.strip(),
        )
        db.session.add(contact_request)
        db.session.commit()
        logger.info("Новая заявка отправлена: id=%s, email=%s", contact_request.id, contact_request.email)
        return redirect(url_for("contact_success"))

    return render_template("index.html", form=form)


@app.route("/contact-success")
def contact_success():
    return render_template("contact_success.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        if (
            form.username.data == app.config["ADMIN_USERNAME"]
            and form.password.data == app.config["ADMIN_PASSWORD"]
        ):
            login_user(AdminUser(form.username.data))
            logger.info("Успешный вход в админ-панель: user=%s", form.username.data)
            return redirect(url_for("admin_dashboard"))
        flash("Неверный логин или пароль.", "danger")

    return render_template("admin/login.html", form=form)


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    requests_query = ContactRequest.query.order_by(ContactRequest.created_at.desc())
    requests_data = requests_query.all()

    stats = {
        "total": ContactRequest.query.count(),
        "new": ContactRequest.query.filter_by(is_read=False).count(),
        "read": ContactRequest.query.filter_by(is_read=True).count(),
    }
    return render_template("admin/dashboard.html", requests=requests_data, stats=stats)


@app.route("/admin/mark-read/<int:request_id>", methods=["POST"])
@login_required
def mark_read(request_id):
    contact_request = ContactRequest.query.get_or_404(request_id)
    if not contact_request.is_read:
        contact_request.is_read = True
        db.session.commit()
        logger.info("Заявка отмечена как прочитанная: id=%s", request_id)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/<int:request_id>", methods=["POST"])
@login_required
def delete_request(request_id):
    contact_request = ContactRequest.query.get_or_404(request_id)
    db.session.delete(contact_request)
    db.session.commit()
    logger.info("Заявка удалена: id=%s", request_id)
    return redirect(url_for("admin_dashboard"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    logger.info("Приложение запущено на http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)