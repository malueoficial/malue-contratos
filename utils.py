"""Helpers do gerador de contrato MaLuê.

- Conversão de valor numérico para extenso (BRL).
- Conversão de data para extenso em português.
- Validação e formatação de CPF/CNPJ.
- Helpers de duração da apresentação.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


# ============================================================
# Valor
# ============================================================
def parse_valor(texto: str) -> Decimal | None:
    """Aceita '18000', '18000,00', '18.000,00', 'R$ 18.000,00', etc.

    Retorna Decimal ou None se inválido.
    """
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    # Remove R$, espaços e qualquer caractere que não seja dígito, ponto ou vírgula
    t = re.sub(r"[^0-9,.\-]", "", t)
    if not t:
        return None
    # Caso brasileiro: tem vírgula → vírgula é decimal, ponto é milhar
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        v = Decimal(t)
    except InvalidOperation:
        return None
    if v <= 0:
        return None
    return v


def formata_valor_brl(valor: Decimal) -> str:
    """Decimal(18000) -> 'R$ 18.000,00'."""
    inteiro, _, centavos = f"{valor:.2f}".partition(".")
    inteiro_fmt = ""
    while len(inteiro) > 3:
        inteiro_fmt = "." + inteiro[-3:] + inteiro_fmt
        inteiro = inteiro[:-3]
    inteiro_fmt = inteiro + inteiro_fmt
    return f"R$ {inteiro_fmt},{centavos}"


_UNIDADES = [
    "zero", "um", "dois", "três", "quatro", "cinco",
    "seis", "sete", "oito", "nove", "dez", "onze",
    "doze", "treze", "quatorze", "quinze", "dezesseis",
    "dezessete", "dezoito", "dezenove",
]
_DEZENAS = [
    "", "", "vinte", "trinta", "quarenta", "cinquenta",
    "sessenta", "setenta", "oitenta", "noventa",
]
_CENTENAS = [
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
    "seiscentos", "setecentos", "oitocentos", "novecentos",
]


def _grupo_extenso(n: int) -> str:
    """Converte número de 0 a 999 para extenso em português."""
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    partes = []
    c = n // 100
    resto = n % 100
    if c > 0:
        partes.append(_CENTENAS[c])
    if resto > 0:
        if resto < 20:
            partes.append(_UNIDADES[resto])
        else:
            d = resto // 10
            u = resto % 10
            if u == 0:
                partes.append(_DEZENAS[d])
            else:
                partes.append(f"{_DEZENAS[d]} e {_UNIDADES[u]}")
    return " e ".join(partes)


def _inteiro_extenso(n: int) -> str:
    """Converte inteiro >= 0 para extenso. Suporta até bilhões."""
    if n == 0:
        return "zero"

    grupos = []
    bilhoes = n // 1_000_000_000
    n %= 1_000_000_000
    milhoes = n // 1_000_000
    n %= 1_000_000
    milhares = n // 1_000
    unidades = n % 1_000

    if bilhoes > 0:
        palavra = "bilhão" if bilhoes == 1 else "bilhões"
        if bilhoes == 1:
            grupos.append(f"um {palavra}")
        else:
            grupos.append(f"{_grupo_extenso(bilhoes)} {palavra}")
    if milhoes > 0:
        palavra = "milhão" if milhoes == 1 else "milhões"
        if milhoes == 1:
            grupos.append(f"um {palavra}")
        else:
            grupos.append(f"{_grupo_extenso(milhoes)} {palavra}")
    if milhares > 0:
        if milhares == 1:
            grupos.append("mil")
        else:
            grupos.append(f"{_grupo_extenso(milhares)} mil")
    if unidades > 0:
        grupos.append(_grupo_extenso(unidades))

    # Liga os grupos com vírgulas, e o último com " e " conforme gramática
    if len(grupos) == 1:
        return grupos[0]
    return ", ".join(grupos[:-1]) + " e " + grupos[-1]


def valor_por_extenso(valor: Decimal) -> str:
    """Decimal('18000') -> 'dezoito mil reais'.

    Formato: 'X reais', 'X real', 'X reais e Y centavos', 'um centavo',
    'Y centavos'.
    """
    inteiro_str, _, centavos_str = f"{valor:.2f}".partition(".")
    inteiro = int(inteiro_str)
    centavos = int(centavos_str)

    partes = []
    if inteiro > 0:
        ext = _inteiro_extenso(inteiro)
        unidade = "real" if inteiro == 1 else "reais"
        partes.append(f"{ext} {unidade}")
    if centavos > 0:
        ext_c = _inteiro_extenso(centavos)
        unidade_c = "centavo" if centavos == 1 else "centavos"
        partes.append(f"{ext_c} {unidade_c}")
    if not partes:
        return "zero reais"
    return " e ".join(partes)


# ============================================================
# Data
# ============================================================
def data_por_extenso(d: date | datetime) -> str:
    """date(2026, 10, 3) -> '03 de outubro de 2026'."""
    return f"{d.day:02d} de {MESES_PT[d.month]} de {d.year}"


def data_compacta(d: date | datetime) -> str:
    """date(2026, 10, 3) -> '03-10-2026'."""
    return f"{d.day:02d}-{d.month:02d}-{d.year}"


# ============================================================
# CPF / CNPJ
# ============================================================
def _so_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def valida_cpf(cpf: str) -> bool:
    digitos = _so_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    # Primeiro dígito verificador
    soma = sum(int(digitos[i]) * (10 - i) for i in range(9))
    dv1 = (soma * 10) % 11
    if dv1 == 10:
        dv1 = 0
    if dv1 != int(digitos[9]):
        return False
    # Segundo dígito verificador
    soma = sum(int(digitos[i]) * (11 - i) for i in range(10))
    dv2 = (soma * 10) % 11
    if dv2 == 10:
        dv2 = 0
    return dv2 == int(digitos[10])


def valida_cnpj(cnpj: str) -> bool:
    digitos = _so_digitos(cnpj)
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    soma1 = sum(int(digitos[i]) * pesos1[i] for i in range(12))
    dv1 = soma1 % 11
    dv1 = 0 if dv1 < 2 else 11 - dv1
    if dv1 != int(digitos[12]):
        return False
    soma2 = sum(int(digitos[i]) * pesos2[i] for i in range(13))
    dv2 = soma2 % 11
    dv2 = 0 if dv2 < 2 else 11 - dv2
    return dv2 == int(digitos[13])


def formata_cpf(cpf: str) -> str:
    d = _so_digitos(cpf)
    if len(d) != 11:
        return cpf
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def formata_cnpj(cnpj: str) -> str:
    d = _so_digitos(cnpj)
    if len(d) != 14:
        return cnpj
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def detecta_e_formata_documento(doc: str) -> tuple[str, str] | None:
    """Detecta CPF ou CNPJ, valida e devolve (tipo, formatado).

    Retorna None se inválido.
    """
    d = _so_digitos(doc)
    if len(d) == 11:
        return ("CPF", formata_cpf(d)) if valida_cpf(d) else None
    if len(d) == 14:
        return ("CNPJ", formata_cnpj(d)) if valida_cnpj(d) else None
    return None


# ============================================================
# Duração
# ============================================================
_NUMEROS_FEMININO = {
    1: "uma", 2: "duas", 3: "três", 4: "quatro", 5: "cinco",
    6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez",
}

_NUMEROS_MINUTOS = {
    5: "cinco", 10: "dez", 15: "quinze", 20: "vinte", 25: "vinte e cinco",
    30: "trinta", 35: "trinta e cinco", 40: "quarenta", 45: "quarenta e cinco",
    50: "cinquenta", 55: "cinquenta e cinco",
}


def _num_extenso_minutos(m: int) -> str:
    if m in _NUMEROS_MINUTOS:
        return _NUMEROS_MINUTOS[m]
    return _inteiro_extenso(m)


def _num_extenso_horas(h: int) -> str:
    if h in _NUMEROS_FEMININO:
        return _NUMEROS_FEMININO[h]
    return _inteiro_extenso(h)


def duracao_extensos(horas: int, minutos: int) -> tuple[str, str, str]:
    """Devolve (numerico, extenso_completo, extenso_curto).

    Exemplos:
      (2, 0) -> ("2h", "2 (duas) horas contínuas", "2 (duas) horas")
      (1, 40) -> ("1h40", "1 (uma) hora e 40 (quarenta) minutos contínuos",
                  "1 (uma) hora e 40 (quarenta) minutos")
    """
    if horas < 0 or minutos < 0 or minutos >= 60:
        raise ValueError("Duração inválida")

    if minutos == 0:
        numerico = f"{horas}h"
    else:
        numerico = f"{horas}h{minutos:02d}"

    # Parte de horas
    if horas == 0:
        partes_completo = []
        partes_curto = []
    else:
        palavra_h = "hora" if horas == 1 else "horas"
        extenso_h = _num_extenso_horas(horas)
        partes_completo = [f"{horas} ({extenso_h}) {palavra_h}"]
        partes_curto = list(partes_completo)

    # Parte de minutos
    if minutos > 0:
        palavra_m = "minuto" if minutos == 1 else "minutos"
        extenso_m = _num_extenso_minutos(minutos)
        partes_completo.append(f"{minutos} ({extenso_m}) {palavra_m}")
        partes_curto.append(f"{minutos} ({extenso_m}) {palavra_m}")

    extenso_completo = " e ".join(partes_completo) + " contínuos"
    extenso_curto = " e ".join(partes_curto)

    # Caso especial: só horas → "contínuas" no feminino
    if minutos == 0 and horas > 0:
        extenso_completo = " e ".join(partes_completo) + " contínuas"

    return numerico, extenso_completo, extenso_curto


# ============================================================
# Horário do show e palco
# ============================================================
def horario_palco_liberado(hora_inicio: str) -> tuple[str, str]:
    """'23:00' -> ('23:00h', '22:30h').

    Aceita '23h', '23:00', '23:30', etc.
    """
    h = hora_inicio.strip().lower().replace("h", "").replace(" ", "")
    if ":" in h:
        hh_str, mm_str = h.split(":", 1)
    else:
        hh_str, mm_str = h, "00"
    hh = int(hh_str)
    mm = int(mm_str) if mm_str else 0
    inicio_total = hh * 60 + mm
    liberacao_total = inicio_total - 30
    if liberacao_total < 0:
        liberacao_total += 24 * 60
    inicio_fmt = f"{hh:02d}:{mm:02d}h"
    libh = liberacao_total // 60
    libm = liberacao_total % 60
    liberacao_fmt = f"{libh:02d}:{libm:02d}h"
    return inicio_fmt, liberacao_fmt
