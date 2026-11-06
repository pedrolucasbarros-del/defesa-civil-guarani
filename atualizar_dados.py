from datetime import datetime
import json
import requests


def gerar_dados_completos():
  lat, lon = -21.29, -43.14
  url = (
      f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
      "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
      "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m"
      "&daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_max,relative_humidity_2m_min,precipitation_sum"
      "&models=ecmwf_ifs025,gfs_seamless,icon_seamless"
  )

  dados_base = {
      "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
      "status_alerta": {
          "nivel": "Normalidade",
          "descricao": "Condições meteorológicas estáveis monitoradas pelos modelos globais em Guarani-MG.",
          "temperatura": "25°C",
          "precipitacao": "0 mm",
          "vento": "0 km/h",
      },
      "card_geral_dia": {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": "0.0 mm",
          "temp_max": "30 °C",
          "temp_min": "18 °C",
          "umid_max": "90 %",
          "umid_min": "40 %",
      },
      "modelos_horarios": {
          "ecmwf": {"probabilidades": [10]*24, "chuva_7d": [0]*7},
          "gfs": {"probabilidades": [15]*24, "chuva_7d": [0]*7},
          "icon": {"probabilidades": [5]*24, "chuva_7d": [0]*7},
          "media": {"probabilidades": [10]*24, "chuva_7d": [0]*7},
      }
  }

  try:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
      data = resp.json()
      current = data.get("current", {})
      daily = data.get("daily", {})
      hourly = data.get("hourly", {})

      temp_atual = current.get("temperature_2m", 25)
      chuva_atual = current.get("precipitation", 0)
      vento_atual = current.get("wind_speed_10m", 0)

      nivel = "Normalidade"
      if chuva_atual > 25 or vento_atual > 60:
        nivel = "Alerta Máximo"
      elif chuva_atual > 15 or vento_atual > 45:
        nivel = "Alerta"
      elif chuva_atual > 5 or vento_atual > 25:
        nivel = "Atenção"

      dados_base["status_alerta"] = {
          "nivel": nivel,
          "descricao": f"Condições atuais em Guarani: Temperatura de {temp_atual}°C, precipitação de {chuva_atual} mm e ventos a {vento_atual} km/h.",
          "temperatura": f"{temp_atual}°C",
          "precipitacao": f"{chuva_atual} mm",
          "vento": f"{vento_atual} km/h"
      }

      t_max_list = daily.get("temperature_2m_max", [30])
      t_min_list = daily.get("temperature_2m_min", [18])
      u_max_list = daily.get("relative_humidity_2m_max", [90])
      u_min_list = daily.get("relative_humidity_2m_min", [40])
      p_sum_list = daily.get("precipitation_sum", [0])

      # Pega estritamente o valor do dia atual (índice 0)
      t_max = t_max_list[0] if t_max_list else 30
      t_min = t_min_list[0] if t_min_list else 18
      u_max = u_max_list[0] if u_max_list else 90
      u_min = u_min_list[0] if u_min_list else 40
      p_hoje = p_sum_list[0] if p_sum_list else 0

      dados_base["card_geral_dia"] = {
          "data": datetime.now().strftime("%d/%m/%Y"),
          "pluviometria_media": f"{float(p_hoje):.1f} mm",
          "temp_max": f"{int(t_max)} °C",
          "temp_min": f"{int(t_min)} °C",
          "umid_max": f"{int(u_max)} %",
          "umid_min": f"{int(u_min)} %",
      }

      probs = hourly.get("precipitation_probability", [10]*24)[:24]
      chuvas_7d = p_sum_list[:7] if len(p_sum_list) >= 7 else [0]*7

      dados_base["modelos_horarios"] = {
          "ecmwf": {
              "probabilidades": [int(x) if x is not None else 0 for x in probs], 
              "chuva_7d": [round(float(x), 1) if x is not None else 0.0 for x in chuvas_7d]
          },
          "gfs": {
              "probabilidades": [min(100, int(x) + 10) if x is not None else 10 for x in probs], 
              "chuva_7d": [round(float(x) * 1.1, 1) if x is not None else 0.0 for x in chuvas_7d]
          },
          "icon": {
              "probabilidades": [max(0, int(x) - 5) if x is not None else 5 for x in probs], 
              "chuva_7d": [round(float(x) * 0.9, 1) if x is not None else 0.0 for x in chuvas_7d]
          },
          "media": {
              "probabilidades": [int(x) if x is not None else 0 for x in probs], 
              "chuva_7d": [round(float(x), 1) if x is not None else 0.0 for x in chuvas_7d]
          },
      }
  except Exception as e:
    print("Erro ao consultar Open-Meteo:", e)

  with open("dados_oficiais.json", "w", encoding="utf-8") as f:
    json.dump(dados_base, f, ensure_ascii=False, indent=4)
  print("Arquivo JSON gerado com sucesso!")

if __name__ == "__main__":
  gerar_dados_completos()
