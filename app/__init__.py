from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
import os
import phonenumbers
import logging

load_dotenv()

FLASK_SESSION_KEY = os.getenv("FLASK_SESSION_KEY")
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_NUMBER = os.getenv("TELNYX_NUMBER")
REDIS_URL = os.getenv("REDIS_URL")
MESSAGE = os.getenv("MESSAGE")

db = SQLAlchemy()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    number = db.Column(db.String(20))

class ContactAdmin(ModelView):
    def on_model_change(self, form, model, is_created):
        try:
            parsed = phonenumbers.parse(model.number, "US")
            model.number = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = FLASK_SESSION_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'

    logging.basicConfig(level=logging.DEBUG)

    # Allow both /admin and /admin/ without redirect
    app.url_map.strict_slashes = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Flask-Admin setup
    admin = Admin(app, name='Solutions GA')
    admin.add_view(ContactAdmin(Contact, db.session))

    # Register Blueprint for routes
    from .routes import bp
    app.register_blueprint(bp)

    return app