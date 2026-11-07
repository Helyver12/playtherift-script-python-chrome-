
import os
import re
import json
import time
import traceback
import unicodedata

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL = "https://playtherift.com"

TOTAL_CONTAS = 4
INTERVALO_COLETA = 60

CHROME_PATH = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)

PROFILE_BASE = r"C:\SeleniumChrome"

DESTINATARIO = "Hellboy"

RESERVA_OURO = 100

TIMEOUT = 15

DIRETORIO_SCRIPT = os.path.dirname(
    os.path.abspath(__file__)
)

ARQUIVO_TRANSFERENCIAS = os.path.join(
    DIRETORIO_SCRIPT,
    "transferencias_ouro.json"
)

DRIVERS = {}


# ============================================================
# UTILITÁRIOS
# ============================================================

def normalizar(texto):

    texto = unicodedata.normalize(
        "NFKD",
        str(texto)
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    return texto.lower().strip()


def aguardar(segundos=1):
    time.sleep(segundos)


def carregar_log():

    if not os.path.exists(ARQUIVO_TRANSFERENCIAS):
        return {}

    with open(
        ARQUIVO_TRANSFERENCIAS,
        "r",
        encoding="utf-8"
    ) as arquivo:

        dados = json.load(arquivo)

        if not isinstance(dados, dict):
            raise ValueError(
                "Arquivo de transferências inválido."
            )

        return dados


def salvar_log(dados):

    temporario = ARQUIVO_TRANSFERENCIAS + ".tmp"

    with open(
        temporario,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

        arquivo.flush()
        os.fsync(arquivo.fileno())

    os.replace(
        temporario,
        ARQUIVO_TRANSFERENCIAS
    )


def registrar_transferencia(conta, status, **informacoes):

    dados = carregar_log()

    chave = f"Conta{conta}"

    registro = dados.get(chave, {})

    registro.update(informacoes)

    registro["status"] = status

    registro["atualizado_em"] = datetime.now().isoformat(
        timespec="seconds"
    )

    dados[chave] = registro

    salvar_log(dados)


# ============================================================
# ALERTA DE LENDÁRIO
# ============================================================

def anunciar_lendario(conta, nome, potencial):

    amarelo = "\033[43m"
    preto = "\033[30m"
    negrito = "\033[1m"
    reset = "\033[0m"

    print("\n")

    print(
        amarelo + preto + negrito
        + "!" * 65
        + reset
    )

    print(
        amarelo + preto + negrito
        + "       ★★★ LENDÁRIO TRAVADO! ★★★       "
        + reset
    )

    print(
        amarelo + preto + negrito
        + f"       CONTA {conta} | {nome}       "
        + reset
    )

    print(
        amarelo + preto + negrito
        + f"       POTENCIAL: {potencial.upper()}       "
        + reset
    )

    print(
        amarelo + preto + negrito
        + "!" * 65
        + reset
    )

    print("\n")


# ============================================================
# CONVERSÃO DE OURO
# ============================================================

def parse_quantia(texto):

    texto = str(texto).strip()
    texto = texto.replace(" ", "")
    texto = texto.replace("\u00a0", "")

    if not texto:
        raise ValueError("Quantidade vazia.")

    multiplicador = 1

    sufixo = texto[-1:].lower()

    if sufixo == "k":
        multiplicador = 1000
        texto = texto[:-1]

    elif sufixo == "m":
        multiplicador = 1000000
        texto = texto[:-1]

    if not texto:
        raise ValueError("Quantidade inválida.")

    if "," in texto and "." in texto:

        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")

        else:
            texto = texto.replace(",", "")

    elif "," in texto:

        partes = texto.split(",")

        if multiplicador == 1 and len(partes[-1]) == 3:
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")

    elif "." in texto:

        partes = texto.split(".")

        if multiplicador == 1 and len(partes[-1]) == 3:
            texto = texto.replace(".", "")

    valor = float(texto) * multiplicador

    return int(valor)


def formatar_ouro(valor):

    return f"{int(valor):,}".replace(",", ".")


# ============================================================
# CONEXÃO E RECUPERAÇÃO DAS CONTAS
# ============================================================

def reconectar_conta(conta):

    profile = os.path.join(
        PROFILE_BASE,
        f"Conta{conta}"
    )

    arquivo_porta = os.path.join(
        profile,
        "DevToolsActivePort"
    )

    if not os.path.exists(arquivo_porta):

        print(
            f"[Conta {conta}] "
            "DevToolsActivePort não encontrado."
        )

        return None

    try:

        with open(
            arquivo_porta,
            "r",
            encoding="utf-8"
        ) as arquivo:

            porta = arquivo.readline().strip()

        if not porta.isdigit():

            print(
                f"[Conta {conta}] Porta de depuração inválida."
            )

            return None

        options = webdriver.ChromeOptions()

        options.binary_location = CHROME_PATH

        options.debugger_address = (
            f"127.0.0.1:{porta}"
        )

        print(
            f"[Conta {conta}] "
            f"Reconectando à porta {porta}..."
        )

        novo_driver = webdriver.Chrome(
            options=options
        )

        novo_driver.execute_script(
            "return document.readyState;"
        )

        DRIVERS[conta] = novo_driver

        print(
            f"[Conta {conta}] "
            "CONEXÃO RECUPERADA COM SUCESSO!"
        )

        return novo_driver

    except Exception as e:

        print(
            f"[Conta {conta}] "
            f"Falha ao recuperar conexão: {e}"
        )

        return None


def obter_driver(conta):

    driver = DRIVERS.get(conta)

    if driver is None:
        return None

    try:

        driver.execute_script(
            "return true;"
        )

        return driver

    except Exception:

        print(
            f"[Conta {conta}] Sessão Selenium perdida."
        )

        DRIVERS.pop(conta, None)

        return reconectar_conta(conta)


def verificar_janelas():

    global DRIVERS

    for conta in range(1, TOTAL_CONTAS + 1):

        driver = DRIVERS.get(conta)

        if driver is None:

            print(
                f"[Conta {conta}] "
                "Tentando recuperar sessão..."
            )

            reconectar_conta(conta)

            continue

        try:

            driver.execute_script(
                "return true;"
            )

        except Exception:

            print(
                f"\n[Conta {conta}] "
                "CONEXÃO COM SELENIUM PERDIDA."
            )

            print(
                f"[Conta {conta}] "
                "Tentando reconectar sem fechar o Chrome..."
            )

            DRIVERS.pop(conta, None)

            novo_driver = reconectar_conta(conta)

            if novo_driver is None:

                print(
                    f"[Conta {conta}] "
                    "Não foi possível recuperar automaticamente."
                )

                print(
                    "A janela do Chrome não será fechada."
                )


# ============================================================
# NAVEGAÇÃO
# ============================================================

def abrir_tela(driver, nome):

    try:

        return driver.execute_script("""
            const nome = arguments[0].trim().toLowerCase();

            const botao = [...document.querySelectorAll(
                'button.nav-item'
            )].find(b =>
                b.textContent.trim().toLowerCase() === nome
            );

            if (!botao) {
                return false;
            }

            botao.click();

            return true;
        """, nome)

    except WebDriverException:

        return False


def esperar_tela(driver, nome, timeout=TIMEOUT):

    inicio = time.time()

    while time.time() - inicio < timeout:

        try:

            ativa = driver.execute_script("""
                const nome = arguments[0].trim().toLowerCase();

                return [...document.querySelectorAll(
                    'button.nav-item'
                )].some(b =>
                    b.textContent.trim().toLowerCase() === nome &&
                    b.getAttribute('aria-pressed') === 'true'
                );
            """, nome)

            if ativa:
                return True

        except WebDriverException:
            pass

        time.sleep(0.2)

    print(
        f"[AVISO] Não foi possível confirmar a tela: {nome}"
    )

    return False


# ============================================================
# FECHAR JANELAS PELO X
# ============================================================

def fechar_janela(driver, nome, conta):

    seletor = (
        f'.fwin[aria-label="{nome}"] '
        'button.fwin-close[aria-label="Fechar janela"]'
    )

    try:

        botoes = driver.find_elements(
            By.CSS_SELECTOR,
            seletor
        )

        janela_aberta = False

        for botao in botoes:

            if not botao.is_displayed():
                continue

            janela_aberta = True

            driver.execute_script(
                "arguments[0].click();",
                botao
            )

            try:

                WebDriverWait(driver, 5).until(
                    lambda d: not any(
                        elemento.is_displayed()
                        for elemento in d.find_elements(
                            By.CSS_SELECTOR,
                            seletor
                        )
                    )
                )

                print(
                    f"[Conta {conta}] "
                    f"Janela {nome} fechada."
                )

                return True

            except TimeoutException:

                print(
                    f"[Conta {conta}] "
                    f"AVISO: não foi possível confirmar "
                    f"o fechamento de {nome}."
                )

                return False

        if not janela_aberta:

            print(
                f"[Conta {conta}] "
                f"Janela {nome} já estava fechada."
            )

            return True

    except Exception as e:

        print(
            f"[Conta {conta}] "
            f"Erro ao fechar {nome}: {e}"
        )

        traceback.print_exc()

    return False


def fechar_janelas_rotina(driver, conta):

    print(
        f"\n[Conta {conta}] Limpando interface do jogo..."
    )

    fechar_janela(
        driver,
        "Mochila",
        conta
    )

    aguardar(0.5)

    fechar_janela(
        driver,
        "Recrutamento",
        conta
    )

    print(
        f"[Conta {conta}] Interface da rotina finalizada."
    )


# ============================================================
# AGUARDAR JOGO
# ============================================================

def aguardar_jogo(driver, conta):

    try:

        WebDriverWait(driver, 30).until(
            lambda d: d.find_elements(
                By.CSS_SELECTOR,
                "button.nav-item"
            )
        )

        print(
            f"[Conta {conta}] Jogo carregado."
        )

        return True

    except TimeoutException:

        print(
            f"\n[Conta {conta}] Interface não apareceu."
        )

        input(
            f"Faça login na Conta {conta}, se necessário, "
            "e pressione ENTER..."
        )

        try:

            WebDriverWait(driver, 120).until(
                lambda d: d.find_elements(
                    By.CSS_SELECTOR,
                    "button.nav-item"
                )
            )

            print(
                f"[Conta {conta}] Login detectado."
            )

            return True

        except TimeoutException:

            print(
                f"[Conta {conta}] Não foi possível confirmar o login."
            )

            return False


# ============================================================
# RECRUTAMENTO
# ============================================================

def recrutar(driver, conta):

    try:

        print(
            f"[Conta {conta}] Abrindo Recrutar..."
        )

        if not abrir_tela(driver, "Recrutar"):

            print(
                "[AVISO] Botão Recrutar não encontrado."
            )

            return

        if not esperar_tela(driver, "Recrutar"):
            return

        aguardar(1)

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            ".rc-card"
        )

        travados = 0

        for card in cards:

            try:

                raridade = normalizar(
                    card.find_element(
                        By.CSS_SELECTOR,
                        ".rc-raridade"
                    ).text
                )

                potencial = normalizar(
                    card.find_element(
                        By.CSS_SELECTOR,
                        ".pot-tag"
                    ).text
                )

                if "lendario" not in raridade:
                    continue

                if not (
                    "excepcional" in potencial
                    or "prodigio" in potencial
                ):
                    continue

                cadeado = card.find_element(
                    By.CSS_SELECTOR,
                    "button.rc-trava"
                )

                aria = (
                    cadeado.get_attribute("aria-label") or ""
                )

                titulo = (
                    cadeado.get_attribute("title") or ""
                )

                if not cadeado.is_enabled():
                    continue

                if normalizar(aria) != "por no cadeado":
                    continue

                if "cheio" in normalizar(titulo):
                    continue

                nome = card.find_element(
                    By.CSS_SELECTOR,
                    ".rc-card-nome"
                ).text

                driver.execute_script(
                    "arguments[0].click();",
                    cadeado
                )

                travados += 1

                print(
                    f"[Conta {conta}] Lendário travado: "
                    f"{nome} | {raridade} | {potencial}"
                )

                anunciar_lendario(
                    conta,
                    nome,
                    potencial
                )

                aguardar(0.3)

            except NoSuchElementException:
                continue

            except WebDriverException as e:

                print(
                    f"[Conta {conta}] Erro em candidato: {e}"
                )

        print(
            f"[Conta {conta}] Recrutamento concluído. "
            f"Novos personagens travados: {travados}"
        )

    except Exception as e:

        print(
            f"[Conta {conta}] Erro no recrutamento: {e}"
        )

        traceback.print_exc()


# ============================================================
# VENDER ITENS DA MOCHILA
# ============================================================

def vender(driver, conta):

    try:

        print(
            f"[Conta {conta}] Abrindo Mochila..."
        )

        if not abrir_tela(driver, "Mochila"):

            print(
                "[AVISO] Botão Mochila não encontrado."
            )

            return

        if not esperar_tela(driver, "Mochila"):
            return

        aguardar(1)

        resultado = driver.execute_script("""
            const botoes = [...document.querySelectorAll('button')];

            const vender = botoes.find(b =>
                /vender tudo/i.test(b.textContent) &&
                !b.disabled &&
                b.offsetWidth > 0 &&
                b.offsetHeight > 0
            );

            if (!vender) {
                return false;
            }

            vender.click();

            return true;
        """)

        if not resultado:

            print(
                f"[Conta {conta}] Botão Vender Tudo não encontrado."
            )

            return

        print(
            f"[Conta {conta}] Vender Tudo clicado."
        )

        aguardar(1)

        confirmado = driver.execute_script("""
            const botoes = [...document.querySelectorAll('button')];

            const confirmar = botoes.find(b =>
                /confirmar.{0,40}vender/i.test(b.textContent) &&
                !b.disabled &&
                b.offsetWidth > 0 &&
                b.offsetHeight > 0
            );

            if (!confirmar) {
                return false;
            }

            confirmar.click();

            return true;
        """)

        if confirmado:

            print(
                f"[Conta {conta}] Venda confirmada."
            )

        else:

            print(
                f"[Conta {conta}] Botão de confirmação "
                "não encontrado."
            )

    except Exception as e:

        print(
            f"[Conta {conta}] Erro ao vender: {e}"
        )

        traceback.print_exc()


# ============================================================
# OBTER SALDO
# ============================================================

def obter_saldo(driver):

    elemento = WebDriverWait(
        driver,
        TIMEOUT
    ).until(
        lambda d: d.find_element(
            By.CSS_SELECTOR,
            'div.coin[title="Ouro"] span.hd'
        )
    )

    texto = elemento.text.strip()

    saldo = parse_quantia(texto)

    if saldo <= 0:

        raise ValueError(
            f"Saldo inválido: {texto}"
        )

    return saldo, texto


# ============================================================
# TRANSFERIR OURO
# ============================================================

def transferir_ouro(driver, conta):

    if conta == 1:

        print(
            "[Conta 1] Conta receptora. "
            "Não realizará transferência."
        )

        return

    chave = f"Conta{conta}"

    try:

        dados = carregar_log()

        registro = dados.get(chave, {})

        status = registro.get("status")

        if status == "confirmed":

            print(
                f"[Conta {conta}] Transferência já confirmada. "
                "Não será repetida."
            )

            return

        if status in (
            "prepared",
            "pending_confirmation",
            "uncertain"
        ):

            print(
                f"[Conta {conta}] Transferência com status "
                f"'{status}'."
            )

            print(
                "Verifique manualmente o histórico do jogo "
                "antes de tentar novamente."
            )

            return

        print(
            f"[Conta {conta}] Preparando transferência..."
        )

        saldo, saldo_original = obter_saldo(driver)

        quantidade = saldo - RESERVA_OURO

        print(
            f"[Conta {conta}] Saldo: {saldo_original}"
        )

        print(
            f"[Conta {conta}] Reserva: {RESERVA_OURO}"
        )

        print(
            f"[Conta {conta}] Valor a enviar: "
            f"{formatar_ouro(quantidade)}"
        )

        if quantidade <= 0:

            print(
                f"[Conta {conta}] Saldo insuficiente."
            )

            return

        if not abrir_tela(driver, "Amigos"):

            print(
                f"[Conta {conta}] Não foi possível abrir Amigos."
            )

            return

        if not esperar_tela(driver, "Amigos"):
            return

        aguardar(1)

        amigos = driver.find_elements(
            By.CSS_SELECTOR,
            ".am-amigo"
        )

        amigo_alvo = None

        for amigo in amigos:

            try:

                nome = amigo.find_element(
                    By.CSS_SELECTOR,
                    ".am-nome"
                ).text.strip()

                primeiro_nome = nome.split("·")[0].strip()

                if normalizar(primeiro_nome) == normalizar(
                    DESTINATARIO
                ):

                    amigo_alvo = amigo
                    break

            except NoSuchElementException:
                continue

        if amigo_alvo is None:

            print(
                f"[Conta {conta}] Amigo {DESTINATARIO} "
                "não encontrado."
            )

            return

        botao_abrir = amigo_alvo.find_element(
            By.XPATH,
            ".//button[contains(normalize-space(.), 'Mandar ouro')]"
        )

        driver.execute_script("""
            arguments[0].scrollIntoView({
                behavior: 'instant',
                block: 'center'
            });

            arguments[0].click();
        """, botao_abrir)

        WebDriverWait(driver, 10).until(
            lambda d: amigo_alvo.find_elements(
                By.CSS_SELECTOR,
                '.am-ouro input[aria-label="Quanto ouro mandar"]'
            )
        )

        aguardar(0.5)

        campo = amigo_alvo.find_element(
            By.CSS_SELECTOR,
            '.am-ouro input[aria-label="Quanto ouro mandar"]'
        )

        campo.click()

        campo.send_keys(
            Keys.CONTROL,
            "a"
        )

        campo.send_keys(
            str(quantidade)
        )

        aguardar(0.7)

        painel = amigo_alvo.find_element(
            By.CSS_SELECTOR,
            ".am-ouro"
        )

        texto_painel = painel.text

        if "15%" not in texto_painel:

            print(
                "[ERRO] A taxa não corresponde a 15%. "
                "Transferência cancelada."
            )

            return

        liquido_elemento = painel.find_element(
            By.CSS_SELECTOR,
            ".gold"
        )

        valor_liquido = liquido_elemento.text.strip()

        print(
            f"[Conta {conta}] Hellboy receberá: "
            f"{valor_liquido}"
        )

        botao_mandar = painel.find_element(
            By.CSS_SELECTOR,
            "button.btn-primary"
        )

        if (
            normalizar(botao_mandar.text) != "mandar"
            or not botao_mandar.is_enabled()
        ):

            print(
                "[ERRO] Botão Mandar indisponível."
            )

            return

        registrar_transferencia(
            conta,
            "prepared",
            destinatario=DESTINATARIO,
            quantidade=quantidade,
            saldo_antes=saldo,
            saldo_texto=saldo_original,
            valor_liquido=valor_liquido
        )

        driver.execute_script(
            "arguments[0].click();",
            botao_mandar
        )

        aguardar(1)

        botoes_confirmacao = painel.find_elements(
            By.CSS_SELECTOR,
            "button.btn-danger"
        )

        if not botoes_confirmacao:

            registrar_transferencia(
                conta,
                "uncertain",
                motivo=(
                    "Confirmação não apareceu após clicar em Mandar."
                )
            )

            print(
                "[ERRO] Confirmação não apareceu. "
                "Verifique manualmente."
            )

            return

        botao_confirmar = botoes_confirmacao[0]

        texto_confirmacao = botao_confirmar.text.strip()

        print(
            f"[Conta {conta}] Confirmação: "
            f"{texto_confirmacao}"
        )

        correspondencia = re.search(
            r"Confirmar\s*[·\-]\s*([\d.,]+)\s*ouro",
            texto_confirmacao,
            re.IGNORECASE
        )

        if not correspondencia:

            registrar_transferencia(
                conta,
                "uncertain",
                motivo="Texto da confirmação não reconhecido.",
                texto_confirmacao=texto_confirmacao
            )

            print(
                "[ERRO] Não foi possível interpretar o valor. "
                "Não vou confirmar."
            )

            return

        valor_confirmacao = parse_quantia(
            correspondencia.group(1)
        )

        if valor_confirmacao != quantidade:

            registrar_transferencia(
                conta,
                "uncertain",
                motivo="Valor da confirmação diferente do solicitado.",
                texto_confirmacao=texto_confirmacao,
                valor_confirmacao=valor_confirmacao
            )

            print(
                "[ERRO] VALOR DIFERENTE! "
                "Transferência cancelada."
            )

            return

        if not botao_confirmar.is_enabled():

            registrar_transferencia(
                conta,
                "uncertain",
                motivo="Botão de confirmação desabilitado."
            )

            print(
                "[ERRO] Botão de confirmação desabilitado."
            )

            return

        registrar_transferencia(
            conta,
            "pending_confirmation",
            texto_confirmacao=texto_confirmacao,
            valor_confirmacao=valor_confirmacao
        )

        print(
            f"[Conta {conta}] Confirmando "
            f"{formatar_ouro(quantidade)} ouro..."
        )

        driver.execute_script(
            "arguments[0].click();",
            botao_confirmar
        )

        try:

            WebDriverWait(driver, 12).until(
                lambda d: not any(
                    b.is_displayed()
                    for b in d.find_elements(
                        By.CSS_SELECTOR,
                        ".am-amigo .am-ouro button.btn-danger"
                    )
                )
            )

        except TimeoutException:

            registrar_transferencia(
                conta,
                "uncertain",
                motivo=(
                    "Não foi possível confirmar visualmente "
                    "o resultado do envio."
                )
            )

            print(
                "[ERRO] Resultado incerto. "
                "Verifique o histórico do jogo."
            )

            return

        registrar_transferencia(
            conta,
            "confirmed",
            quantidade=quantidade,
            destinatario=DESTINATARIO,
            valor_liquido=valor_liquido,
            saldo_antes=saldo
        )

        print(
            f"[Conta {conta}] Transferência confirmada!"
        )

        print(
            f"[Conta {conta}] Enviado: "
            f"{formatar_ouro(quantidade)} ouro."
        )

        print(
            f"[Conta {conta}] Recebido pelo Hellboy: "
            f"{valor_liquido} ouro."
        )

    except Exception as e:

        print(
            f"[Conta {conta}] Erro na transferência: {e}"
        )

        traceback.print_exc()

        try:

            dados = carregar_log()
            registro = dados.get(chave, {})

            if registro.get("status") in (
                "prepared",
                "pending_confirmation"
            ):

                registrar_transferencia(
                    conta,
                    "uncertain",
                    motivo=str(e)
                )

        except Exception:

            print(
                "[ERRO CRÍTICO] Não foi possível atualizar "
                "o histórico."
            )


# ============================================================
# CICLO DE ROTINA
# SOMENTE RECRUTAR + MOCHILA
# ============================================================

def executar_ciclo(driver, conta):

    print("\n" + "=" * 50)

    print(
        f"INICIANDO CICLO DA CONTA {conta}"
    )

    print("=" * 50)

    try:

        recrutar(driver, conta)

        aguardar(1)

        vender(driver, conta)

        print(
            f"[Conta {conta}] Ciclo concluído."
        )

    finally:

        fechar_janelas_rotina(
            driver,
            conta
        )


# ============================================================
# ABRIR UMA CONTA
# ============================================================

def abrir_conta(conta):

    profile = os.path.join(
        PROFILE_BASE,
        f"Conta{conta}"
    )

    os.makedirs(
        profile,
        exist_ok=True
    )

    options = webdriver.ChromeOptions()

    options.binary_location = CHROME_PATH

    options.add_argument(
        f"--user-data-dir={profile}"
    )

    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-debugging-port=0")

    driver = webdriver.Chrome(
        options=options
    )

    driver.get(URL)

    print(
        f"[Conta {conta}] Chrome aberto."
    )

    return driver


# ============================================================
# ABRIR AS QUATRO CONTAS
# ============================================================

def abrir_todas_as_contas():

    global DRIVERS

    print("\n" + "=" * 55)
    print("ABRINDO AS QUATRO CONTAS")
    print("=" * 55)

    for conta in range(1, TOTAL_CONTAS + 1):

        if conta in DRIVERS:
            continue

        try:

            print(
                f"\nAbrindo Conta {conta}..."
            )

            driver = abrir_conta(conta)

            DRIVERS[conta] = driver

        except Exception as e:

            print(
                f"[Conta {conta}] Erro ao abrir: {e}"
            )

            traceback.print_exc()

    for conta in range(1, TOTAL_CONTAS + 1):

        driver = DRIVERS.get(conta)

        if driver is None:
            continue

        try:

            aguardar_jogo(
                driver,
                conta
            )

            print(
                f"[Conta {conta}] Janela mantida aberta."
            )

        except Exception as e:

            print(
                f"[Conta {conta}] Erro ao verificar jogo: {e}"
            )


# ============================================================
# FECHAR TODAS AS CONTAS
# ============================================================

def fechar_todas_as_contas():

    global DRIVERS

    print("\nFechando todas as contas...")

    for conta, driver in list(DRIVERS.items()):

        try:

            driver.quit()

            print(
                f"[Conta {conta}] Chrome fechado."
            )

        except Exception:
            pass

    DRIVERS.clear()


# ============================================================
# PROCESSAR CONTAS
# ============================================================

def processar_contas():

    verificar_janelas()

    if not DRIVERS:

        print(
            "[ERRO] Nenhuma sessão disponível."
        )

        return

    for conta in range(1, TOTAL_CONTAS + 1):

        driver = obter_driver(conta)

        if driver is None:

            print(
                f"[Conta {conta}] Sessão indisponível. "
                "Conta ignorada."
            )

            continue

        print("\n" + "=" * 50)

        print(
            f"PROCESSANDO CONTA {conta}"
        )

        print("=" * 50)

        try:

            if not aguardar_jogo(driver, conta):
                continue

            executar_ciclo(
                driver,
                conta
            )

        except Exception:

            print(
                f"[Conta {conta}] Erro durante a rotina:"
            )

            traceback.print_exc()

    print(
        "\nVarredura das quatro contas concluída."
    )


# ============================================================
# TRANSFERÊNCIAS
# ============================================================

def processar_transferencias():

    print("\n" + "=" * 50)

    print(
        "TRANSFERÊNCIAS PARA CONTA 1"
    )

    print("=" * 50)

    verificar_janelas()

    for conta in range(2, TOTAL_CONTAS + 1):

        driver = obter_driver(conta)

        if driver is None:

            print(
                f"[Conta {conta}] Sessão indisponível. "
                "Transferência ignorada."
            )

            continue

        print(
            f"\n[TRANSFERÊNCIA] Processando Conta {conta}..."
        )

        try:

            if not aguardar_jogo(driver, conta):
                continue

            transferir_ouro(
                driver,
                conta
            )

        except Exception:

            print(
                f"[Conta {conta}] Erro na transferência:"
            )

            traceback.print_exc()

    print(
        "\nTransferências finalizadas."
    )


# ============================================================
# HISTÓRICO
# ============================================================

def mostrar_historico():

    print("\n" + "=" * 50)

    print(
        "HISTÓRICO DE TRANSFERÊNCIAS"
    )

    print("=" * 50)

    dados = carregar_log()

    if not dados:

        print(
            "Nenhuma transferência registrada."
        )

        return

    for conta in range(2, TOTAL_CONTAS + 1):

        chave = f"Conta{conta}"

        registro = dados.get(chave)

        print(f"\n{chave}")

        if not registro:

            print(
                "  Status: Nunca transferiu."
            )

            continue

        print(
            f"  Status: {registro.get('status', 'Desconhecido')}"
        )

        print(
            f"  Destinatário: "
            f"{registro.get('destinatario', DESTINATARIO)}"
        )

        if "quantidade" in registro:

            print(
                f"  Enviado: "
                f"{formatar_ouro(registro['quantidade'])} ouro"
            )

        if "valor_liquido" in registro:

            print(
                f"  Recebido: "
                f"{registro['valor_liquido']} ouro"
            )

        if "atualizado_em" in registro:

            print(
                f"  Atualizado em: "
                f"{registro['atualizado_em']}"
            )

        if registro.get("motivo"):

            print(
                f"  Observação: {registro['motivo']}"
            )


# ============================================================
# PAINEL
# ============================================================

def mostrar_painel():

    print("\n")

    print("=" * 55)

    print(
        "             THE RIFT - PAINEL"
    )

    print("=" * 55)

    print()

    print(
        "  [1] Executar rotina nas quatro contas"
    )

    print(
        "  [2] Transferir ouro das Contas 2, 3 e 4"
    )

    print(
        "  [3] Executar rotina + transferir ouro"
    )

    print(
        "  [4] Consultar histórico de transferências"
    )

    print(
        "  [5] Ativar rotina automática (60 segundos)"
    )

    print(
        "  [0] Encerrar e fechar as quatro contas"
    )

    print()

    print(
        f"  Sessões Selenium: {len(DRIVERS)}/{TOTAL_CONTAS}"
    )

    print("=" * 55)


# ============================================================
# MENU PRINCIPAL
# ============================================================

def main():

    print("=" * 55)

    print(
        "THE RIFT - AUTOMAÇÃO"
    )

    print("=" * 55)

    print(
        f"Destinatário: {DESTINATARIO}"
    )

    print(
        f"Reserva de ouro: {RESERVA_OURO}"
    )

    print(
        f"Intervalo automático: {INTERVALO_COLETA} segundos"
    )

    try:

        abrir_todas_as_contas()

        while True:

            mostrar_painel()

            opcao = input(
                "\nEscolha uma opção: "
            ).strip()

            if opcao == "1":

                print(
                    "\nExecutando rotina nas quatro contas..."
                )

                processar_contas()

            elif opcao == "2":

                print(
                    "\nIniciando transferências..."
                )

                processar_transferencias()

            elif opcao == "3":

                print(
                    "\nExecutando rotina..."
                )

                processar_contas()

                print(
                    "\nIniciando transferências..."
                )

                processar_transferencias()

            elif opcao == "4":

                mostrar_historico()

            elif opcao == "5":

                print(
                    "\nRotina automática iniciada."
                )

                print(
                    "Pressione CTRL+C para voltar ao painel."
                )

                try:

                    while True:

                        print("\n" + "#" * 50)

                        print(
                            "NOVO CICLO:",
                            datetime.now().strftime(
                                "%d/%m/%Y %H:%M:%S"
                            )
                        )

                        print("#" * 50)

                        processar_contas()

                        print(
                            f"\nAguardando "
                            f"{INTERVALO_COLETA} segundos..."
                        )

                        time.sleep(
                            INTERVALO_COLETA
                        )

                except KeyboardInterrupt:

                    print(
                        "\nRotina automática interrompida."
                    )

            elif opcao == "0":

                print(
                    "\nEncerrando automação..."
                )

                break

            else:

                print(
                    "\n[AVISO] Opção inválida."
                )

            input(
                "\nPressione ENTER para voltar ao painel..."
            )

    except KeyboardInterrupt:

        print(
            "\nPrograma interrompido pelo usuário."
        )

    except Exception:

        print(
            "\nERRO GERAL:"
        )

        traceback.print_exc()

    finally:

        fechar_todas_as_contas()

        print(
            "\nPrograma encerrado."
        )

        input(
            "Pressione ENTER para fechar o console..."
        )


# ============================================================
# INICIAR
# ============================================================

if __name__ == "__main__":

    main()
