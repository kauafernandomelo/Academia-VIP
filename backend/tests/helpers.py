"""Helpers reutilizaveis entre modulos de teste."""

from datetime import date

from dateutil.relativedelta import relativedelta

from models import Aluno, Matricula, db
from regras import gerar_mensalidade_inicial


_cpf_counter = 0


def criar_aluno_com_matricula(plano, data_inicio, forma_pagamento="pix"):
    """Helper: cria aluno+matricula com cobranca integral e retorna os objetos.

    Deve ser chamado dentro de um app_context.
    """
    global _cpf_counter
    _cpf_counter += 1
    cpf_base = f"123.456.78{_cpf_counter % 10:01d}-{_cpf_counter % 100:02d}"
    while Aluno.query.filter_by(cpf=cpf_base).first():
        _cpf_counter += 1
        cpf_base = f"123.456.78{_cpf_counter % 10:01d}-{_cpf_counter % 100:02d}"

    aluno = Aluno(
        nome=f"Aluno Teste {_cpf_counter}",
        cpf=cpf_base,
        telefone="(11) 99999-9999",
        data_cadastro=data_inicio,
    )
    db.session.add(aluno)
    db.session.flush()

    data_fim = data_inicio + relativedelta(months=plano.duracao_meses)
    matricula = Matricula(
        aluno_id=aluno.id,
        plano_id=plano.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        ativa=True,
    )
    db.session.add(matricula)
    db.session.flush()

    gerar_mensalidade_inicial(matricula, plano, data_inicio, forma_pagamento=forma_pagamento)
    db.session.commit()
    return aluno, matricula