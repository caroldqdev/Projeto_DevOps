"""

Para rodar localmente (requer um ambiente com tela / display):
    python3 salao_agendamento_gui.py
    
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from salao_agendamento import (
    SistemaAgendamento, Cliente, Funcionario, Servico, EtapaServico, Plano,
    DescontoPercentual, SemDesconto, AvaliacaoCapilar, Hidratacao, Tratamento,
    Visagismo, ConflitoDeHorarioError, StatusAgendamento,
)

PROCEDIMENTOS_DISPONIVEIS = {
    "Avaliação capilar": AvaliacaoCapilar,
    "Hidratação": Hidratacao,
    "Tratamento": Tratamento,
    "Visagismo": Visagismo,
}


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Gestão de Agendamentos — Salão de Beleza")
        self.geometry("880x560")

        self.sistema = SistemaAgendamento()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.aba_clientes = self._montar_aba_clientes(notebook)
        self.aba_funcionarios = self._montar_aba_funcionarios(notebook)
        self.aba_servicos = self._montar_aba_servicos(notebook)
        self.aba_agendar = self._montar_aba_agendar(notebook)
        self.aba_agenda = self._montar_aba_agenda(notebook)
        self.aba_metricas = self._montar_aba_metricas(notebook)

        notebook.add(self.aba_clientes, text="Clientes")
        notebook.add(self.aba_funcionarios, text="Funcionários")
        notebook.add(self.aba_servicos, text="Serviços")
        notebook.add(self.aba_agendar, text="Novo Agendamento")
        notebook.add(self.aba_agenda, text="Agenda")
        notebook.add(self.aba_metricas, text="Métricas")

    # ------------------------------------------------------------------ #
    # Aba: Clientes
    # ------------------------------------------------------------------ #
    def _montar_aba_clientes(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        form = ttk.LabelFrame(frame, text="Novo cliente")
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        nome_var = tk.StringVar()
        ttk.Entry(form, textvariable=nome_var, width=30).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Telefone:").grid(row=0, column=2, sticky="w", padx=5)
        tel_var = tk.StringVar()
        ttk.Entry(form, textvariable=tel_var, width=20).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Desconto do plano (%, 0 = sem plano):").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        desc_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=desc_var, width=8).grid(row=1, column=1, sticky="w", padx=5)

        lista = ttk.Treeview(frame, columns=("nome", "telefone", "plano"), show="headings", height=12)
        for col, titulo in [("nome", "Nome"), ("telefone", "Telefone"), ("plano", "Plano")]:
            lista.heading(col, text=titulo)
        lista.pack(fill="both", expand=True, padx=10, pady=10)

        def atualizar_lista() -> None:
            lista.delete(*lista.get_children())
            for c in self.sistema.clientes.listar():
                plano_txt = c.plano.nome if c.plano else "—"
                lista.insert("", "end", values=(c.nome, c.telefone, plano_txt))

        def adicionar() -> None:
            nome = nome_var.get().strip()
            tel = tel_var.get().strip()
            if not nome:
                messagebox.showwarning("Atenção", "Informe o nome do cliente.")
                return
            try:
                desconto = float(desc_var.get() or 0)
            except ValueError:
                messagebox.showwarning("Atenção", "Desconto inválido.")
                return
            plano = None
            if desconto > 0:
                plano = Plano(f"Plano {desconto:.0f}%", DescontoPercentual(desconto))
            cliente = Cliente(nome, tel, plano)
            self.sistema.clientes.adicionar(cliente)
            nome_var.set(""); tel_var.set(""); desc_var.set("0")
            atualizar_lista()
            self._atualizar_combos()

        ttk.Button(form, text="Adicionar cliente", command=adicionar).grid(
            row=1, column=2, columnspan=2, padx=5, pady=5)

        frame._atualizar_lista = atualizar_lista  # type: ignore[attr-defined]
        atualizar_lista()
        return frame

    # ------------------------------------------------------------------ #
    # Aba: Funcionários
    # ------------------------------------------------------------------ #
    def _montar_aba_funcionarios(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        form = ttk.LabelFrame(frame, text="Novo funcionário")
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        nome_var = tk.StringVar()
        ttk.Entry(form, textvariable=nome_var, width=25).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Especialidades (separadas por vírgula):").grid(
            row=0, column=2, sticky="w", padx=5)
        esp_var = tk.StringVar()
        ttk.Entry(form, textvariable=esp_var, width=30).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Procedimentos habilitados:").grid(
            row=1, column=0, sticky="nw", padx=5, pady=5)
        proc_vars: dict[str, tk.BooleanVar] = {}
        proc_frame = ttk.Frame(form)
        proc_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        for i, nome_proc in enumerate(PROCEDIMENTOS_DISPONIVEIS):
            var = tk.BooleanVar()
            ttk.Checkbutton(proc_frame, text=nome_proc, variable=var).grid(
                row=0, column=i, padx=5)
            proc_vars[nome_proc] = var

        lista = ttk.Treeview(frame, columns=("nome", "especialidades", "procedimentos"),
                              show="headings", height=12)
        for col, titulo in [("nome", "Nome"), ("especialidades", "Especialidades"),
                             ("procedimentos", "Procedimentos habilitados")]:
            lista.heading(col, text=titulo)
        lista.pack(fill="both", expand=True, padx=10, pady=10)

        def atualizar_lista() -> None:
            lista.delete(*lista.get_children())
            for f in self.sistema.funcionarios.listar():
                lista.insert("", "end", values=(
                    f.nome, ", ".join(f.especialidades), ", ".join(f.procedimentos_habilitados)))

        def adicionar() -> None:
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showwarning("Atenção", "Informe o nome do funcionário.")
                return
            especialidades = [e.strip() for e in esp_var.get().split(",") if e.strip()]
            funcionario = Funcionario(nome, especialidades)
            for nome_proc, var in proc_vars.items():
                if var.get():
                    funcionario.habilita(nome_proc)
            self.sistema.funcionarios.adicionar(funcionario)
            nome_var.set(""); esp_var.set("")
            for var in proc_vars.values():
                var.set(False)
            atualizar_lista()
            self._atualizar_combos()

        ttk.Button(form, text="Adicionar funcionário", command=adicionar).grid(
            row=2, column=0, columnspan=4, pady=8)

        frame._atualizar_lista = atualizar_lista  # type: ignore[attr-defined]
        atualizar_lista()
        return frame

    # ------------------------------------------------------------------ #
    # Aba: Serviços
    # ------------------------------------------------------------------ #
    def _montar_aba_servicos(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        form = ttk.LabelFrame(frame, text="Novo serviço")
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        nome_var = tk.StringVar()
        ttk.Entry(form, textvariable=nome_var, width=25).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Valor base (R$):").grid(row=0, column=2, sticky="w", padx=5)
        valor_var = tk.StringVar()
        ttk.Entry(form, textvariable=valor_var, width=12).grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Etapas (formato: nome:duração_min, separadas por vírgula):").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        etapas_var = tk.StringVar(value="Lavagem:10, Corte:30, Secagem:15")
        ttk.Entry(form, textvariable=etapas_var, width=45).grid(
            row=1, column=2, columnspan=2, padx=5)

        lista = ttk.Treeview(frame, columns=("nome", "valor", "etapas"), show="headings", height=12)
        for col, titulo in [("nome", "Nome"), ("valor", "Valor base"), ("etapas", "Etapas")]:
            lista.heading(col, text=titulo)
        lista.pack(fill="both", expand=True, padx=10, pady=10)

        def atualizar_lista() -> None:
            lista.delete(*lista.get_children())
            for s in self.sistema.servicos.listar():
                etapas_txt = ", ".join(f"{e.nome}({e.duracao_min}min)" for e in s.etapas)
                lista.insert("", "end", values=(s.nome, f"R$ {s.valor_base:.2f}", etapas_txt))

        def adicionar() -> None:
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showwarning("Atenção", "Informe o nome do serviço.")
                return
            try:
                valor = float(valor_var.get())
            except ValueError:
                messagebox.showwarning("Atenção", "Valor base inválido.")
                return
            etapas: list[EtapaServico] = []
            try:
                for parte in etapas_var.get().split(","):
                    nome_etapa, dur = parte.strip().split(":")
                    etapas.append(EtapaServico(nome_etapa.strip(), int(dur)))
            except ValueError:
                messagebox.showwarning("Atenção", "Formato de etapas inválido. Use nome:duração.")
                return
            if not etapas:
                messagebox.showwarning("Atenção", "Informe ao menos uma etapa.")
                return
            servico = Servico(nome, valor, etapas)
            self.sistema.servicos.adicionar(servico)
            nome_var.set(""); valor_var.set("")
            atualizar_lista()
            self._atualizar_combos()

        ttk.Button(form, text="Adicionar serviço", command=adicionar).grid(
            row=2, column=0, columnspan=4, pady=8)

        frame._atualizar_lista = atualizar_lista  # type: ignore[attr-defined]
        atualizar_lista()
        return frame

    # ------------------------------------------------------------------ #
    # Aba: Novo Agendamento
    # ------------------------------------------------------------------ #
    def _montar_aba_agendar(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        form = ttk.LabelFrame(frame, text="Marcar agendamento")
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Cliente:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        cliente_combo = ttk.Combobox(form, state="readonly", width=25)
        cliente_combo.grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Funcionário:").grid(row=0, column=2, sticky="w", padx=5)
        func_combo = ttk.Combobox(form, state="readonly", width=25)
        func_combo.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Serviço base:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        servico_combo = ttk.Combobox(form, state="readonly", width=25)
        servico_combo.grid(row=1, column=1, padx=5)

        ttk.Label(form, text="Data/hora (DD/MM/AAAA HH:MM):").grid(
            row=1, column=2, sticky="w", padx=5)
        horario_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y %H:%M"))
        ttk.Entry(form, textvariable=horario_var, width=25).grid(row=1, column=3, padx=5)

        ttk.Label(form, text="Procedimentos adicionais (só os habilitados p/ o funcionário):").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 0))
        extras_frame = ttk.Frame(form)
        extras_frame.grid(row=3, column=0, columnspan=4, sticky="w", padx=5)
        extras_vars: dict[str, tk.BooleanVar] = {}

        def atualizar_extras(*_args) -> None:
            for w in extras_frame.winfo_children():
                w.destroy()
            extras_vars.clear()
            func = self._funcionario_por_nome(func_combo.get())
            if not func:
                return
            for i, nome_proc in enumerate(func.procedimentos_habilitados):
                var = tk.BooleanVar()
                ttk.Checkbutton(extras_frame, text=nome_proc, variable=var).grid(
                    row=0, column=i, padx=5)
                extras_vars[nome_proc] = var

        func_combo.bind("<<ComboboxSelected>>", atualizar_extras)

        resultado_var = tk.StringVar()
        ttk.Label(frame, textvariable=resultado_var, foreground="blue").pack(
            fill="x", padx=10, pady=5)

        def agendar() -> None:
            cliente = self._cliente_por_nome(cliente_combo.get())
            func = self._funcionario_por_nome(func_combo.get())
            base = self._servico_por_nome(servico_combo.get())
            if not (cliente and func and base):
                messagebox.showwarning("Atenção", "Selecione cliente, funcionário e serviço.")
                return
            try:
                horario = datetime.strptime(horario_var.get().strip(), "%d/%m/%Y %H:%M")
            except ValueError:
                messagebox.showwarning("Atenção", "Data/hora inválida. Use DD/MM/AAAA HH:MM.")
                return

            servico = base.clonar_base()
            for nome_proc, var in extras_vars.items():
                if var.get():
                    servico = servico + PROCEDIMENTOS_DISPONIVEIS[nome_proc]()

            try:
                ag = self.sistema.agendar(cliente, func, servico, horario)
            except ConflitoDeHorarioError as e:
                messagebox.showerror("Conflito de horário", str(e))
                return

            resultado_var.set(f"Agendado: {ag}")
            self.aba_agenda._atualizar_lista()  # type: ignore[attr-defined]

        ttk.Button(form, text="Confirmar agendamento", command=agendar).grid(
            row=4, column=0, columnspan=4, pady=10)

        frame._cliente_combo = cliente_combo  # type: ignore[attr-defined]
        frame._func_combo = func_combo  # type: ignore[attr-defined]
        frame._servico_combo = servico_combo  # type: ignore[attr-defined]
        return frame

    # ------------------------------------------------------------------ #
    # Aba: Agenda (lista de agendamentos + status)
    # ------------------------------------------------------------------ #
    def _montar_aba_agenda(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        lista = ttk.Treeview(
            frame, columns=("cliente", "funcionario", "servico", "horario", "status", "valor"),
            show="headings", height=16)
        titulos = {"cliente": "Cliente", "funcionario": "Funcionário", "servico": "Serviço",
                   "horario": "Horário", "status": "Status", "valor": "Valor"}
        for col, titulo in titulos.items():
            lista.heading(col, text=titulo)
        lista.pack(fill="both", expand=True, padx=10, pady=10)

        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", padx=10, pady=(0, 10))

        def atualizar_lista() -> None:
            lista.delete(*lista.get_children())
            for idx, a in enumerate(sorted(self.sistema.agendamentos.listar())):
                lista.insert("", "end", iid=str(idx), values=(
                    a.cliente.nome, a.funcionario.nome, a.servico.nome,
                    a.horario_inicio.strftime("%d/%m/%Y %H:%M"), a.status.name,
                    f"R$ {a.valor_final():.2f}"))
            lista._mapa = {str(i): a for i, a in enumerate(sorted(self.sistema.agendamentos.listar()))}  # type: ignore

        def mudar_status(novo_status: StatusAgendamento) -> None:
            sel = lista.selection()
            if not sel:
                messagebox.showinfo("Info", "Selecione um agendamento na lista.")
                return
            agendamento = lista._mapa.get(sel[0])  # type: ignore[attr-defined]
            if agendamento is None:
                return
            if novo_status == StatusAgendamento.CONFIRMADO:
                agendamento.confirmar()
            elif novo_status == StatusAgendamento.CONCLUIDO:
                agendamento.concluir()
            elif novo_status == StatusAgendamento.CANCELADO:
                agendamento.cancelar()
            atualizar_lista()

        ttk.Button(botoes, text="Confirmar",
                   command=lambda: mudar_status(StatusAgendamento.CONFIRMADO)).pack(side="left", padx=5)
        ttk.Button(botoes, text="Concluir",
                   command=lambda: mudar_status(StatusAgendamento.CONCLUIDO)).pack(side="left", padx=5)
        ttk.Button(botoes, text="Cancelar",
                   command=lambda: mudar_status(StatusAgendamento.CANCELADO)).pack(side="left", padx=5)
        ttk.Button(botoes, text="Atualizar lista", command=atualizar_lista).pack(side="right", padx=5)

        frame._atualizar_lista = atualizar_lista  # type: ignore[attr-defined]
        atualizar_lista()
        return frame

    # ------------------------------------------------------------------ #
    # Aba: Métricas
    # ------------------------------------------------------------------ #
    def _montar_aba_metricas(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent)

        texto = tk.Text(frame, height=20, wrap="word")
        texto.pack(fill="both", expand=True, padx=10, pady=10)

        def calcular() -> None:
            texto.delete("1.0", "end")
            texto.insert("end", "=== Profissionais mais requisitados ===\n")
            for nome, qtd in self.sistema.profissionais_mais_requisitados():
                texto.insert("end", f"  {nome}: {qtd} atendimento(s)\n")
            texto.insert("end", "\n=== Serviços mais procurados ===\n")
            for nome, qtd in self.sistema.servicos_mais_procurados():
                texto.insert("end", f"  {nome}: {qtd} vez(es)\n")
            texto.insert("end", "\n=== Taxa de ocupação por funcionário ===\n")
            for nome, taxa in self.sistema.taxa_ocupacao_por_funcionario().items():
                texto.insert("end", f"  {nome}: {taxa}%\n")

        def exportar() -> None:
            import os
            pasta = "/mnt/user-data/outputs"
            os.makedirs(pasta, exist_ok=True)
            self.sistema.exportar_relatorio(os.path.join(pasta, "relatorio_metricas.txt"))
            self.sistema.salvar(os.path.join(pasta, "dados_agendamentos.json"))
            messagebox.showinfo("Exportado", "Relatório e dados exportados com sucesso.")

        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(botoes, text="Calcular métricas", command=calcular).pack(side="left", padx=5)
        ttk.Button(botoes, text="Exportar relatório + JSON", command=exportar).pack(side="left", padx=5)

        return frame

    # ------------------------------------------------------------------ #
    # Utilitários
    # ------------------------------------------------------------------ #
    def _atualizar_combos(self) -> None:
        nomes_clientes = [c.nome for c in self.sistema.clientes.listar()]
        nomes_funcs = [f.nome for f in self.sistema.funcionarios.listar()]
        nomes_servicos = [s.nome for s in self.sistema.servicos.listar()]
        self.aba_agendar._cliente_combo["values"] = nomes_clientes  # type: ignore[attr-defined]
        self.aba_agendar._func_combo["values"] = nomes_funcs  # type: ignore[attr-defined]
        self.aba_agendar._servico_combo["values"] = nomes_servicos  # type: ignore[attr-defined]

    def _cliente_por_nome(self, nome: str) -> Cliente | None:
        return next((c for c in self.sistema.clientes.listar() if c.nome == nome), None)

    def _funcionario_por_nome(self, nome: str) -> Funcionario | None:
        return next((f for f in self.sistema.funcionarios.listar() if f.nome == nome), None)

    def _servico_por_nome(self, nome: str) -> Servico | None:
        return next((s for s in self.sistema.servicos.listar() if s.nome == nome), None)


if __name__ == "__main__":
    app = App()
    app.mainloop()
