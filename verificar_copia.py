"""Conferência textual local: não importa nem executa o adaptador."""
import ast
from pathlib import Path
import re

ARQUIVOS = ("automacao.py", "configuracao.py", "adaptador_legado.py")

def main():
    raiz = Path(__file__).resolve().parent
    erros = []
    for nome in ARQUIVOS:
        texto = (raiz / nome).read_text(encoding="utf-8-sig")
        try:
            arvore = ast.parse(texto, filename=nome)
        except SyntaxError as erro:
            erros.append((nome, erro.lineno, "sintaxe"))
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign) and isinstance(no.value, ast.Constant) and isinstance(no.value.value, str):
                nomes = [alvo.id for alvo in no.targets if isinstance(alvo, ast.Name)]
                if any(re.search(r"senha|password|token|secret", chave, re.I) for chave in nomes) and no.value.value:
                    erros.append((nome, no.lineno, "credencial literal"))
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                if re.search(r"[A-Za-z]:[\\/](?:Users|Windows|Program Files)", no.value):
                    erros.append((nome, no.lineno, "caminho de máquina"))
    for nome, linha, tipo in erros:
        print(f"REVISAR: {nome}:{linha}: {tipo}")
    if not erros:
        print("Sintaxe e padrões limitados conferidos; nenhum código do app foi executado.")
        print("Esta conferência não substitui revisão de privacidade nem teste funcional.")
    return 1 if erros else 0

if __name__ == "__main__":
    raise SystemExit(main())
