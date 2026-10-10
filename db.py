"""
Persistencia en Supabase: caché de indicadores e historial de conversaciones.

Principio de diseño: si Supabase no responde, la app sigue funcionando.
Ninguna funcion de este modulo lanza excepciones hacia afuera.
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    _url = os.environ.get("SUPABASE_URL")
    _key = os.environ.get("SUPABASE_KEY")
    cliente = create_client(_url, _key) if _url and _key else None
except Exception:
    cliente = None


def disponible() -> bool:
    """True si hay conexion configurada."""
    return cliente is not None

def leer_cache(llave: str):
    """Devuelve el payload guardado para esa llave, o None."""
    if cliente is None:
        return None
    try:
        r = (cliente.table("cache_indicadores")
             .select("payload")
             .eq("llave", llave)
             .limit(1)
             .execute())
        return r.data[0]["payload"] if r.data else None
    except Exception:
        return None


def guardar_cache(llave: str, payload: dict) -> None:
    """Guarda o actualiza el payload de esa llave."""
    if cliente is None:
        return
    try:
        (cliente.table("cache_indicadores")
         .upsert({"llave": llave, "payload": payload})
         .execute())
    except Exception:
        pass


def listar_sesiones(limite: int = 20) -> list:
    """Devuelve las conversaciones recientes: id de sesion, titulo y fecha."""
    if cliente is None:
        return []
    try:
        r = (cliente.table("conversaciones")
             .select("sesion, rol, texto, titulo, creado_en")
             .order("creado_en", desc=True)
             .limit(limite * 12)
             .execute())
    except Exception:
        return []

    # Las filas vienen de la mas reciente a la mas antigua
    sesiones = {}
    for fila in r.data:
        s = sesiones.setdefault(fila["sesion"], {
            "sesion": fila["sesion"],
            "titulo": None,
            "pregunta": None,
            "fecha": fila["creado_en"][:10],
        })
        if fila.get("titulo"):
            s["titulo"] = fila["titulo"]
        if fila["rol"] == "user":
            s["pregunta"] = fila["texto"][:60]  # termina siendo la primera

    # Las conversaciones viejas no tienen titulo: se usa su primera pregunta
    resultado = []
    for s in list(sesiones.values())[:limite]:
        resultado.append({
            "sesion": s["sesion"],
            "titulo": s["titulo"] or s["pregunta"] or "Conversación",
            "fecha": s["fecha"],
        })
    return resultado


def cargar_sesion(sesion: str) -> list:
    """Devuelve todos los mensajes de una sesion, en orden."""
    if cliente is None:
        return []
    try:
        r = (cliente.table("conversaciones")
             .select("rol, texto, visuales")
             .eq("sesion", sesion)
             .order("creado_en")
             .execute())
        return [{"rol": m["rol"], "texto": m["texto"],
                 "graficos": m.get("visuales") or []} for m in r.data]
    except Exception:
        return []


def borrar_sesion(sesion: str) -> None:
    """Elimina todos los mensajes de una conversacion."""
    if cliente is None:
        return
    try:
        cliente.table("conversaciones").delete().eq("sesion", sesion).execute()
    except Exception:
        pass

def guardar_mensaje(sesion: str, rol: str, texto: str, visuales=None,
                    titulo: str = None) -> None:
    """Guarda un turno de la conversacion (con titulo si es el primero)."""
    if cliente is None:
        return
    try:
        fila = {"sesion": sesion, "rol": rol, "texto": texto,
                "visuales": visuales or []}
        if titulo:
            fila["titulo"] = titulo
        cliente.table("conversaciones").insert(fila).execute()
    except Exception:
        pass