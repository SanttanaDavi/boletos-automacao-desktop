# -*- coding: utf-8 -*-
# Edição pública configurável. Autoria: David Santana.
# Não contém as configurações da instalação original.
import configuracao as config
config.exigir_autorizacao()

from pathlib import Path
from getpass import getpass
import ctypes
import os
import re
import time
from urllib.parse import urlparse

import pandas as pd
import pyautogui
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait



DESKTOP = Path.home() / "Desktop"
PASTA_AUTOMACAO = DESKTOP / "Automacao"
PASTA_AUTOMACAO_COM_ACENTO = DESKTOP / "Automação"
if PASTA_AUTOMACAO_COM_ACENTO.exists():
    PASTA_AUTOMACAO = PASTA_AUTOMACAO_COM_ACENTO

PASTA_SALVAR = config.caminho("DIR_SAIDA")
CAMINHO_PLANILHA = config.caminho("PLANILHA")
CAMINHO_DRIVER = config.caminho("DRIVER")

URL_TASY = config.url_sistema()
USUARIO_TASY = config.valor("USUARIO")

COLUNA_TITULO = "NR_TITULO"
COLUNA_RENOMEAMENTO = "RENOMEAMENTO_BOLETO"
COLUNA_COBRAR = "Cobrar"

TEMPO_PADRAO = 20
TEMPO_REGISTRO = 35
TEMPO_PROCESSAMENTO = 180
TEMPO_DOWNLOAD = 180

COORD_LOTE_FILTRO = (616, 450)
COORD_ABRIR_FILTRO_TITULO = (1095, 536)
COORD_CAMPO_TITULO = (970, 520)
COORD_LINHA_RESULTADO = (1030, 380)


def log(mensagem):
    print(time.strftime("[%H:%M:%S] ") + mensagem, flush=True)


class ErroTitulo(RuntimeError):
    def __init__(self, mensagem, pode_continuar=False):
        super().__init__(mensagem)
        self.pode_continuar = pode_continuar


def garantir_tasy_ativo(navegador):
    """Bloqueia automacao se o foco saiu do Tasy ou a aba navegou para outro site."""
    try:
        url = navegador.current_url
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        tamanho = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        titulo_janela = ctypes.create_unicode_buffer(tamanho + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, titulo_janela, tamanho + 1)
        url_host = (urlparse(url).hostname or "").lower()
        janela_ativa = titulo_janela.value.lower()
    except Exception as erro:
        raise RuntimeError(f"Nao foi possivel confirmar que o Tasy esta ativo: {erro}") from erro

    if url_host != config.host_sistema() or "tasy" not in janela_ativa:
        raise RuntimeError(
            "Execucao interrompida por seguranca: o Tasy nao esta em primeiro plano. "
            "Nenhuma acao sera enviada para outra janela."
        )


def aguardar_tasy_voltar(navegador, timeout=90):
    """Depois de uma autorizacao no terminal, espera o operador retornar ao Tasy."""
    prazo = time.time() + timeout
    while time.time() < prazo:
        try:
            garantir_tasy_ativo(navegador)
            return True
        except RuntimeError:
            time.sleep(0.5)
    return False


def perguntar_se_continua(navegador, titulo, erro):
    log(f"Falha segura antes da impressao do titulo {titulo}: {erro}")
    resposta = input(
        f"O boleto do titulo {titulo} nao chegou a ser impresso. Confira a tela do Tasy. "
        "Deseja pular este titulo e tentar o proximo? (S/N): "
    ).strip().upper()
    if resposta != "S":
        return False

    log("Autorizacao recebida. Retorne ao Tasy; aguardarei ate 90 segundos antes de continuar.")
    if not aguardar_tasy_voltar(navegador):
        log("Tasy nao voltou ao primeiro plano. Execucao interrompida sem avancar.")
        return False
    return True


def clicar_tasy(navegador, *args, **kwargs):
    garantir_tasy_ativo(navegador)
    pyautogui.click(*args, **kwargs)


def pressionar_tasy(navegador, *args, **kwargs):
    garantir_tasy_ativo(navegador)
    pyautogui.press(*args, **kwargs)


def atalho_tasy(navegador, *args, **kwargs):
    garantir_tasy_ativo(navegador)
    pyautogui.hotkey(*args, **kwargs)


def digitar_tasy(navegador, texto, **kwargs):
    intervalo = kwargs.get("interval", 0)
    for caractere in str(texto):
        garantir_tasy_ativo(navegador)
        pyautogui.write(caractere, interval=interval)


def criar_navegador():
    PASTA_SALVAR.mkdir(parents=True, exist_ok=True)

    options = webdriver.EdgeOptions()
    prefs = {
        "plugins.always_open_pdf_externally": True,
        "download.default_directory": str(PASTA_SALVAR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(str(CAMINHO_DRIVER))
    navegador = webdriver.Edge(service=service, options=options)
    navegador.maximize_window()
    return navegador


def validar_arquivos():
    erros = []
    if not CAMINHO_DRIVER.exists():
        erros.append(f"Driver nao encontrado: {CAMINHO_DRIVER}")
    if not CAMINHO_PLANILHA.exists():
        erros.append(f"Planilha nao encontrada: {CAMINHO_PLANILHA}")
    if erros:
        raise FileNotFoundError("\n".join(erros))


def carregar_planilha():
    df = pd.read_excel(CAMINHO_PLANILHA)
    faltando = [
        c for c in (COLUNA_TITULO, COLUNA_RENOMEAMENTO, COLUNA_COBRAR)
        if c not in df.columns
    ]
    if faltando:
        raise ValueError("Coluna(s) ausente(s) na planilha: " + ", ".join(faltando))

    
    
    df[COLUNA_COBRAR] = df[COLUNA_COBRAR].fillna("").astype(str).str.strip().str.upper()
    total = len(df)
    df = df[df[COLUNA_COBRAR] == "SIM"].copy()
    df = df.dropna(subset=[COLUNA_TITULO, COLUNA_RENOMEAMENTO]).copy()
    if df.empty:
        raise ValueError(
            "Nao ha titulos liberados. Confira se a coluna Cobrar esta como SIM "
            "e se NR_TITULO e RENOMEAMENTO_BOLETO estao preenchidos."
        )
    titulos = df[COLUNA_TITULO].map(titulo_como_texto)
    if titulos.duplicated().any():
        repetidos = titulos[titulos.duplicated(keep=False)].unique().tolist()
        raise ValueError("Titulo repetido na planilha; processamento bloqueado: " + ", ".join(repetidos))
    nomes = df[COLUNA_RENOMEAMENTO].map(nome_arquivo_seguro).str.casefold()
    if nomes.duplicated().any():
        repetidos = nomes[nomes.duplicated(keep=False)].unique().tolist()
        raise ValueError("Nome de PDF repetido na planilha; processamento bloqueado: " + ", ".join(repetidos))
    log(f"Planilha central carregada: {total} linhas; {len(df)} titulo(s) liberado(s) com Cobrar = SIM.")
    return df


def login(navegador, wait, senha):
    navegador.get(URL_TASY)
    garantir_tasy_ativo(navegador)
    navegador.execute_script("document.body.style.zoom='0.75'")

    garantir_tasy_ativo(navegador)
    wait.until(EC.element_to_be_clickable((By.ID, "loginUsername"))).send_keys(USUARIO_TASY)
    garantir_tasy_ativo(navegador)
    wait.until(EC.element_to_be_clickable((By.ID, "loginPassword"))).send_keys(senha + Keys.ENTER)
    time.sleep(5)


def acionar_filtro(navegador):
    garantir_tasy_ativo(navegador)
    ActionChains(navegador).key_down(Keys.CONTROL).key_down(Keys.ALT).send_keys("f").key_up(Keys.ALT).key_up(Keys.CONTROL).perform()


def preencher_campo_por_coordenada(navegador, x, y, texto, enter=True):
    clicar_tasy(navegador, x=x, y=y)
    time.sleep(0.2)
    atalho_tasy(navegador, "ctrl", "a")
    pressionar_tasy(navegador, "backspace")
    digitar_tasy(navegador, texto, interval=0.04)
    if enter:
        pressionar_tasy(navegador, "enter")


def abrir_lote_inicial(navegador, wait, lote):
    garantir_tasy_ativo(navegador)
    log("Aguardando texto 'Cobrança escritural' aparecer na tela...")

    try:
        elemento_cobranca = WebDriverWait(navegador, 60).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[contains(text(), "Cobrança escritural")]')
            )
        )
    except TimeoutException:
        raise RuntimeError("Texto 'Cobrança escritural' não apareceu em 60 segundos.")

    garantir_tasy_ativo(navegador)
    log("Tela carregada. Garantindo foco na página...")

    try:
        elemento_cobranca.click()
    except Exception:
        garantir_tasy_ativo(navegador)
        navegador.find_element(By.TAG_NAME, "body").click()
    time.sleep(0.5)

    log("Abrindo filtro com Ctrl+Alt+F...")
    atalho_tasy(navegador, "ctrl", "alt", "f")
    time.sleep(2)

    log(f"Clicando no campo do lote em {COORD_LOTE_FILTRO}...")
    clicar_tasy(navegador, *COORD_LOTE_FILTRO)
    time.sleep(0.5)

    log(f"Digitando lote '{lote}'...")
    for digito in lote:
        pressionar_tasy(navegador, digito)
        time.sleep(0.12)

    time.sleep(0.4)

    pressionar_tasy(navegador, "enter")
    log("ENTER enviado. Aguardando resultado do filtro...")
    time.sleep(4)

    try:
        boleto = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="datagrid"]/div[4]/div[3]/div/div[1]/div[8]/div')
        ))
        garantir_tasy_ativo(navegador)
        texto_antes = navegador.find_element(By.TAG_NAME, "body").text
        ActionChains(navegador).double_click(boleto).perform()
        try:
            WebDriverWait(navegador, TEMPO_PADRAO).until(
                lambda driver: (garantir_tasy_ativo(driver) is None)
                and driver.find_element(By.TAG_NAME, "body").text != texto_antes
            )
        except TimeoutException as erro:
            raise RuntimeError(
                f"O lote {lote} foi selecionado, mas nao confirmei que a tela abriu. "
                "A rotina foi interrompida antes de digitar qualquer titulo."
            ) from erro
        garantir_tasy_ativo(navegador)
        log("Lote inicial aberto com sucesso.")
    except TimeoutException:
        raise RuntimeError("Linha do lote não encontrada após o filtro. Verifique o XPath do datagrid.")


def fechar_downloads(navegador):
    garantir_tasy_ativo(navegador)
    navegador.execute_script("""
        document.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'j', keyCode: 74, ctrlKey: true, bubbles: true
        }));
    """)


def esperar_titulo_carregar(navegador, titulo, timeout=TEMPO_REGISTRO):
    titulo = str(titulo)

    def titulo_apareceu(driver):
        garantir_tasy_ativo(driver)
        texto_tela = driver.find_element(By.TAG_NAME, "body").text
        return "Registros:" in texto_tela and "1 - 1 de 1" in texto_tela and titulo in texto_tela

    try:
        WebDriverWait(navegador, timeout).until(titulo_apareceu)
        return True
    except TimeoutException:
        return False


def nome_arquivo_seguro(nome):
    nome = str(nome).strip()
    nome = re.sub(r'[<>:"/\\|?*]+', "_", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    if not nome.lower().endswith(".pdf"):
        nome += ".pdf"
    return nome


def titulo_como_texto(valor):
    if pd.isna(valor):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def listar_arquivos_download():
    return [
        arquivo for arquivo in PASTA_SALVAR.iterdir()
        if arquivo.is_file()
    ]


def listar_pdfs_prontos():
    return [
        arquivo for arquivo in listar_arquivos_download()
        if arquivo.suffix.lower() == ".pdf"
        and not arquivo.name.lower().endswith((".crdownload", ".tmp"))
    ]


def verificar_sem_download_pendente():
    pendentes = [
        arquivo.name for arquivo in listar_arquivos_download()
        if arquivo.name.lower().endswith((".crdownload", ".tmp", ".part"))
    ]
    if pendentes:
        raise RuntimeError(
            "Ha download anterior ainda em andamento. Para evitar associar um boleto ao titulo errado, "
            "a rotina foi interrompida: " + ", ".join(pendentes)
        )


def assinatura_arquivo(arquivo):
    try:
        info = arquivo.stat()
        return (str(arquivo.resolve()).lower(), info.st_size, info.st_mtime)
    except FileNotFoundError:
        return (str(arquivo.resolve()).lower(), -1, -1)


def aguardar_pdf_novo(navegador, arquivos_antes, timeout=TEMPO_DOWNLOAD):
    prazo = time.time() + timeout
    caminhos_antes = {str(arquivo.resolve()).lower() for arquivo in arquivos_antes}
    assinaturas_antes = {assinatura_arquivo(arquivo) for arquivo in arquivos_antes}

    while time.time() < prazo:
        garantir_tasy_ativo(navegador)
        candidatos = []
        for arquivo in listar_pdfs_prontos():
            caminho = str(arquivo.resolve()).lower()
            if caminho not in caminhos_antes or assinatura_arquivo(arquivo) not in assinaturas_antes:
                candidatos.append(arquivo)

        if candidatos:
            fim_estabilizacao = time.time() + 2
            while time.time() < fim_estabilizacao:
                garantir_tasy_ativo(navegador)
                time.sleep(0.25)
            candidatos = []
            for arquivo in listar_pdfs_prontos():
                caminho = str(arquivo.resolve()).lower()
                if caminho not in caminhos_antes or assinatura_arquivo(arquivo) not in assinaturas_antes:
                    candidatos.append(arquivo)
            if len(candidatos) != 1:
                raise ErroTitulo(
                    f"Foram detectados {len(candidatos)} PDFs possiveis para o titulo atual. "
                    "Nao vou renomear um arquivo sem associacao segura.",
                    pode_continuar=False,
                )
            return candidatos[0]

        time.sleep(0.5)

    return None


def esperar_arquivo_estavel(navegador, arquivo, tentativas=80):
    tamanho_anterior = -1
    for _ in range(tentativas):
        garantir_tasy_ativo(navegador)
        time.sleep(0.5)
        try:
            tamanho_atual = arquivo.stat().st_size
        except FileNotFoundError:
            return False
        if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
            return True
        tamanho_anterior = tamanho_atual
    return False


def abrir_impressao(navegador, wait):
    clicar_tasy(navegador, *COORD_LINHA_RESULTADO, button="right")
    garantir_tasy_ativo(navegador)
    imprimir = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="popupViewPort"]/li[8]/div[3]')))
    garantir_tasy_ativo(navegador)
    imprimir.click()
    time.sleep(1)
    garantir_tasy_ativo(navegador)
    ActionChains(navegador).send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.ENTER).perform()

    
    try:
        confirmar = WebDriverWait(navegador, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Confirmar"]'))
        )
        garantir_tasy_ativo(navegador)
        confirmar.click()
        log("Modal de confirmação de impressão confirmado.")
    except TimeoutException:
        log("Modal de confirmação não apareceu — continuando mesmo assim.")


def esperar_processamento(navegador):
    garantir_tasy_ativo(navegador)
    try:
        def processamento_apareceu(driver):
            garantir_tasy_ativo(driver)
            return EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "Processando")]'))(driver)

        WebDriverWait(navegador, 10).until(processamento_apareceu)
        log("Processando no Tasy...")
        def processamento_terminou(driver):
            garantir_tasy_ativo(driver)
            return EC.invisibility_of_element_located((By.XPATH, '//*[contains(text(), "Processando")]'))(driver)

        WebDriverWait(navegador, TEMPO_PROCESSAMENTO).until(processamento_terminou)
        log("Processamento concluido.")
    except TimeoutException:
        log("Aviso: nao consegui confirmar o fim do processamento; continuando pela espera do PDF.")


def processar_titulo(navegador, wait, titulo, nome_final):
    garantir_tasy_ativo(navegador)
    fechar_downloads(navegador)

    destino = PASTA_SALVAR / nome_final
    log(f"Iniciando titulo {titulo}.")

    clicar_tasy(navegador, *COORD_ABRIR_FILTRO_TITULO)
    acionar_filtro(navegador)
    time.sleep(1)
    preencher_campo_por_coordenada(navegador, *COORD_CAMPO_TITULO, titulo)

    if not esperar_titulo_carregar(navegador, titulo):
        log(f"Titulo {titulo} demorou demais para carregar. Pulando.")
        pressionar_tasy(navegador, "esc")
        raise ErroTitulo(
            f"O titulo {titulo} nao foi confirmado na tela antes da impressao.",
            pode_continuar=True,
        )

    log(f"Titulo {titulo} carregado.")

    verificar_sem_download_pendente()
    arquivos_antes = listar_arquivos_download()
    abrir_impressao(navegador, wait)
    esperar_processamento(navegador)

    log(f"Aguardando PDF do titulo {titulo}.")
    arquivo_novo = aguardar_pdf_novo(navegador, arquivos_antes)

    if not arquivo_novo:
        raise ErroTitulo(
            f"PDF nao encontrado para o titulo {titulo} apos solicitar a impressao.",
            pode_continuar=False,
        )

    if not esperar_arquivo_estavel(navegador, arquivo_novo):
        raise ErroTitulo(
            f"PDF do titulo {titulo} nao estabilizou; a associacao do proximo boleto nao e segura.",
            pode_continuar=False,
        )

    with arquivo_novo.open("rb") as pdf:
        if pdf.read(5) != b"%PDF-":
            raise ErroTitulo(
                f"O arquivo recebido para o titulo {titulo} nao e um PDF valido.",
                pode_continuar=False,
            )

    
    arquivo_novo.replace(destino)
    with destino.open("rb") as pdf:
        if pdf.read(5) != b"%PDF-":
            raise RuntimeError(f"Falha ao confirmar o PDF salvo para o titulo {titulo}.")
    log(f"Renomeado: {destino.name}")

    pressionar_tasy(navegador, "esc")
    time.sleep(0.5)
    return True


def main():
    validar_arquivos()
    df = carregar_planilha()
    print(
        "\nAntes de iniciar os boletos, o lote precisa estar criado e registrado no banco.\n"
        "Informe o número do lote para continuar. Se ainda precisar gerá-lo, deixe o campo vazio;\n"
        "a rotina será pausada sem abrir o Tasy.\n"
    )
    lote = input("Número do lote: ").strip()
    if not lote:
        log("Execução pausada: nenhum lote informado. Gere e registre o lote, depois inicie novamente.")
        return
    if not lote.isdigit():
        log("Execução cancelada: o lote deve conter apenas números. Nenhum boleto foi processado.")
        return

    senha_tasy = getpass("Digite a senha do Tasy (nao sera exibida): ")
    if not senha_tasy:
        raise ValueError("A senha do Tasy nao foi informada.")

    navegador = None
    sucesso = 0
    falhas = []

    try:
        navegador = criar_navegador()
        wait = WebDriverWait(navegador, TEMPO_PADRAO)

        login(navegador, wait, senha_tasy)
        abrir_lote_inicial(navegador, wait, lote)

        for _, row in df.iterrows():
            titulo = titulo_como_texto(row[COLUNA_TITULO])
            nome_final = nome_arquivo_seguro(row[COLUNA_RENOMEAMENTO])

            if not titulo:
                falhas.append("(titulo vazio)")
                log("Rotina interrompida: titulo vazio na planilha; os proximos registros nao serao processados.")
                break

            try:
                if processar_titulo(navegador, wait, titulo, nome_final):
                    sucesso += 1
                else:
                    falhas.append(titulo)
                    log("Rotina interrompida: esta etapa nao foi concluida; os proximos titulos nao serao processados.")
                    break
            except ErroTitulo as erro:
                falhas.append(titulo)
                if erro.pode_continuar and perguntar_se_continua(navegador, titulo, erro):
                    continue
                log("Rotina interrompida para impedir que um arquivo seja associado ao titulo errado.")
                break
            except Exception as erro:
                log(f"ERRO no titulo {titulo}; interrompendo para nao avançar em uma tela inesperada: {erro}")
                falhas.append(titulo)
                break

        log(f"Finalizado. Baixados com sucesso: {sucesso}. Falhas: {len(falhas)}.")
        if falhas:
            log("Titulos com falha: " + ", ".join(falhas))

    finally:
        if navegador:
            navegador.quit()


if __name__ == "__main__":
    main()
