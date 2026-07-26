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

def mpu_init():
    i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')  # tira o sensor do modo sleep

def ler_temperatura():
    dados = i2c.readfrom_mem(MPU_ADDR, 0x41, 2)
    bruto = (dados[0] << 8) | dados[1]
    if bruto > 32767:
        bruto -= 65536
    return (bruto / 340.0) + 36.53  # formula do registrador de temperatura do MPU6050

mpu_init()

# ---------------- Estado do sistema ----------------
porta_aberta_desde = None
temp_referencia = None
em_alarme = False
alarme_porta_disparado = False
alarme_temp_disparado = False
condicoes_seguras_desde = None

print("Sistema de Monitoramento Inicializado")

while True:
    porta_fechada = btn1.value() == 1
    temp_atual = ler_temperatura()

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
    condicoes_seguras = porta_fechada and delta_t < LIMITE_VARIACAO_Y
    if em_alarme and condicoes_seguras:
        if condicoes_seguras_desde is None:
            condicoes_seguras_desde = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), condicoes_seguras_desde) >= DEBOUNCE_NORMALIZACAO:
            em_alarme = False
            alarme_porta_disparado = False
            alarme_temp_disparado = False
            temp_referencia = temp_atual
            condicoes_seguras_desde = None
            print("Status: Sistema Normalizado.")
    else:
        condicoes_seguras_desde = None

    time.sleep_ms(50)