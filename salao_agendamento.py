"""
Protótipo em Python — Sistema de Gestão de Agendamentos para Salões de Beleza

"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Generic, TypeVar, Optional
from collections import Counter
import json
import os

# ---------------------------------------------------------------------------
# "Template" genérico de repositório (análogo a container/template da STL)
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Repositorio(Generic[T]):
    """Repositório genérico em memória para qualquer entidade do sistema."""

    def __init__(self) -> None:
        self._itens: dict[int, T] = {}
        self._proximo_id = 1

    def adicionar(self, item: T) -> int:
        item_id = self._proximo_id
        self._itens[item_id] = item
        self._proximo_id += 1
        return item_id

    def remover(self, item_id: int) -> None:
        self._itens.pop(item_id, None)

    def obter(self, item_id: int) -> Optional[T]:
        return self._itens.get(item_id)

    def listar(self) -> list[T]:
        return list(self._itens.values())


# ---------------------------------------------------------------------------
# Entidades básicas: Cliente e Funcionário
# ---------------------------------------------------------------------------

@dataclass
class Cliente:
    nome: str
    telefone: str
    plano: Optional["Plano"] = None

    def __str__(self) -> str:
        return f"Cliente({self.nome})"


@dataclass
class Funcionario:
    nome: str
    especialidades: list[str] = field(default_factory=list)
    procedimentos_habilitados: list[str] = field(default_factory=list)

    def habilita(self, procedimento_nome: str) -> None:
        if procedimento_nome not in self.procedimentos_habilitados:
            self.procedimentos_habilitados.append(procedimento_nome)

    def pode_realizar(self, procedimento_nome: str) -> bool:
        return procedimento_nome in self.procedimentos_habilitados

    def __str__(self) -> str:
        return f"Funcionario({self.nome})"


# ---------------------------------------------------------------------------
# Procedimentos adicionais opcionais — Classe Abstrata + Polimorfismo
# ---------------------------------------------------------------------------

class ProcedimentoAdicional(ABC):
    """Classe abstrata: cada procedimento define seu próprio custo/duração."""

    nome: str = "Procedimento genérico"

    @abstractmethod
    def custo_extra(self) -> float:
        ...

    @abstractmethod
    def duracao_extra_min(self) -> int:
        ...

    def __str__(self) -> str:
        return self.nome


class AvaliacaoCapilar(ProcedimentoAdicional):
    nome = "Avaliação capilar"

    def custo_extra(self) -> float:
        return 15.0

    def duracao_extra_min(self) -> int:
        return 10


class Hidratacao(ProcedimentoAdicional):
    nome = "Hidratação"

    def custo_extra(self) -> float:
        return 40.0

    def duracao_extra_min(self) -> int:
        return 25


class Tratamento(ProcedimentoAdicional):
    nome = "Tratamento"

    def custo_extra(self) -> float:
        return 60.0

    def duracao_extra_min(self) -> int:
        return 30


class Visagismo(ProcedimentoAdicional):
    nome = "Visagismo"

    def custo_extra(self) -> float:
        return 50.0

    def duracao_extra_min(self) -> int:
        return 20


# ---------------------------------------------------------------------------
# Etapa de execução e Serviço (composição)
# ---------------------------------------------------------------------------

@dataclass
class EtapaServico:
    nome: str
    duracao_min: int


class Servico:
    """Um serviço é composto por etapas fixas + procedimentos opcionais."""

    def __init__(self, nome: str, valor_base: float, etapas: list[EtapaServico]):
        self.nome = nome
        self.valor_base = valor_base
        self.etapas = etapas
        self.procedimentos_selecionados: list[ProcedimentoAdicional] = []

    def __add__(self, procedimento: ProcedimentoAdicional) -> "Servico":
        """Sobrecarga de operador: servico + procedimento adiciona opcional."""
        self.procedimentos_selecionados.append(procedimento)
        return self

    @property
    def valor_total(self) -> float:
        extra = sum(p.custo_extra() for p in self.procedimentos_selecionados)
        return self.valor_base + extra

    @property
    def duracao_total_min(self) -> int:
        base = sum(e.duracao_min for e in self.etapas)
        extra = sum(p.duracao_extra_min() for p in self.procedimentos_selecionados)
        return base + extra

    def clonar_base(self) -> "Servico":
        """Cria uma cópia do serviço apenas com as etapas base (sem extras),
        útil para montar um novo agendamento a partir de um serviço cadastrado."""
        novo = Servico(self.nome, self.valor_base, list(self.etapas))
        return novo

    def resumo(self) -> str:
        etapas_str = ", ".join(e.nome for e in self.etapas)
        extras_str = ", ".join(str(p) for p in self.procedimentos_selecionados) or "nenhum"
        return (f"{self.nome} | etapas: [{etapas_str}] | extras: [{extras_str}] "
                f"| duração: {self.duracao_total_min} min | valor: R$ {self.valor_total:.2f}")


# ---------------------------------------------------------------------------
# Planos / Pacotes — Strategy para cálculo de preço
# ---------------------------------------------------------------------------

class EstrategiaPreco(ABC):
    @abstractmethod
    def aplicar(self, valor: float) -> float:
        ...


class SemDesconto(EstrategiaPreco):
    def aplicar(self, valor: float) -> float:
        return valor


class DescontoPercentual(EstrategiaPreco):
    def __init__(self, percentual: float):
        self.percentual = percentual

    def aplicar(self, valor: float) -> float:
        return valor * (1 - self.percentual / 100)


@dataclass
class Plano:
    nome: str
    estrategia: EstrategiaPreco = field(default_factory=SemDesconto)

    def calcular(self, valor: float) -> float:
        return self.estrategia.aplicar(valor)


# ---------------------------------------------------------------------------
# Agendamento — ciclo de vida + verificação de conflitos
# ---------------------------------------------------------------------------

class StatusAgendamento(Enum):
    PENDENTE = auto()
    CONFIRMADO = auto()
    CONCLUIDO = auto()
    CANCELADO = auto()


class ConflitoDeHorarioError(Exception):
    pass


@dataclass
class Agendamento:
    cliente: Cliente
    funcionario: Funcionario
    servico: Servico
    horario_inicio: datetime
    status: StatusAgendamento = StatusAgendamento.PENDENTE

    @property
    def horario_fim(self) -> datetime:
        return self.horario_inicio + timedelta(minutes=self.servico.duracao_total_min)

    def sobrepoe(self, outro: "Agendamento") -> bool:
        return (self.horario_inicio < outro.horario_fim and
                outro.horario_inicio < self.horario_fim)

    def __lt__(self, outro: "Agendamento") -> bool:
        """Sobrecarga de operador: permite ordenar agendamentos por horário."""
        return self.horario_inicio < outro.horario_inicio

    def valor_final(self) -> float:
        if self.cliente.plano:
            return self.cliente.plano.calcular(self.servico.valor_total)
        return self.servico.valor_total

    def confirmar(self) -> None:
        self.status = StatusAgendamento.CONFIRMADO

    def concluir(self) -> None:
        self.status = StatusAgendamento.CONCLUIDO

    def cancelar(self) -> None:
        self.status = StatusAgendamento.CANCELADO

    def __str__(self) -> str:
        return (f"[{self.status.name}] {self.cliente.nome} com {self.funcionario.nome} "
                f"em {self.horario_inicio:%d/%m %H:%M} - {self.servico.nome} "
                f"(R$ {self.valor_final():.2f})")


# ---------------------------------------------------------------------------
# Sistema (Singleton) — orquestra tudo, gera métricas e persiste dados
# ---------------------------------------------------------------------------

class SistemaAgendamento:
    _instancia: Optional["SistemaAgendamento"] = None

    def __new__(cls) -> "SistemaAgendamento":
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False
        return cls._instancia

    def __init__(self) -> None:
        if self._inicializado:
            return
        self.clientes: Repositorio[Cliente] = Repositorio()
        self.funcionarios: Repositorio[Funcionario] = Repositorio()
        self.servicos: Repositorio[Servico] = Repositorio()
        self.agendamentos: Repositorio[Agendamento] = Repositorio()
        self._inicializado = True

    def agendar(self, cliente: Cliente, funcionario: Funcionario,
                servico: Servico, horario: datetime) -> Agendamento:
        novo = Agendamento(cliente, funcionario, servico, horario)
        for existente in self.agendamentos.listar():
            if (existente.funcionario is funcionario and
                    existente.status != StatusAgendamento.CANCELADO and
                    existente.sobrepoe(novo)):
                raise ConflitoDeHorarioError(
                    f"Conflito: {funcionario.nome} já tem um agendamento nesse horário.")
        self.agendamentos.adicionar(novo)
        return novo

    # --- Métricas gerenciais -------------------------------------------------

    def profissionais_mais_requisitados(self) -> list[tuple[str, int]]:
        contagem = Counter(a.funcionario.nome for a in self.agendamentos.listar())
        return contagem.most_common()

    def servicos_mais_procurados(self) -> list[tuple[str, int]]:
        contagem = Counter(a.servico.nome for a in self.agendamentos.listar())
        return contagem.most_common()

    def taxa_ocupacao_por_funcionario(self, jornada_min: int = 480) -> dict[str, float]:
        minutos_por_funcionario: dict[str, int] = {}
        for a in self.agendamentos.listar():
            if a.status == StatusAgendamento.CANCELADO:
                continue
            minutos_por_funcionario[a.funcionario.nome] = (
                minutos_por_funcionario.get(a.funcionario.nome, 0)
                + a.servico.duracao_total_min)
        return {nome: round(min_ocupado / jornada_min * 100, 1)
                for nome, min_ocupado in minutos_por_funcionario.items()}

    def exportar_relatorio(self, caminho: str) -> None:
        linhas = ["=== Relatório de Métricas ===", ""]
        linhas.append("Profissionais mais requisitados:")
        for nome, qtd in self.profissionais_mais_requisitados():
            linhas.append(f"  - {nome}: {qtd} atendimento(s)")
        linhas.append("")
        linhas.append("Serviços mais procurados:")
        for nome, qtd in self.servicos_mais_procurados():
            linhas.append(f"  - {nome}: {qtd} vez(es)")
        linhas.append("")
        linhas.append("Taxa de ocupação por profissional:")
        for nome, taxa in self.taxa_ocupacao_por_funcionario().items():
            linhas.append(f"  - {nome}: {taxa}%")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))

    # --- Persistência simples (JSON) -----------------------------------------

    def salvar(self, caminho: str) -> None:
        dados = {
            "clientes": [c.nome for c in self.clientes.listar()],
            "funcionarios": [f.nome for f in self.funcionarios.listar()],
            "agendamentos": [
                {
                    "cliente": a.cliente.nome,
                    "funcionario": a.funcionario.nome,
                    "servico": a.servico.nome,
                    "horario": a.horario_inicio.isoformat(),
                    "status": a.status.name,
                    "valor": round(a.valor_final(), 2),
                }
                for a in self.agendamentos.listar()
            ],
        }
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Demonstração (main)
# ---------------------------------------------------------------------------

def demo() -> None:
    sistema = SistemaAgendamento()

    # Cadastro de clientes e funcionários (req. 1 e 2)
    ana = Cliente("Ana Souza", "41 99999-0001")
    bruno = Cliente("Bruno Lima", "41 99999-0002")
    sistema.clientes.adicionar(ana)
    sistema.clientes.adicionar(bruno)

    carla = Funcionario("Carla", especialidades=["Cabelo"])
    carla.habilita("Hidratação")
    carla.habilita("Avaliação capilar")
    diego = Funcionario("Diego", especialidades=["Cabelo", "Visagismo"])
    diego.habilita("Visagismo")
    sistema.funcionarios.adicionar(carla)
    sistema.funcionarios.adicionar(diego)

    # Cadastro de serviço com etapas (req. 3 e 4)
    corte = Servico(
        "Corte + Escova", 80.0,
        etapas=[EtapaServico("Lavagem", 10), EtapaServico("Corte", 30), EtapaServico("Escova", 20)],
    )
    # Composição de procedimentos adicionais (req. 6), verificando habilitação (req. 7)
    if carla.pode_realizar("Hidratação"):
        corte = corte + Hidratacao()
    print(corte.resumo())

    # Plano do cliente (req. 12 e 13)
    ana.plano = Plano("Plano Ouro", DescontoPercentual(15))

    # Agendamento com verificação de conflito (req. 8 e 9)
    horario1 = datetime(2026, 9, 10, 14, 0)
    a1 = sistema.agendar(ana, carla, corte, horario1)
    a1.confirmar()
    print(a1)

    servico2 = Servico("Corte Simples", 50.0, etapas=[EtapaServico("Corte", 25)])
    try:
        # Conflito proposital: mesmo funcionário, horário sobreposto
        sistema.agendar(bruno, carla, servico2, datetime(2026, 9, 10, 14, 20))
    except ConflitoDeHorarioError as e:
        print(f"Falha esperada: {e}")

    a2 = sistema.agendar(bruno, diego, servico2, datetime(2026, 9, 10, 15, 0))
    a2.concluir()
    print(a2)

    # Métricas (req. 16, 17 e 18)
    print("\nProfissionais mais requisitados:", sistema.profissionais_mais_requisitados())
    print("Serviços mais procurados:", sistema.servicos_mais_procurados())
    print("Taxa de ocupação:", sistema.taxa_ocupacao_por_funcionario())

    # Exportação de relatório e persistência (req. 15 e 19)
    saida_dir = "/mnt/user-data/outputs"
    os.makedirs(saida_dir, exist_ok=True)
    sistema.exportar_relatorio(os.path.join(saida_dir, "relatorio_metricas.txt"))
    sistema.salvar(os.path.join(saida_dir, "dados_agendamentos.json"))
    print("\nArquivos gerados: relatorio_metricas.txt, dados_agendamentos.json")


if __name__ == "__main__":
    demo()
