from rotas.auth import auth_bp
from rotas.alunos import alunos_bp
from rotas.planos import planos_bp
from rotas.matriculas import matriculas_bp
from rotas.mensalidades import mensalidades_bp
from rotas.relatorios import relatorios_bp


def registrar_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(alunos_bp, url_prefix="/alunos")
    app.register_blueprint(planos_bp, url_prefix="/planos")
    app.register_blueprint(matriculas_bp, url_prefix="/matriculas")
    app.register_blueprint(mensalidades_bp, url_prefix="/mensalidades")
    app.register_blueprint(relatorios_bp, url_prefix="/relatorios")
