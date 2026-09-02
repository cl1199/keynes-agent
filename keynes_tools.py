import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time


class KeynesTools:
    """
      APIs:
      - api.worldbank.org -> indicadores macroeconomicos por pais
      - open.er-api.com -> tipo de cambio de moneda 
      """

    TIMEOUT = 20
    ZONA = "America/Guatemala"
    INDICADORES = {
    # Actividad económica
    "pib": "NY.GDP.MKTP.CD",
    "pib_real_crecimiento": "NY.GDP.MKTP.KD.ZG",
    "pib_per_capita": "NY.GDP.PCAP.CD",
    "pib_per_capita_crecimiento": "NY.GDP.PCAP.KD.ZG",

    # Precios
    "inflacion": "FP.CPI.TOTL.ZG",

    # Población y empleo
    "poblacion": "SP.POP.TOTL",
    "crecimiento_poblacion": "SP.POP.GROW",
    "desempleo": "SL.UEM.TOTL.ZS",
    "participacion_laboral": "SL.TLF.CACT.ZS",

    # Sector externo
    "exportaciones": "NE.EXP.GNFS.CD",
    "importaciones": "NE.IMP.GNFS.CD",
    "balanza_comercial": "NE.RSB.GNFS.CD",
    "cuenta_corriente": "BN.CAB.XOKA.CD",
    "cuenta_corriente_pct_pib": "BN.CAB.XOKA.GD.ZS",
    "ied_entrada": "BX.KLT.DINV.CD.WD",
    "ied_entrada_pct_pib": "BX.KLT.DINV.WD.GD.ZS",

    # Remesas
    "remesas": "BX.TRF.PWKR.CD.DT",
    "remesas_pct_pib": "BX.TRF.PWKR.DT.GD.ZS",

    # Finanzas públicas
    "deuda_gobierno_pct_pib": "GC.DOD.TOTL.GD.ZS",
    "ingresos_tributarios_pct_pib": "GC.TAX.TOTL.GD.ZS",

    # Sector financiero
    "credito_sector_privado_pct_pib": "FS.AST.PRVT.GD.ZS",
    "tasa_interes_real": "FR.INR.RINR",
    "tasa_prestamos": "FR.INR.LEND",

    # Desarrollo
    "esperanza_vida": "SP.DYN.LE00.IN",
    "pobreza_215": "SI.POV.DDAY",
    "gini": "SI.POV.GINI",

    # Estructura económica
    "agricultura_pct_pib": "NV.AGR.TOTL.ZS",
    "industria_pct_pib": "NV.IND.TOTL.ZS",
    "manufactura_pct_pib": "NV.IND.MANF.ZS",
    "servicios_pct_pib": "NV.SRV.TOTL.ZS",
    }
    NOMBRES = {
    # Actividad económica
    "pib": "PIB (US$)",
    "pib_real_crecimiento": "Crecimiento del PIB real (%)",
    "pib_per_capita": "PIB per cápita (US$)",
    "pib_per_capita_crecimiento": "Crecimiento del PIB per cápita (%)",

    # Precios
    "inflacion": "Inflación anual (%)",

    # Población y empleo
    "poblacion": "Población total",
    "crecimiento_poblacion": "Crecimiento de la población (%)",
    "desempleo": "Desempleo (% de la fuerza laboral)",
    "participacion_laboral": "Participación laboral (%)",

    # Sector externo
    "exportaciones": "Exportaciones (US$)",
    "importaciones": "Importaciones (US$)",
    "balanza_comercial": "Balanza comercial (US$)",
    "cuenta_corriente": "Cuenta corriente (US$)",
    "cuenta_corriente_pct_pib": "Cuenta corriente (% del PIB)",
    "ied_entrada": "Inversión extranjera directa (US$)",
    "ied_entrada_pct_pib": "Inversión extranjera directa (% del PIB)",

    # Remesas
    "remesas": "Remesas recibidas (US$)",
    "remesas_pct_pib": "Remesas (% del PIB)",

    # Finanzas públicas
    "deuda_gobierno_pct_pib": "Deuda del gobierno (% del PIB)",
    "ingresos_tributarios_pct_pib": "Ingresos tributarios (% del PIB)",

    # Sector financiero
    "credito_sector_privado_pct_pib": "Crédito al sector privado (% del PIB)",
    "tasa_interes_real": "Tasa de interés real (%)",
    "tasa_prestamos": "Tasa de interés activa (%)",

    # Desarrollo
    "esperanza_vida": "Esperanza de vida (años)",
    "pobreza_215": "Pobreza extrema, US$2.15/día (%)",
    "gini": "Índice de Gini",

    # Estructura económica
    "agricultura_pct_pib": "Agricultura (% del PIB)",
    "industria_pct_pib": "Industria (% del PIB)",
    "manufactura_pct_pib": "Manufactura (% del PIB)",
    "servicios_pct_pib": "Servicios (% del PIB)",
}
    NOMBRES_CORTOS = {
        "pib": "PIB",
        "pib_per_capita": "PIB per cápita",
        "pib_real_crecimiento": "Crecimiento real",
        "inflacion": "Inflación",
        "poblacion": "Población",
        "desempleo": "Desempleo",
        "pobreza_215": "Pobreza extrema",
        "esperanza_vida": "Esperanza de vida",
    }
    
    def __init__(self):
        # Caché en memoria para los indicadores del Banco Mundial.
        # Vive mientras corra el proceso. No se cachea el tipo de cambio
        # porque cambia a diario y un valor viejo seria incorrecto.
        self._cache = {}

### Herramienta 1 Banco mundial 
    def consultar_indicador_banco_mundial(self, pais: str, indicador: str, anios: int = 5) -> dict:
        """Indicadores macro del Banco Mundial. pais en ISO3, por ejemplo GTM."""
        pais = (pais or "").strip().upper()
        clave = (indicador or "").strip().lower()

        if len(pais) != 3:
            return {"error": "El país debe indicarse con código ISO3, por ejemplo GTM."}

        codigo = self.INDICADORES.get(clave)
        if codigo is None:
            return {"error": f"Indicador '{indicador}' no disponible.",
                    "indicadores_validos": list(self.INDICADORES.keys())}

        try:
            anios = int(anios)
        except (TypeError, ValueError):
            return {"error": "'anios' debe ser un entero positivo."}
        if anios <= 0:
            return {"error": "'anios' debe ser un entero positivo."}

        llave = f"{pais}:{clave}:{anios}"
        if llave in self._cache:
            return self._cache[llave]

        url = f"https://api.worldbank.org/v2/country/{pais}/indicator/{codigo}"
        try:
            r = requests.get(url,
                             params={"format": "json", "per_page": anios * 3},
                             timeout=self.TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except requests.Timeout:
            return {"error": "El servidor del Banco Mundial esta tardando mas de lo "
                             "normal. Intenta de nuevo en unos segundos."}
        except Exception as e:
            return {"error": f"No se pudo consultar el Banco Mundial: {e}"}

        observaciones = []
        if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
            return {"error": f"Respuesta inválida del Banco Mundial para {pais}."}

        for fila in data[1]:
            if fila.get("value") is not None:
                observaciones.append({"anio": fila["date"], "valor": fila["value"]})
            if len(observaciones) >= anios:
                break

        if not observaciones:
            return {"error": f"No hay valores publicados de {clave} para {pais}."}

        resultado = {
            "pais": data[1][0].get("country", {}).get("value", pais),
            "indicador": clave,
            "indicador_nombre": self.NOMBRES.get(clave, clave),
            "dato_mas_reciente": observaciones[0],
            "serie": observaciones,
            "fuente": "Banco Mundial",
        }
        self._cache[llave] = resultado
        return resultado

### Herramienta 2: Conversión entre monedas (por defecto 1 USD a GTQ)

    def convertir_moneda(self, monto: float = 1, origen: str = "USD", destino: str = "GTQ") -> dict:
        """
        Convierte un monto entre dos monedas.
        Con los valores por defecto responde "¿a cómo está el dólar?" (1 USD -> GTQ).
        """
        origen = (origen or "").strip().upper()
        destino = (destino or "").strip().upper()

        if not origen or not destino:
            return {"error": "Debe indicarse la moneda de origen y la de destino."}

        try:
            monto = float(monto)
        except (TypeError, ValueError):
            return {"error": f"El monto debe ser un numero, se recibio: {monto}"}
        url = f"https://open.er-api.com/v6/latest/{origen}"
        try:
            r = requests.get(url, timeout=self.TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return {"error": f"No se pudo consultar el tipo de cambio: {e}"}

        if data.get("result") != "success":
            return {"error": f"La moneda {origen} no fue reconocida por la fuente."}

        tasa = data.get("rates", {}).get(destino)
        if tasa is None:
            return {"error": f"No hay tasa {destino} disponible para {origen}."}
        resultado = monto * tasa
        return {
            "monto_original": monto,
            "moneda_origen": origen,
            "moneda_destino": destino,
            "tipo_cambio": round(tasa, 6),
            "monto_convertido": round(resultado, 2),
            "interpretacion": f"{monto} {origen} = {round(resultado, 2)} {destino}",
            "fecha_actualizacion": self._fecha_local(data.get("time_last_update_unix")),
            "fuente": "open.er-api.com",
        }
 
# Herramienta 3: fecha y hora actual     
    def _fecha_local(self, unix_ts) -> str:
        """Convierte una marca de tiempo UTC a hora de Guatemala."""
        try:
            momento = datetime.fromtimestamp(int(unix_ts), ZoneInfo(self.ZONA))
            return momento.strftime("%d/%m/%Y %H:%M (hora de Guatemala)")
        except (TypeError, ValueError, OSError):
            return "fecha de actualizacion no disponible"
                             
    def obtener_fecha_hora(self) -> dict:
        """
        Fecha y hora actual en Guatemala. Sirve para resolver preguntas
        relativas como 'el mes pasado' o 'lo que va del anio'.
        """
        ahora = datetime.now(ZoneInfo(self.ZONA))
        return {
            "fecha": ahora.strftime("%d/%m/%Y"),
            "hora": ahora.strftime("%H:%M:%S"),
            "dia_semana": ahora.strftime("%A"),
            "anio": ahora.year,
            "zona_horaria": self.ZONA,
        }

### Herramienta 4: Gráfico de la evolución de un indicador

    def graficar_indicador(self, pais: str, indicador: str, anios: int = 10) -> dict:
        """
        Genera un gráfico de línea con la evolución de un indicador del
        Banco Mundial y lo guarda como archivo PNG.
        """
        datos = self.consultar_indicador_banco_mundial(pais, indicador, anios)

        if "error" in datos:
            return datos          # se propaga el error tal cual

        serie = datos["serie"]
        if len(serie) < 2:
            return {"error": f"Solo hay {len(serie)} observación; se necesitan al menos 2 para graficar."}

        # El Banco Mundial devuelve del más reciente al más antiguo;
        # para graficar necesitamos orden cronológico.
        serie = sorted(serie, key=lambda x: x["anio"])
        anios_serie = [obs["anio"] for obs in serie]
        valores = [obs["valor"] for obs in serie]

        # Datos ya normalizados por la herramienta 1
        clave = datos["indicador"]
        nombre_pais = datos["pais"]
        etiqueta = self.NOMBRES.get(clave, clave.replace("_", " ").capitalize())
        nombre = f"{clave}_{pais.strip().upper()}.png"


        return {
            "tipo": "grafico",
            "pais": nombre_pais,
            "indicador": clave,
            "indicador_nombre": etiqueta,
            "serie": [{"anio": a, "valor": v} for a, v in zip(anios_serie, valores)],
            "periodo": f"{anios_serie[0]}-{anios_serie[-1]}",
            "valor_inicial": valores[0],
            "valor_final": valores[-1],
            "observaciones": len(serie),
            "fuente": "Banco Mundial",
        }

### Herramienta 5: Comparación de un indicador entre varios países

    def comparar_paises(self, paises, indicador: str, anios: int = 10) -> dict:
        """
        Compara la evolución de un mismo indicador entre varios países.
        paises: lista de códigos ISO3, por ejemplo ["GTM", "MEX", "CRI"]
        """
        # El modelo a veces manda un string en vez de lista
        if isinstance(paises, str):
            paises = [p.strip() for p in paises.replace(",", " ").split()]

        if not paises or len(paises) < 2:
            return {"error": "Debe indicarse al menos dos paises para comparar."}
        if len(paises) > 5:
            return {"error": "Maximo 5 paises por comparacion."}

        series = []
        nombres = []
        fallidos = []

        for pais in paises:
            datos = self.consultar_indicador_banco_mundial(pais, indicador, anios)
            if "error" in datos:
                fallidos.append({"pais": pais, "motivo": datos["error"]})
                continue

            nombres.append(datos["pais"])
            for obs in sorted(datos["serie"], key=lambda x: x["anio"]):
                series.append({
                    "pais": datos["pais"],
                    "anio": obs["anio"],
                    "valor": obs["valor"],
                })

        if len(nombres) < 2:
            return {"error": "No se obtuvieron datos suficientes para comparar.",
                    "fallidos": fallidos}

        clave = indicador.strip().lower()
        ultimos = {}
        for n in nombres:
            propias = [s for s in series if s["pais"] == n]
            ultimos[n] = {"anio": propias[-1]["anio"], "valor": propias[-1]["valor"]}
        analisis = {}
        for n in nombres:
            propias = [s for s in series if s["pais"] == n]
            valores = [s["valor"] for s in propias]
            inicial, final = valores[0], valores[-1]

            analisis[n] = {
                "inicial": round(inicial, 2),
                "final": round(final, 2),
                "cambio_absoluto": round(final - inicial, 2),
                "promedio": round(sum(valores) / len(valores), 2),
                "maximo": round(max(valores), 2),
                "minimo": round(min(valores), 2),
            }

        finales = {n: analisis[n]["final"] for n in nombres}
        mayor = max(finales, key=finales.get)
        menor = min(finales, key=finales.get)

        resumen = {
            "mayor_valor_actual": {"pais": mayor, "valor": finales[mayor]},
            "menor_valor_actual": {"pais": menor, "valor": finales[menor]},
            "brecha": round(finales[mayor] - finales[menor], 2),
        }
        return {
            "tipo": "comparacion",
            "indicador": clave,
            "indicador_nombre": self.NOMBRES.get(clave, clave),
            "paises": nombres,
            "serie": series,
            "ultimos_valores": ultimos,
            "fallidos": fallidos,
            "fuente": "Banco Mundial",
            "analisis": analisis,
            "resumen": resumen,
        }
### Herramienta 6: Ficha macroeconómica de un país

    FICHA = [
        "pib", "pib_per_capita", "pib_real_crecimiento", "inflacion",
        "poblacion", "desempleo", "pobreza_215", "esperanza_vida",
    ]
    # Indicadores donde un aumento es una señal negativa
    INVERSOS = {"inflacion", "desempleo", "pobreza_215"}

    def ficha_pais(self, pais: str) -> dict:
        """Perfil macroeconómico de un país con los indicadores clave."""
        pais = (pais or "").strip().upper()
        if len(pais) != 3:
            return {"error": "El país debe indicarse con código ISO3, por ejemplo GTM."}

        metricas = []
        nombre_pais = pais

        for clave in self.FICHA:
            datos = self.consultar_indicador_banco_mundial(pais, clave, 2)
            if "error" in datos:
                continue

            nombre_pais = datos["pais"]
            serie = datos["serie"]          # [más reciente, anterior]
            actual = serie[0]
            previo = serie[1] if len(serie) > 1 else None

            metricas.append({
                "indicador": clave,
                "nombre": self.NOMBRES.get(clave, clave),
                "anio": actual["anio"],
                "valor": actual["valor"],
                "valor_previo": previo["valor"] if previo else None,
                "anio_previo": previo["anio"] if previo else None,
                "inverso": clave in self.INVERSOS,
            })

        if not metricas:
            return {"error": f"No se obtuvieron datos para {pais}."}

        return {
            "tipo": "ficha",
            "pais": nombre_pais,
            "codigo": pais,         
            "metricas": metricas,
            "fuente": "Banco Mundial",
        }
### Herramienta 7: Composición sectorial del PIB

    SECTORES = ["agricultura_pct_pib", "industria_pct_pib",
                "servicios_pct_pib"]

    def composicion_sectorial(self, pais: str) -> dict:
        """
        Estructura del PIB por sector: agricultura, industria, manufactura
        y servicios, como porcentaje del PIB.
        """
        pais = (pais or "").strip().upper()
        if len(pais) != 3:
            return {"error": "El país debe indicarse con código ISO3, por ejemplo GTM."}

        sectores = []
        nombre_pais = pais
        anio = None

        for clave in self.SECTORES:
            datos = self.consultar_indicador_banco_mundial(pais, clave, 1)
            if "error" in datos:
                continue

            nombre_pais = datos["pais"]
            obs = datos["serie"][0]
            anio = obs["anio"]

            etiqueta = self.NOMBRES.get(clave, clave).split(" (")[0]
            sectores.append({
                "sector": etiqueta,
                "porcentaje": round(obs["valor"], 2),
                "anio": obs["anio"],
            })

        if not sectores:
            return {"error": f"No hay datos de composición sectorial para {pais}."}

        return {
            "tipo": "sectores",
            "pais": nombre_pais,
            "codigo": pais,
            "anio": anio,
            "sectores": sectores,
            "fuente": "Banco Mundial",
        }
### Herramienta 8: Mapa coroplético de un indicador

    def mapa_indicador(self, paises, indicador: str) -> dict:
        """
        Valor mas reciente de un indicador para varios paises,
        preparado para dibujar un mapa coropletico.
        """
        if isinstance(paises, str):
            paises = [p.strip() for p in paises.replace(",", " ").split()]

        if not paises or len(paises) < 2:
            return {"error": "Debe indicarse al menos dos paises."}
        if len(paises) > 20:
            return {"error": "Maximo 20 paises por mapa."}

        valores = []
        fallidos = []

        for pais in paises:
            datos = self.consultar_indicador_banco_mundial(pais, indicador, 1)
            if "error" in datos:
                fallidos.append(pais)
                continue

            obs = datos["serie"][0]
            valores.append({
                "codigo": pais.strip().upper(),
                "pais": datos["pais"],
                "anio": obs["anio"],
                "valor": round(obs["valor"], 2),
            })

        if len(valores) < 2:
            return {"error": "No se obtuvieron datos suficientes para el mapa.",
                    "fallidos": fallidos}

        clave = indicador.strip().lower()
        return {
            "tipo": "mapa",
            "indicador": clave,
            "indicador_nombre": self.NOMBRES.get(clave, clave),
            "valores": valores,
            "fallidos": fallidos,
            "fuente": "Banco Mundial",
        }
    # Prueba rapida de las herramientas sin pasar por el agente
if __name__ == "__main__":
    herramientas = KeynesTools()
    print(herramientas.mapa_indicador(["GTM","SLV","HND","NIC","CRI","PAN","BLZ"], "pib_per_capita"))