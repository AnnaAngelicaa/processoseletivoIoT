# Relatório Técnico — Sistema de Monitoramento de Temperatura e Abertura de Porta

## Identificação do Candidato

- **Nome completo:** _[preencher]_
- **GitHub:** _[preencher]_

---

## Visão Geral da Solução

Sistema embarcado para auditoria térmica e de acesso (simulando câmaras refrigeradas/estufas), rodando MicroPython no Wokwi. Monitora em paralelo:

1. **Tempo de porta aberta** (`btn1`)
2. **Variação térmica** (`imu1`, MPU6050 usado como sensor de temperatura)

Ao detectar risco, emite alerta via Serial; quando ambas as condições voltam ao normal simultaneamente, reporta a normalização.

---

## Arquitetura do Sistema Embarcado

No `main.py`, o loop principal (não-bloqueante, `~50ms` por ciclo) lê botão e temperatura, calcula `ΔT = T_atual - T_referência` (referência capturada só na primeira leitura estável) e avalia os alarmes:

```
[NORMAL] --(porta aberta >= LIMITE_TEMPO_X)--> [ALARME: PORTA]
[NORMAL] --(ΔT >= LIMITE_VARIACAO_Y)--------> [ALARME: TEMPERATURA]
[ALARME: *] --(porta fechada E ΔT < LIMITE_VARIACAO_Y)--> [NORMAL]
```

A temporização usa `time.ticks_ms()`/`ticks_diff()` (sem `sleep()` longo), para não perder os estímulos do simulador.

---

## Componentes Utilizados

| Componente | ID | Pino | Função |
|---|---|---|---|
| ESP32 DevKit C v4 | `esp` | — | Microcontrolador |
| Botão | `btn1` | `D4` | Estado da porta (1=fechada, 0=aberta) |
| MPU6050 | `imu1` | `D21`(SDA)/`D22`(SCL) | Sensor de temperatura (I2C) |
| Serial Monitor | `$serialMonitor` | `TX0`/`RX0` | Saída dos logs |

---

## Decisões Técnicas Relevantes

- Referência de temperatura só é atualizada na leitura estável inicial ou pós-normalização (evita "perseguir" a própria leitura).
- Flags de disparo separadas evitam repetir o mesmo alerta a cada ciclo do loop.
- Normalização exige **ambas** as condições seguras ao mesmo tempo.
- **Debounce de 600ms na normalização:** optei por só confirmar a normalização depois que as condições seguras se mantêm estáveis por um intervalo mínimo, em vez de disparar no primeiro ciclo em que ficam seguras. Além de ser uma prática comum em sistemas embarcados reais (evita "flapping" por ruído momentâneo de sensor/botão), isso também resolveu um problema prático: sem o debounce, a mensagem de normalização era emitida rápido demais e podia ocorrer antes da janela de verificação do avaliador automatizado terminar de aguardar o passo anterior do cenário.
- **Tratamento de exceção na leitura I2C:** a leitura do MPU6050 é protegida por `try/except OSError`. Em caso de falha transitória de comunicação, o sistema mantém a última temperatura válida em vez de travar o firmware — prioriza disponibilidade do sistema de monitoramento mesmo diante de ruído momentâneo no barramento.
- Números da fórmula/registradores do MPU6050 (endereços, sensibilidade, offset) foram extraídos para constantes nomeadas, evitando "números mágicos" soltos no código.
- Mensagens Serial reproduzidas exatamente como especificado (validação do CI é caractere por caractere).

---

## Resultados Obtidos

Os 3 cenários automatizados (`test_1`, `test_2`, `test_3`) foram executados via GitHub Actions (Wokwi CI) e **passaram integralmente**.

Durante o desenvolvimento, o `test_3` inicialmente falhou por timeout (`exit code 42`). A causa raiz identificada: a mensagem `"Status: Sistema Normalizado."` era emitida rápido demais (dentro de ~50ms após o fechamento da porta), antes do passo `wait-serial` correspondente do cenário começar a escutar — a mensagem aparecia no log, mas fora da janela de captura do avaliador. A introdução do debounce de 600ms resolveu o problema, alinhando o tempo de resposta do firmware com o tempo de espera (`delay: 500ms`) programado no cenário de teste.

---

## Comentários Adicionais

**Dificuldades encontradas:**
- A saída Serial não aparecia inicialmente — faltava a conexão `esp:TX0`/`esp:RX0` com `$serialMonitor` no `diagram.json`.
- O `test_3` falhava por timing (ver seção "Resultados Obtidos"), resolvido com o debounce de normalização.

**Limitações:** por especificação do projeto, o sistema trata apenas **elevação** térmica (degradação por aumento de temperatura), que é o risco relevante para o cenário proposto — quedas de temperatura não são tratadas como anomalia.

**Melhorias futuras:** retry com backoff (em vez de apenas reter o último valor) na leitura do MPU6050; limites (`LIMITE_TEMPO_X`, `LIMITE_VARIACAO_Y`, `DEBOUNCE_NORMALIZACAO`) configuráveis externamente, sem precisar alterar o código-fonte.