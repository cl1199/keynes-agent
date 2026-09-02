from dotenv import load_dotenv
from groq import Groq
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from basic_memory import BasicMemory
from keynes_tools import KeynesTools

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

now = datetime.now(ZoneInfo("America/Guatemala"))
memory = BasicMemory(max_messages=10)
tools = KeynesTools()

SYSTEM_PROMPT = f"""
Eres un agente economico especializado principalmente en datos macroeconomicos.
Respondes en español, de forma breve y con datos concretos.

OBJETIVO:
Apoyar consultas de coyuntura economica entregando cifras verificadas
por tus herramientas, nunca estimaciones propias.

FECHA ACTUAL: {now.strftime('%d/%m/%Y')} (hora de Guatemala).

REGLAS:
1. Nunca inventes cifras. Todo numero debe venir de una herramienta.
2. Si una herramienta devuelve un campo "error", informa que el dato no
   esta disponible. No lo sustituyas con una estimacion.
3. Siempre indica la fuente y el año o fecha del dato.
4. Llama solo a las herramientas necesarias para responder.
5. Cuando uses graficar_bm, NO insertes la imagen en tu respuesta ni uses
   sintaxis de markdown para imagenes. El grafico se muestra
   automaticamente. Limitate a describir en una o dos lineas que muestra y
   citar la fuente.
6. Cuando uses ficha_pais, no repitas todas las cifras en tu respuesta.
   La ficha se muestra automaticamente. Comenta en dos o tres lineas lo
   mas relevante del perfil.
7. No uses el simbolo $ en tus respuestas. Escribe "USD" o "US dolares"
   en su lugar (por ejemplo: "123 mil millones de USD"). El simbolo $
   rompe el formato de la interfaz.
8. Cuando uses comparar_paises, apoyate en los campos "analisis" y
   "resumen" para comentar. No calcules diferencias por tu cuenta.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "indicador_bm",
            "description": (
                "Consulta indicadores macroeconomicos de un pais segun el Banco "
                "Mundial. Categorias disponibles: actividad economica "
                "(pib, pib_per_capita, pib_real_crecimiento), precios (inflacion), "
                "poblacion y empleo (poblacion, desempleo, participacion_laboral), "
                "sector externo (exportaciones, importaciones, balanza_comercial, "
                "cuenta_corriente, ied_entrada), remesas (remesas, remesas_pct_pib), "
                "finanzas publicas, sector financiero, desarrollo y estructura economica. "
                "Si el indicador solicitado no existe, la herramienta devuelve la lista completa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": "Codigo ISO3 del pais, por ejemplo GTM, MEX, USA"
                    },
                    "indicador": {
                        "type": "string",
                        "description": (
                            "Nombre del indicador en minusculas. Ejemplos: pib, "
                            "pib_per_capita, inflacion, poblacion, desempleo, "
                            "remesas, remesas_pct_pib, exportaciones, importaciones, "
                            "gini, tasa_prestamos, servicios_pct_pib. Hay mas "
                            "disponibles: si el solicitado no existe, la herramienta "
                            "devuelve la lista completa de validos."
                        )
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Años de historia a devolver. Por defecto 5"
                    }
                },
                "required": ["pais", "indicador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_moneda",
            "description": (
                "Convierte un monto entre dos monedas. "
                "Devuelve el monto convertido y el tipo de cambio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {
                        "type": "number",
                        "description": "Monto a convertir"
                    },
                    "origen": {
                        "type": "string",
                        "description": "Codigo de la moneda de origen, por ejemplo USD o EUR"
                    },
                    "destino": {
                        "type": "string",
                        "description": "Codigo de la moneda de destino, por ejemplo GTQ o USD"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fecha_hora",
            "description": (
                "Devuelve la fecha y hora actual en Guatemala. Usar cuando la "
                "pregunta involucre referencias temporales como hoy, este mes "
                "o el año pasado."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "graficar_bm",
            "description": (
                "Genera un grafico de linea con la evolucion historica de un "
                "indicador del Banco Mundial. Usar cuando el usuario pida ver, "
                "graficar o visualizar la tendencia de un indicador a lo largo "
                "del tiempo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": "Codigo ISO3 del pais, por ejemplo GTM"
                    },
                    "indicador": {
                        "type": "string",
                        "description": "Nombre del indicador, los mismos de indicador_bm"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Años de historia a graficar. Por defecto 10"
                    }
                },
                "required": ["pais", "indicador"]
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "comparar_paises",
            "description": (
                "Compara la evolucion de un mismo indicador economico entre "
                "dos y cinco paises. Usar cuando el usuario pida comparar, "
                "contrastar o ver diferencias entre paises."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "paises": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Codigos ISO3, por ejemplo ['GTM', 'MEX', 'CRI']"
                    },
                    "indicador": {
                        "type": "string",
                        "description": "Nombre del indicador, los mismos de indicador_bm"
                    },
                    "anios": {
                        "type": "integer",
                        "description": "Años de historia. Por defecto 10"
                    }
                },
                "required": ["paises", "indicador"]
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "ficha_pais",
            "description": (
                "Devuelve el perfil macroeconomico completo de un pais: PIB, "
                "PIB per capita, crecimiento, inflacion, poblacion, desempleo, "
                "pobreza y esperanza de vida, con la variacion respecto al año "
                "anterior. Usar cuando el usuario pida un panorama, resumen o "
                "perfil general de un pais, en vez de llamar indicador_bm "
                "varias veces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": "Codigo ISO3 del pais, por ejemplo GTM"
                    }
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sectores_pib",
            "description": (
                "Muestra la composicion del PIB de un pais por sector: "
                "agricultura, industria y servicios, como porcentaje del PIB. "
                "Usar cuando el usuario pregunte por la estructura economica, "
                "de que vive un pais, o el peso de los sectores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string",
                             "description": "Codigo ISO3, por ejemplo GTM"}
                },
                "required": ["pais"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mapa_indicador",
            "description": (
                "Muestra el valor mas reciente de un indicador para varios "
                "paises en un mapa coropletico. Usar cuando el usuario pida "
                "ver algo en un mapa, o comparar muchos paises en un solo "
                "momento. Para comparar la evolucion en el tiempo usa "
                "comparar_paises."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "paises": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Codigos ISO3, entre 2 y 20"
                    },
                    "indicador": {
                        "type": "string",
                        "description": "Nombre del indicador, los mismos de indicador_bm"
                    }
                },
                "required": ["paises", "indicador"]
            }
        }
    }
]


def process_response(client, memory_messages, user_text):
    """
    Envia la consulta al modelo y ejecuta las herramientas que pida.
    Devuelve una tupla: (texto de la respuesta, lista de resultados de herramientas).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory_messages)
    messages.append({"role": "user", "content": user_text})

    resultados = []          # lo que produjeron las herramientas

    while True:
        try:
            resp = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                tools=TOOLS
            )
        except Exception as e:
            return f"No pude procesar la consulta: {e}", resultados

        msg = resp.choices[0].message

        # Caso A: respuesta final, sin herramientas
        if not getattr(msg, "tool_calls", None):
            return msg.content or "", resultados

        # Caso B: pidio herramientas. Primero se guarda la peticion.
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
        })

        # Luego se ejecuta cada una y se guarda el resultado.
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if name == "indicador_bm":
                result = tools.consultar_indicador_banco_mundial(
                    pais=args["pais"],
                    indicador=args["indicador"],
                    anios=args.get("anios", 5)
                )
            elif name == "convertir_moneda":
                result = tools.convertir_moneda(
                    monto=args.get("monto", 1),
                    origen=args.get("origen", "USD"),
                    destino=args.get("destino", "GTQ")
                )
            elif name == "fecha_hora":
                result = tools.obtener_fecha_hora()
            elif name == "graficar_bm":
                result = tools.graficar_indicador(
                    pais=args["pais"],
                    indicador=args["indicador"],
                    anios=args.get("anios", 10)
                )
            elif name == "comparar_paises":
                result = tools.comparar_paises(
                    paises=args["paises"],
                    indicador=args["indicador"],
                    anios=args.get("anios", 10)
                )
            elif name == "ficha_pais":
                result = tools.ficha_pais(pais=args["pais"])
            elif name == "sectores_pib":
                result = tools.composicion_sectorial(pais=args["pais"])
            elif name == "mapa_indicador":
                result = tools.mapa_indicador(
                    paises=args["paises"],
                    indicador=args["indicador"]
                )
            else:
                result = {"error": f"Herramienta desconocida: {name}"}

            resultados.append({"herramienta": name, "resultado": result})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        # sin return: el while vuelve a llamar al modelo


if __name__ == "__main__":
    print("Agente Economico Keynes")
    print("Escribe 'salir' para terminar.\n")

    while True:
        user_text = input("Tú: ").strip()
        if not user_text:
            continue
        if user_text.lower() in ("exit", "salir"):
            print("Hasta luego!")
            break

        assistant_text, resultados = process_response(
            client, memory.messages(), user_text
        )

        for r in resultados:
            print(f"   [{r['herramienta']}]")

        print(f"Keynes: {assistant_text}\n")

        memory.add("user", user_text)
        memory.add("assistant", assistant_text)