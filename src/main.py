import time
from machine import Pin, I2C

# ---------------- Parametros ----------------
LIMITE_TEMPO_X = 5000       # ms - tempo maximo com a porta aberta
LIMITE_VARIACAO_Y = 3.0     # graus C - variacao maxima de temperatura tolerada
DEBOUNCE_NORMALIZACAO = 600  # ms - confirma estabilidade antes de normalizar

# ---------------- Hardware ----------------
# Botao (fim de curso da porta): Fechado/Pressionado = 1, Aberto/Solto = 0
btn1 = Pin(4, Pin.IN, Pin.PULL_DOWN)

# MPU6050 via I2C (usado como sensor de temperatura)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
MPU_ADDR = 0x68
REG_PWR_MGMT_1 = 0x6B     # registrador de gerenciamento de energia (0 = tira do modo sleep)
REG_TEMP_OUT_H = 0x41     # registrador inicial da leitura de temperatura (2 bytes, big-endian)
TEMP_SENSITIVITY = 340.0  # fator de escala do datasheet do MPU6050
TEMP_OFFSET = 36.53       # offset do datasheet do MPU6050

def mpu_init():
    i2c.writeto_mem(MPU_ADDR, REG_PWR_MGMT_1, b'\x00')

def ler_temperatura():
    dados = i2c.readfrom_mem(MPU_ADDR, REG_TEMP_OUT_H, 2)
    bruto = (dados[0] << 8) | dados[1]
    if bruto > 32767:
        bruto -= 65536
    return (bruto / TEMP_SENSITIVITY) + TEMP_OFFSET

mpu_init()

# ---------------- Estado do sistema ----------------
porta_aberta_desde = None
temp_referencia = None
em_alarme = False
alarme_porta_disparado = False
alarme_temp_disparado = False
condicoes_seguras_desde = None

print("Sistema de Monitoramento Inicializado")

temp_atual = None

while True:
    porta_fechada = btn1.value() == 1

    # Leitura resiliente do sensor: em caso de falha transitoria no I2C,
    # mantem a ultima temperatura valida em vez de travar o firmware.
    try:
        temp_atual = ler_temperatura()
    except OSError:
        print("AVISO: Falha de leitura no sensor de temperatura, mantendo ultimo valor valido")
        if temp_atual is None:
            time.sleep_ms(50)
            continue

    # Captura a referencia apenas na primeira leitura estavel (ou apos normalizacao)
    if temp_referencia is None and porta_fechada and not em_alarme:
        temp_referencia = temp_atual

    delta_t = (temp_atual - temp_referencia) if temp_referencia is not None else 0

    # ---- Deteccao: Porta aberta por tempo excessivo (Limite X) ----
    if not porta_fechada:
        if porta_aberta_desde is None:
            porta_aberta_desde = time.ticks_ms()
        tempo_aberta = time.ticks_diff(time.ticks_ms(), porta_aberta_desde)
        if tempo_aberta >= LIMITE_TEMPO_X and not alarme_porta_disparado:
            alarme_porta_disparado = True
            em_alarme = True
            print("ALERTA: Porta aberta por muito tempo!")
    else:
        porta_aberta_desde = None

    # ---- Deteccao: Elevacao termica (Variacao Y) ----
    if delta_t >= LIMITE_VARIACAO_Y and not alarme_temp_disparado:
        alarme_temp_disparado = True
        em_alarme = True
        print("ALERTA: Degradacao termica detectada!")

    # ---- Normalizacao: exige AMBAS as condicoes seguras simultaneamente ----
    # Um pequeno debounce evita disparos instantaneos demais e garante
    # estabilidade real da leitura antes de confirmar a normalizacao.
    condicoes_seguras = porta_fechada and delta_t < LIMITE_VARIACAO_Y
    if em_alarme and condicoes_seguras:
        if condicoes_seguras_desde is None:
            condicoes_seguras_desde = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), condicoes_seguras_desde) >= DEBOUNCE_NORMALIZACAO:
            em_alarme = False
            alarme_porta_disparado = False
            alarme_temp_disparado = False
            temp_referencia = temp_atual  # novo baseline
            condicoes_seguras_desde = None
            print("Status: Sistema Normalizado.")
    else:
        condicoes_seguras_desde = None

    time.sleep_ms(50)
    