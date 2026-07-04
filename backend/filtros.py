"""
filtros.py — Parse dos filtros da query string e montagem do WHERE em SQL.

Todos os endpoints compartilham o mesmo conjunto de filtros:

    anos=2024,2025          anos de notificação (obrigatório na prática;
                            default = ano mais recente disponível)
    ufs=SP,RJ               siglas de UF (vazio = todas)
    sexo=Masculino          valores exatos da coluna `sexo`
    formas=Pulmonar         valores exatos da coluna `forma`
    racas=Parda,Preta       valores exatos da coluna `raca_cor`
    entradas=Caso Novo      valores exatos da coluna `tipo_entrada`
    hiv=Positivo            valores exatos da coluna `status_hiv`
    vuln=populacao_situacao_rua,...    flags que devem ser 'Sim' (AND)
    agravos=agravo_diabetes,...        flags que devem ser 'Sim' (AND)

A montagem usa parâmetros posicionais (?) do DuckDB — nunca interpola
valores do usuário no SQL. Nomes de colunas de vuln/agravos são validados
contra whitelist.
"""

from dataclasses import dataclass, field

from constantes import AGRAVOS, POPULACOES, UF_VARIANTES

_COLS_VULN    = tuple(POPULACOES.keys())
_COLS_AGRAVOS = tuple(AGRAVOS.keys())


@dataclass(frozen=True)
class Filtros:
    """Filtros imutáveis e hasheáveis — servem de chave de cache."""
    anos:     tuple[int, ...]
    ufs:      tuple[str, ...] = ()
    sexo:     tuple[str, ...] = ()
    formas:   tuple[str, ...] = ()
    racas:    tuple[str, ...] = ()
    entradas: tuple[str, ...] = ()
    hiv:      tuple[str, ...] = ()
    vuln:     tuple[str, ...] = ()
    agravos:  tuple[str, ...] = ()

    def where_sql(self) -> tuple[str, list]:
        """Retorna (cláusula WHERE, parâmetros) para a CTE `sinan`."""
        conds: list[str] = []
        params: list = []

        if self.ufs:
            nomes: list[str] = []
            for sigla in self.ufs:
                nomes.extend(UF_VARIANTES.get(sigla, []))
            if nomes:
                ph = ", ".join("?" * len(nomes))
                conds.append(f"estado_notificacao IN ({ph})")
                params.extend(nomes)

        for col, valores in (
            ("sexo", self.sexo),
            ("forma", self.formas),
            ("raca_cor", self.racas),
            ("tipo_entrada", self.entradas),
            ("status_hiv", self.hiv),
        ):
            if valores:
                ph = ", ".join("?" * len(valores))
                conds.append(f"{col} IN ({ph})")
                params.extend(valores)

        for col in self.vuln:
            if col in _COLS_VULN:
                conds.append(f"lower({col}) = 'sim'")
        for col in self.agravos:
            if col in _COLS_AGRAVOS:
                conds.append(f"lower({col}) = 'sim'")

        where = " AND ".join(conds) if conds else "TRUE"
        return where, params

    @property
    def n_anos(self) -> int:
        return max(len(self.anos), 1)

    @property
    def ano_ref(self) -> int:
        """Ano de referência: o mais recente selecionado."""
        return max(self.anos)


def _split(valor: str | None) -> tuple[str, ...]:
    if not valor:
        return ()
    return tuple(v.strip() for v in valor.split(",") if v.strip())


def parse_filtros(
    anos: str | None,
    anos_disponiveis: list[int],
    ufs: str | None = None,
    sexo: str | None = None,
    formas: str | None = None,
    racas: str | None = None,
    entradas: str | None = None,
    hiv: str | None = None,
    vuln: str | None = None,
    agravos: str | None = None,
) -> Filtros:
    """Converte query params crus em Filtros validados."""
    disponiveis = set(anos_disponiveis)
    lista_anos: list[int] = []
    for parte in _split(anos):
        try:
            a = int(parte)
        except ValueError:
            continue
        if a in disponiveis:
            lista_anos.append(a)
    if not lista_anos:
        lista_anos = [max(anos_disponiveis)]

    ufs_validas = tuple(s for s in _split(ufs) if s in UF_VARIANTES)

    return Filtros(
        anos=tuple(sorted(set(lista_anos))),
        ufs=tuple(sorted(ufs_validas)),
        sexo=tuple(sorted(_split(sexo))),
        formas=tuple(sorted(_split(formas))),
        racas=tuple(sorted(_split(racas))),
        entradas=tuple(sorted(_split(entradas))),
        hiv=tuple(sorted(_split(hiv))),
        vuln=tuple(sorted(v for v in _split(vuln) if v in _COLS_VULN)),
        agravos=tuple(sorted(a for a in _split(agravos) if a in _COLS_AGRAVOS)),
    )
