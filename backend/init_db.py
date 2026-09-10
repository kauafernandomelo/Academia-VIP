"""Script para inicializar o banco de dados, criar o primeiro administrador, planos padrao e 100 alunos de teste."""

import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app import criar_app
from models import db, Usuario, Plano, Aluno, Matricula, Mensalidade, Pagamento

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
    "Daniela Nascimento", "Amanda Lima", "Priscila Santos", "Letitia Almeida", "Camila Oliveira",
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


def seed_alunos(planos):
    if Aluno.query.count() >= 50:
        print(f"Banco ja tem {Aluno.query.count()} alunos. Pulando seed.")
        return

    print("Criando 100 alunos de teste...")
    hoje = date.today()
    plano_map = {p.nome: p for p in planos}
    cpfs_usados = set()

    for i in range(100):
        if random.random() < 0.55:
            nome_base = random.choice(NOMES_MASCULINOS)
        else:
            nome_base = random.choice(NOMES_FEMININOS)
        sobrenome = random.choice(SOBRENOMES)
        nome = f"{nome_base} {sobrenome}"

        cpf = gerar_cpf()
        while cpf in cpfs_usados:
            cpf = gerar_cpf()
        cpfs_usados.add(cpf)

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

        valor_mensal = float(plano.valor) / plano.duracao_meses
        for j in range(plano.duracao_meses):
            vencimento = data_inicio + relativedelta(months=j)
            cenario = random.random()

            mensalidade = Mensalidade(
                matricula_id=matricula.id,
                valor=valor_mensal,
                data_vencimento=vencimento,
                paga=False,
            )
            db.session.add(mensalidade)
            db.session.flush()

            if cenario < 0.35:
                data_pag = vencimento + timedelta(days=random.randint(-5, 2))
                if data_pag > hoje:
                    data_pag = hoje - timedelta(days=random.randint(0, 5))
                mensalidade.paga = True
                mensalidade.data_pagamento = data_pag
                pagamento = Pagamento(
                    mensalidade_id=mensalidade.id,
                    valor_pago=valor_mensal,
                    data_pagamento=data_pag,
                    forma_pagamento=random.choice(FORMAS_PAGAMENTO),
                )
                db.session.add(pagamento)
            elif cenario < 0.55:
                pass
            elif cenario < 0.75:
                pass
            else:
                data_pag = vencimento + timedelta(days=random.randint(1, 30))
                if data_pag > hoje:
                    data_pag = hoje - timedelta(days=random.randint(0, 3))
                mensalidade.paga = True
                mensalidade.data_pagamento = data_pag
                pagamento = Pagamento(
                    mensalidade_id=mensalidade.id,
                    valor_pago=valor_mensal,
                    data_pagamento=data_pag,
                    forma_pagamento=random.choice(FORMAS_PAGAMENTO),
                )
                db.session.add(pagamento)

    db.session.commit()

    total_pagas = Mensalidade.query.filter_by(paga=True).count()
    total_pendentes = Mensalidade.query.filter(Mensalidade.paga == False, Mensalidade.data_vencimento >= hoje).count()
    total_atrasadas = Mensalidade.query.filter(Mensalidade.paga == False, Mensalidade.data_vencimento < hoje).count()

    print(f"100 alunos criados!")
    print(f"Mensalidades: {Mensalidade.query.count()}")
    print(f"Pagamentos: {Pagamento.query.count()}")
    print(f"  Pagas: {total_pagas}")
    print(f"  Pendentes: {total_pendentes}")
    print(f"  Atrasadas: {total_atrasadas}")


app = criar_app()

with app.app_context():
    db.create_all()

    # Criar administrador
    if not Usuario.query.filter_by(login="admin").first():
        admin = Usuario(nome="Administrador", login="admin", admin=True)
        admin.definir_senha("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Administrador criado: admin / admin123")
    else:
        print("Administrador ja existe.")

    # Criar planos padrao
    planos_padrao = [
        {"nome": "Mensal", "valor": 65.00, "duracao_meses": 1, "descricao": "Plano mensal sem desconto"},
        {"nome": "Trimestral", "valor": 175.50, "duracao_meses": 3, "descricao": "Plano trimestral com 10% de desconto (R$58,50/mes)"},
        {"nome": "Semestral", "valor": 331.50, "duracao_meses": 6, "descricao": "Plano semestral com 15% de desconto (R$55,25/mes)"},
        {"nome": "Anual", "valor": 624.00, "duracao_meses": 12, "descricao": "Plano anual com 20% de desconto (R$52,00/mes)"},
    ]

    for plano_data in planos_padrao:
        if not Plano.query.filter_by(nome=plano_data["nome"]).first():
            plano = Plano(**plano_data)
            db.session.add(plano)

    db.session.commit()
    print("Planos criados/verificados.")

    # Seed 100 alunos
    planos = Plano.query.filter_by(ativo=True).all()
    seed_alunos(planos)

    print("\nInicializacao concluida!")
