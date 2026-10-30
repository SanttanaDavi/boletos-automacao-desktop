"""Configuração local e travas para exemplos públicos. Não contém credenciais."""
from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlsplit
from email.utils import getaddresses

_ENV_PREFIX = "AUTOMACAO_"
_ENVIADOS = 0

def exigir_autorizacao():
    """Importar o adaptador legado não deve iniciar uma automação sem consentimento."""
    if os.environ.get(_ENV_PREFIX + "CONFIRMAR_EXECUCAO") != "EU_REVISEI":
        raise SystemExit("Execução bloqueada. Leia o README e use o iniciador em modo de conferência.")

def valor(chave):
    nome = _ENV_PREFIX + chave
    conteudo = os.environ.get(nome, "").strip()
    padroes = {"NOME_REMETENTE": "Equipe de exemplo", "OBSERVACAO": "Exemplo fictício para validação"}
    if not conteudo:
        conteudo = padroes.get(chave, "")
    if not conteudo:
        raise ValueError("Configuração obrigatória ausente: " + nome)
    if "\x00" in conteudo or "\r" in conteudo or "\n" in conteudo:
        raise ValueError("Configuração contém caractere não permitido: " + nome)
    return conteudo

def caminho(chave):
    if chave == "ASSINATURA" and not os.environ.get(_ENV_PREFIX + chave, "").strip():
        return ""
    texto = valor(chave)
    destino = Path(texto).expanduser().resolve()
    if chave in {"DRIVER", "PLANILHA", "PLANILHA_DESCRITIVOS", "PLANILHA_NOTAS", "ASSINATURA"}:
        if not destino.is_file():
            raise ValueError("Arquivo configurado ausente: AUTOMACAO_" + chave)
    elif chave.startswith("DIR_"):
        if not destino.is_dir():
            raise ValueError("Pasta configurada ausente: AUTOMACAO_" + chave)
    elif not destino.parent.is_dir():
        raise ValueError("Pasta de destino ausente: AUTOMACAO_" + chave)
    return str(destino)

def url_sistema():
    url = valor("URL")
    partes = urlsplit(url)
    if partes.scheme != "https" or not partes.hostname or partes.username or partes.password:
        raise ValueError("Configure uma URL HTTPS, sem credenciais no endereço.")
    if partes.hostname.endswith(".invalid") or partes.hostname in {"localhost", "127.0.0.1"}:
        raise ValueError("O endereço de exemplo não é um sistema configurado.")
    return url

def host_sistema():
    return urlsplit(url_sistema()).hostname.lower()

class _CapturaDesativada:
    def save(self, *_args, **_kwargs):
        return None

def captura_desativada(*_args, **_kwargs):
    """A edição pública não captura telas nem grava imagens de diagnóstico."""
    return _CapturaDesativada()

def enviar_piloto(smtp, mensagem):
    """Somente autoenvio explícito, no máximo três mensagens por execução."""
    global _ENVIADOS
    if os.environ.get(_ENV_PREFIX + "ENVIAR_EMAIL") != "PILOTO_PROPRIO_EMAIL":
        raise RuntimeError("Envio bloqueado: somente piloto explícito para o próprio remetente.")
    remetente = valor("EMAIL_REMETENTE").casefold()
    de = getaddresses(mensagem.get_all("From", []))
    para = getaddresses(sum((mensagem.get_all(campo, []) for campo in ("To", "Cc", "Bcc")), []))
    if len(de) != 1 or de[0][1].casefold() != remetente:
        raise ValueError("O remetente deve ser a própria conta autenticada.")
    if not para or any(endereco.casefold() != remetente for _, endereco in para):
        raise ValueError("O piloto não envia para terceiros, inclusive em cópia.")
    if _ENVIADOS >= 3:
        raise RuntimeError("Limite de três mensagens atingido.")
    _ENVIADOS += 1  # Não liberar nova tentativa automática após resultado incerto.
    smtp.send_message(mensagem)
