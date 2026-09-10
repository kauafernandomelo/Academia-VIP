#!/usr/bin/env python3
"""
Script de seed - Gera 100 alunos aleatorios com cobranca integral
Roda: cd backend && python seed.py
"""

import random
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app import criar_app
from models import db, Aluno, Plano, Matricula, Mensalidade, Pagamento
from regras import gerar_mensalidade_inicial
from dateutil.relativedelta import relativedelta

NOMES_MASCULINOS = [
    "Joao Pedro", "Lucas Oliveira", "Matheus Silva", "Gabriel Santos", "Rafael Lima",
    "Pedro Henrique", "Enzo Gabriel", "Arthur Miguel", "Bernardo Almeida", "Heitor Costa",
    "Lorenzo Fernandes", "Theo Pereira", "Davi Lucca", "Samuel Rodrigues", "Benjamin Araujo",
    "Nicolas Martins", "Henrique Ribeiro", "Gustavo Henrique", "Felipe Cardoso", "Leonardo Barbosa",
    "Bruno Nascimento", "Eduardo Mendes", "Thiago Barbosa", "Diego Vieira", "Ricardo Souza",
    "Marcos Vinicius", "Carlos Eduardo", "Andre Ferreira", "Paulo Ricardo", "Roberto Carlos",
    "Daniel Gomes", "Fernando Dias", "Alexandre Ribeiro", "Claudio Martins", "Rogerio Santos",
    "Fabio Almeida", "Juliano Costa", "Marcio Pereira", "Leandro Lima", "Cristiano Araujo",
    "Adriano Silva", "Marcelo Oliveira", "Antonio Carlos", "Jose Eduardo", "Francisco Almeida",
    "Roberto Neto", "Carlos Alberto", "Joao Vitor", "Pedro Lucas", "Miguel Santos",
]

NOMES_FEMININOS = [
    "Maria Eduarda", "Julia Ferreira", "Ana Clara", "Laura Rodrigues", "Helena Costa",
    "Valentina Araujo", "Giovanna Martins", "Livia Almeida", "Maria Luiza", "Cecilia Lima",
    "Beatriz Santos", "Maria Julia", "Sophia Pereira", "Isabela Oliveira", "Maria Clara",
    "Lorena Ribeiro", "Gabriela Barbosa", "Ana Luisa", "Maria Fernanda", "Lara Gomes",
    "Marina Dias", "Isabela Cardoso", "Ana Beatriz", "Carolina Souza", "Fernanda Lima",
    "Renata Nascimento", "Patricia Mendes", "Claudia Vieira", "Adriana Martins", "Camila Santos",
    "Vanessa Oliveira", "Luciana Almeida", "Aline Costa", "Cristiane Pereira", "Simone Ribeiro",
    "Tatiane Lima", "Priscila Araujo", "Rosana Barbosa", "Denise Rodrigues", "Eliane Gomes",
    "Sandra Dias", "Marta Cardoso", "Raquel Ferreira", "Juliana Martins", "Bianca Souza",
    "Daniela Nascimento", "Amanda Lima", "Priscila Santos", "Leticia Almeida", "Camila Oliveira",
]

SOBRENOMES = [
    "da Silva", "dos Santos", "de Oliveira", "Souza", "Ferreira", "Almeida",
    "Pereira", "Costa", "Rodrigues", "Nascimento", "Lima", "Araujo",
    "Barbosa", "Ribeiro", "Martins", "Gomes", "Cardoso", "Dias",
    "Vieira", "Mendes", "Moreira", "Castro", "Rocha", "Carvalho",
    "Batista", "Freitas", "Correia", "Teixeira", "Azevedo", "Monteiro",
]

FORMAS_PAGAMENTO = ["dinheiro", "pix", "cartao_credito", "cartao_debito", "boleto"]


def gerar_cpf():
    cpf = [random.randint(0, 9) for _ in range(9)]
    soma = sum((10 - i) * cpf[i] for i in range(9))
    resto = soma % 11
    cpf.append(0 if resto < 2 else 11 - resto)
    soma = sum((11 - i) * cpf[i] for i in range(10))
    resto = soma % 11
    cpf.append(0 if resto < 2 else 11 - resto)
    return f"{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}"


def gerar_telefone():
    ddd = random.choice([11, 21, 31, 41, 51, 61, 71, 81, 91, 12, 13, 14, 15, 16, 17, 18, 19, 22, 24, 27, 28, 32, 33, 34, 35, 37, 38, 42, 43, 44, 45, 46, 47, 48, 49])
    return f"({ddd}) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


def criar_seed():
    app = criar_app()

    with app.app_context():
        print("Limpando dados antigos...")
        Pagamento.query.delete()
        Mensalidade.query.delete()
        Matricula.query.delete()
        Aluno.query.delete()
        db.session.commit()

        print("Buscando planos...")
        planos = Plano.query.filter_by(ativo=True).order_by(Plano.valor).all()
        if not planos:
            print("ERRO: Nenhum plano encontrado. Execute init_db.py primeiro.")
            return

        plano_map = {p.nome: p for p in planos}
        print(f"Planos encontrados: {[p.nome for p in planos]}")

        hoje = date.today()
        alunos_criados = 0
        mensalidades_criadas = 0
        pagamentos_registrados = 0
        renovacoes_pendentes = 0

        print("Criando 100 alunos (cobranca integral)...")

        for i in range(100):
            if random.random() < 0.55:
                nome_base = random.choice(NOMES_MASCULINOS)
            else:
                nome_base = random.choice(NOMES_FEMININOS)
            sobrenome = random.choice(SOBRENOMES)
            nome = f"{nome_base} {sobrenome}"

            cpf = gerar_cpf()
            while Aluno.query.filter_by(cpf=cpf).first():
                cpf = gerar_cpf()

            aluno = Aluno(
                nome=nome,
                cpf=cpf,
                telefone=gerar_telefone(),
                data_nascimento=hoje - timedelta(days=random.randint(18*365, 55*365)),
                data_cadastro=hoje - timedelta(days=random.randint(0, 365)),
                ativo=random.random() > 0.05,
            )
            db.session.add(aluno)
            db.session.flush()
            alunos_criados += 1

            escolha = random.random()
            if escolha < 0.30:
                plano = plano_map.get("Mensal") or planos[0]
            elif escolha < 0.55:
                plano = plano_map.get("Trimestral") or planos[min(1, len(planos)-1)]
            elif escolha < 0.80:
                plano = plano_map.get("Semestral") or planos[min(2, len(planos)-1)]
            else:
                plano = plano_map.get("Anual") or planos[min(3, len(planos)-1)]

            dias_atras = random.randint(0, 90)
            data_inicio = hoje - timedelta(days=dias_atras)
            data_fim = data_inicio + relativedelta(months=plano.duracao_meses)

            matricula = Matricula(
                aluno_id=aluno.id,
                plano_id=plano.id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                ativa=data_fim >= hoje,
            )
            db.session.add(matricula)
            db.session.flush()

            # Cobranca integral: 1 pagamento = valor cheio do plano
            forma = random.choice(FORMAS_PAGAMENTO)
            gerar_mensalidade_inicial(matricula, plano, data_inicio, forma_pagamento=forma)
            mensalidades_criadas += 1
            pagamentos_registrados += 1

            # Alguns com renovacao pendente (plano perto de vencer ou vencido)
            if (data_fim - hoje).days <= 7 and matricula.ativa and random.random() < 0.4:
                renovacao = Mensalidade(
                    matricula_id=matricula.id,
                    valor=plano.valor,
                    data_vencimento=data_fim,
                    paga=False,
                )
                db.session.add(renovacao)
                renovacoes_pendentes += 1
                mensalidades_criadas += 1

        db.session.commit()

        print(f"\n{'='*50}")
        print(f"SEED CONCLUIDO (COBRANCA INTEGRAL)")
        print(f"{'='*50}")
        print(f"Alunos criados: {alunos_criados}")
        print(f"Matriculas criadas: {alunos_criados}")
        print(f"Mensalidades criadas: {mensalidades_criadas}")
        print(f"  - Pagas (integral): {pagamentos_registrados}")
        print(f"  - Renovacoes pendentes: {renovacoes_pendentes}")
        print(f"Pagamentos registrados: {pagamentos_registrados}")
        print(f"{'='*50}")

        total_pagas = Mensalidade.query.filter_by(paga=True).count()
        total_pendentes = Mensalidade.query.filter(
            Mensalidade.paga == False,
            Mensalidade.data_vencimento >= hoje
        ).count()
        total_atrasadas = Mensalidade.query.filter(
            Mensalidade.paga == False,
            Mensalidade.data_vencimento < hoje
        ).count()
        print(f"\nStatus das mensalidades:")
        print(f"  Pagas: {total_pagas}")
        print(f"  Pendentes (renovacoes): {total_pendentes}")
        print(f"  Atrasadas: {total_atrasadas}")
        print(f"\nAcesse o sistema e teste todas as paginas!")


if __name__ == "__main__":
    criar_seed()
