import os
from flask import Flask
from flask_login import LoginManager
from config import config
from models import db, Usuario

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


def criar_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
    )
    app.config.from_object(config[config_name])

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def carregar_usuario(usuario_id):
        return Usuario.query.get(int(usuario_id))

    from rotas import registrar_blueprints

    registrar_blueprints(app)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = criar_app()
    app.run(debug=True)
