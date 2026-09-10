import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from models import Aluno, Mensalidade, Matricula, Usuario, Pagamento

auth_bp = Blueprint("auth", __name__)


def _obter_sparkline(model, date_field, days=30):
    """Gera dados para sparkline dos últimos N dias."""
    hoje = date.today()
    dados = []
    for i in range(days - 1, -1, -1):
        data_ref = hoje - timedelta(days=i)
        count = model.query.filter(
            func.date(getattr(model, date_field)) == data_ref
        ).count()
        dados.append(count)
    return dados


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        login = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(login=login).first()

        if usuario and usuario.verificar_senha(senha):
            login_user(usuario)
            proximo = request.args.get("next")
            flash("Login realizado com sucesso!", "success")
            return redirect(proximo or url_for("auth.dashboard"))

        flash("Login ou senha incorretos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout realizado.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/")
@login_required
def dashboard():
    total_alunos = Aluno.query.filter_by(ativo=True).count()
    matriculas_ativas = Matricula.query.filter_by(ativa=True).count()
    mensalidades_pendentes = Mensalidade.query.filter_by(paga=False).filter(
        Mensalidade.data_vencimento >= date.today()
    ).count()
    mensalidades_atrasadas = Mensalidade.query.filter_by(paga=False).filter(
        Mensalidade.data_vencimento < date.today()
    ).count()

    # Alunos com vencimento em ate 7 dias (avisos)
    data_limite = date.today() + timedelta(days=7)
    vencem_7dias = (
        Mensalidade.query.filter_by(paga=False)
        .filter(
            Mensalidade.data_vencimento >= date.today(),
            Mensalidade.data_vencimento <= data_limite,
        )
        .all()
    )
    
    # Sparklines (últimos 30 dias)
    sparkline_alunos = _obter_sparkline(Aluno, 'data_cadastro', 30)
    sparkline_matriculas = _obter_sparkline(Matricula, 'data_inicio', 30)
    sparkline_pendentes = _obter_sparkline(Mensalidade, 'data_vencimento', 30)
    sparkline_atrasadas = _obter_sparkline(Mensalidade, 'data_vencimento', 30)

    return render_template(
        "dashboard.html",
        total_alunos=total_alunos,
        matriculas_ativas=matriculas_ativas,
        mensalidades_pendentes=mensalidades_pendentes,
        mensalidades_atrasadas=mensalidades_atrasadas,
        vencem_7dias=vencem_7dias,
        sparkline_alunos=sparkline_alunos,
        sparkline_matriculas=sparkline_matriculas,
        sparkline_pendentes=sparkline_pendentes,
        sparkline_atrasadas=sparkline_atrasadas,
    )
