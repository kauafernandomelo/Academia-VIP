"""Constantes centralizadas do projeto Academia VIP."""

from enum import Enum


class JanelaRenovacao:
    """Configurações da janela de renovação automática."""
    DIAS = 7


class StatusMatricula(str, Enum):
    """Status possíveis de uma matrícula."""
    VIGENTE = "vigente"
    ATIVA = "ativa"
    ENCERRADA = "encerrada"
    SEM_PLANO = "sem_plano"


class StatusMensalidade(str, Enum):
    """Status possíveis de uma mensalidade."""
    PAGA = "paga"
    PENDENTE = "pendente"
    ATRASADA = "atrasada"
    ESTIMADA = "estimada"


class FormaPagamento(str, Enum):
    """Formas de pagamento aceitas."""
    DINHEIRO = "dinheiro"
    PIX = "pix"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    BOLETO = "boleto"

    @classmethod
    def choices(cls):
        return [(f.value, f.label) for f in cls]

    @property
    def label(self):
        return FORMA_PAGAMENTO_LABELS[self]


FORMA_PAGAMENTO_LABELS = {
    FormaPagamento.DINHEIRO: "Dinheiro",
    FormaPagamento.PIX: "PIX",
    FormaPagamento.CARTAO_CREDITO: "Cartão de Crédito",
    FormaPagamento.CARTAO_DEBITO: "Cartão de Débito",
    FormaPagamento.BOLETO: "Boleto",
}


STATUS_MATRICULA_LABELS = {
    StatusMatricula.VIGENTE: ("Vigente", "success"),
    StatusMatricula.ATIVA: ("Ativa", "warning"),
    StatusMatricula.ENCERRADA: ("Encerrada", "secondary"),
    StatusMatricula.SEM_PLANO: ("Sem plano", "secondary"),
}

STATUS_MENSALIDADE_LABELS = {
    StatusMensalidade.PAGA: ("Paga", "success"),
    StatusMensalidade.PENDENTE: ("Pendente", "warning"),
    StatusMensalidade.ATRASADA: ("Atrasada", "danger"),
    StatusMensalidade.ESTIMADA: ("Estimada", "info"),
}

ALUNO_STATUS_LABELS = {
    True: ("Ativo", "success"),
    False: ("Inativo", "secondary"),
}

MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

PAGINACAO_POR_PAGINA = 10
PAGINACAO_MENSALIDADES = 15