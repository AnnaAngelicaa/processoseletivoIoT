# Relatório Técnico — Sistema de Monitoramento de Temperatura e Abertura de Porta

## Identificação do Candidato

- **Nome completo:** Anna Angélica Costa de Souza

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
- Mensagens Serial reproduzidas exatamente como especificado (validação do CI é caractere por caractere).

---

## Resultados Obtidos

Validado na simulação Wokwi: inicialização, alerta de porta aberta, alerta de degradação térmica e normalização funcionaram conforme esperado. Os 3 cenários (`test_1`, `test_2`, `test_3`) foram executados via GitHub Actions.

---

## Comentários Adicionais

**Dificuldade encontrada:** saída Serial não aparecia inicialmente — faltava a conexão `esp:TX0`/`esp:RX0` com `$serialMonitor` no `diagram.json`.

**Limitações:** por especificação do projeto, o sistema trata apenas **elevação** térmica (degradação por aumento de temperatura), que é o risco relevante para o cenário proposto — quedas de temperatura não são tratadas como anomalia. Também não há tratamento de erro no I2C.

**Melhorias futuras:** retry na leitura do MPU6050; limites configuráveis externamente.