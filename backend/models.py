from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class TimestampMixin:
    criado_em = db.Column(db.DateTime, default=datetime.now, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


class Usuario(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Usuario {self.login}>"


class Aluno(db.Model, TimestampMixin):
    __tablename__ = "alunos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150))
    data_nascimento = db.Column(db.Date)
    data_cadastro = db.Column(db.Date, default=date.today, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    matriculas = db.relationship("Matricula", backref="aluno", lazy=True, cascade="all, delete-orphan")

    @property
    def idade(self):
        if self.data_nascimento:
            hoje = date.today()
            return (
                hoje.year
                - self.data_nascimento.year
                - (
                    (hoje.month, hoje.day)
                    < (self.data_nascimento.month, self.data_nascimento.day)
                )
            )
        return None

    def __repr__(self):
        return f"<Aluno {self.nome}>"


class Plano(db.Model, TimestampMixin):
    __tablename__ = "planos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    duracao_meses = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    matriculas = db.relationship("Matricula", backref="plano", lazy=True)

    def __repr__(self):
        return f"<Plano {self.nome}>"


class Matricula(db.Model, TimestampMixin):
    __tablename__ = "matriculas"

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey("planos.id"), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    ativa = db.Column(db.Boolean, default=True, nullable=False)

    mensalidades = db.relationship(
        "Mensalidade", backref="matricula", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def esta_vigente(self):
        return self.ativa and self.data_inicio <= date.today() <= self.data_fim

    @property
    def mensalidade_atual(self):
        hoje = date.today()
        for m in self.mensalidades:
            if m.data_vencimento.month == hoje.month and m.data_vencimento.year == hoje.year:
                return m
        return None

    @property
    def dias_restantes(self):
        """Dias que faltam para o acesso expirar.

        Se existir uma mensalidade do mes atual NAO paga, conta ate o
        vencimento dela (pode ser negativo -> atrasada). Caso contrario
        (planos integrais ja pagos / sem cobranca pendente), conta ate o
        fim do periodo do plano (data_fim).
        """
        if not self.ativa:
            return None
        hoje = date.today()
        mensalidade = self.mensalidade_atual
        if mensalidade and not mensalidade.paga:
            return (mensalidade.data_vencimento - hoje).days
        return (self.data_fim - hoje).days

    def __repr__(self):
        return f"<Matricula {self.id} - Aluno {self.aluno_id}>"


class Mensalidade(db.Model, TimestampMixin):
    __tablename__ = "mensalidades"

    id = db.Column(db.Integer, primary_key=True)
    matricula_id = db.Column(
        db.Integer, db.ForeignKey("matriculas.id"), nullable=False
    )
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    paga = db.Column(db.Boolean, default=False, nullable=False)
    observacao = db.Column(db.Text)

    pagamentos = db.relationship(
        "Pagamento", backref="mensalidade", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def esta_atrasada(self):
        return not self.paga and date.today() > self.data_vencimento

    @property
    def dias_restantes(self):
        if self.paga:
            return None
        delta = self.data_vencimento - date.today()
        return delta.days

    @property
    def status_display(self):
        if self.paga:
            return "Paga"
        if self.esta_atrasada:
            return "Atrasada"
        return "Pendente"

    def __repr__(self):
        return f"<Mensalidade {self.id} - {self.status_display}>"


class Pagamento(db.Model, TimestampMixin):
    __tablename__ = "pagamentos"

    id = db.Column(db.Integer, primary_key=True)
    mensalidade_id = db.Column(
        db.Integer, db.ForeignKey("mensalidades.id"), nullable=False
    )
    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, default=date.today, nullable=False)
    forma_pagamento = db.Column(
        db.String(30), nullable=False
    )  # dinheiro, pix, cartao, boleto
    observacao = db.Column(db.Text)

    def __repr__(self):
        return f"<Pagamento {self.id}>"
