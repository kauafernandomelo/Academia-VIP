from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Usuario

auth_bp = Blueprint("auth", __name__)


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
    from datetime import date, timedelta
    from models import Aluno, Mensalidade, Matricula
    from regras import garantir_renovacoes

    # Garantir cobrancas de renovacao antes de mostrar os numeros
    garantir_renovacoes()

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

    return render_template(
        "dashboard.html",
        total_alunos=total_alunos,
        matriculas_ativas=matriculas_ativas,
        mensalidades_pendentes=mensalidades_pendentes,
        mensalidades_atrasadas=mensalidades_atrasadas,
        vencem_7dias=vencem_7dias,
    )
