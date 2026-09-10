"""Script para inicializar o banco de dados, criar o primeiro administrador e planos padrao."""

from app import criar_app
from models import db, Usuario, Plano

app = criar_app()

with app.app_context():
    db.create_all()

    # Criar administrador
    if not Usuario.query.filter_by(login="admin").first():
        admin = Usuario(
            nome="Administrador",
            login="admin",
            admin=True,
        )
        admin.definir_senha("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Administrador criado com sucesso!")
        print("Login: admin")
        print("Senha: admin123")
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
            print(f"Plano '{plano_data['nome']}' criado com sucesso!")

    db.session.commit()
    print("\nInicializacao concluida!")
