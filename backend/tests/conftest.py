"""Fixtures compartilhadas para os testes."""

import os
import sys
import tempfile

import pytest

# Configurar o DB de teste ANTES de importar o app (config.py le a env var)
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".sqlite")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH

TEST_DIR = os.path.dirname(__file__)
sys.path.insert(0, TEST_DIR)
sys.path.insert(0, os.path.join(TEST_DIR, ".."))

from app import criar_app
from models import db, Usuario, Plano, Aluno, Matricula, Mensalidade, Pagamento


@pytest.fixture()
def app():
    app = criar_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "teste-secreto"

    with app.app_context():
        _criar_dados_base()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def pytest_sessionfinish(session, exitstatus):
    try:
        os.close(_TEST_DB_FD)
        os.unlink(_TEST_DB_PATH)
    except OSError:
        pass


def _criar_dados_base():
    admin = Usuario(nome="Administrador", login="admin", admin=True)
    admin.definir_senha("admin123")
    db.session.add(admin)

    plans = [
        Plano(nome="Mensal", valor=65.00, duracao_meses=1, descricao="Mensal"),
        Plano(nome="Trimestral", valor=175.50, duracao_meses=3, descricao="Trimestral"),
        Plano(nome="Semestral", valor=331.50, duracao_meses=6, descricao="Semestral"),
        Plano(nome="Anual", valor=624.00, duracao_meses=12, descricao="Anual"),
    ]
    db.session.add_all(plans)
    db.session.commit()


def _criar_dados_base():
    admin = Usuario(nome="Administrador", login="admin", admin=True)
    admin.definir_senha("admin123")
    db.session.add(admin)

    plans = [
        Plano(nome="Mensal", valor=65.00, duracao_meses=1, descricao="Mensal"),
        Plano(nome="Trimestral", valor=175.50, duracao_meses=3, descricao="Trimestral"),
        Plano(nome="Semestral", valor=331.50, duracao_meses=6, descricao="Semestral"),
        Plano(nome="Anual", valor=624.00, duracao_meses=12, descricao="Anual"),
    ]
    db.session.add_all(plans)
    db.session.commit()


@pytest.fixture()
def cliente(app):
    return app.test_client()


@pytest.fixture()
def aluno_logado(cliente):
    """Faz login e retorna o objeto Aluno de teste."""
    cliente.post("/login", data={"login": "admin", "senha": "admin123"})
    return cliente


@pytest.fixture()
def plano_mensal(app):
    with app.app_context():
        return Plano.query.filter_by(nome="Mensal").first()


@pytest.fixture()
def plano_trimestral(app):
    with app.app_context():
        return Plano.query.filter_by(nome="Trimestral").first()