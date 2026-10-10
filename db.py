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
def guardar_mensaje(sesion: str, rol: str, texto: str, visuales=None) -> None:
    """Guarda un turno de la conversacion."""
    if cliente is None:
        return
    try:
        (cliente.table("conversaciones")
         .insert({
             "sesion": sesion,
             "rol": rol,
             "texto": texto,
             "visuales": visuales or [],
         })
         .execute())
    except Exception:
        pass


def listar_sesiones(limite: int = 20) -> list:
    """Devuelve las conversaciones recientes: id de sesion, primera pregunta y fecha."""
    if cliente is None:
        return []
    try:
        r = (cliente.table("conversaciones")
             .select("sesion, texto, creado_en")
             .eq("rol", "user")
             .order("creado_en", desc=True)
             .limit(limite * 6)
             .execute())
    except Exception:
        return []

    vistas, sesiones = set(), []
    for fila in r.data:
        if fila["sesion"] in vistas:
            continue
        vistas.add(fila["sesion"])
        sesiones.append({
            "sesion": fila["sesion"],
            "titulo": fila["texto"][:60],
            "fecha": fila["creado_en"][:10],
        })
        if len(sesiones) >= limite:
            break
    return sesiones


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
