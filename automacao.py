"""Entrada sem efeitos por padrão: não importa o adaptador na conferência."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import runpy

def main():
    parser = argparse.ArgumentParser(description="Exemplo público: conferência por padrão, execução somente após revisão local.")
    parser.add_argument("--executar", action="store_true", help="Carrega o adaptador legado após configuração e autorização explícitas.")
    args = parser.parse_args()
    if not args.executar:
        print("MODO DE CONFERÊNCIA: nenhum navegador, planilha, e-mail ou automação foi iniciado.")
        print("Leia README.md, PRIVACIDADE.md e LIMITACOES.md antes de adaptar o exemplo.")
        return 0
    from configuracao import exigir_autorizacao
    exigir_autorizacao()
    runpy.run_path(str(Path(__file__).with_name("adaptador_legado.py")), run_name="__main__")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
