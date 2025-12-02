from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime, timedelta
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Permitir CORS para que Streamlit pueda hacer peticiones
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenar datos de autenticación temporalmente
# En producción, usar una base de datos
auth_sessions = {}

# --- RUTAS ---

@app.get("/")
async def get_auth_page():
    """Servir la página HTML de autenticación"""
    logger.info("GET / - Sirviendo página de autenticación")
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        logger.error(f"Archivo no encontrado: {template_path}")
        raise HTTPException(status_code=404, detail="Archivo index.html no encontrado")
    return FileResponse(template_path)

@app.post("/api/auth/save")
async def save_auth(data: dict):
    """
    Guardar datos de autenticación.
    Llamado por la ventana emergente después de firmar.
    """
    logger.info(f"POST /api/auth/save - Recibiendo datos: {data}")
    try:
        wallet = data.get("wallet")
        signature = data.get("signature")
        message = data.get("message")
        
        logger.info(f"Wallet: {wallet}, Signature length: {len(signature) if signature else 0}, Message: {message[:50] if message else 'None'}...")
        
        if not wallet or not signature or not message:
            logger.error("Datos incompletos en la solicitud")
            raise HTTPException(status_code=400, detail="Datos incompletos")
        
        # Generar un ID de sesión único
        session_id = wallet.lower()
        
        # Guardar los datos con un timestamp de expiración (5 minutos)
        auth_sessions[session_id] = {
            "wallet": wallet,
            "signature": signature,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        
        logger.info(f"✅ Datos guardados para {session_id}")
        logger.info(f"Sessions actuales: {list(auth_sessions.keys())}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Datos guardados correctamente"
        }
    except Exception as e:
        logger.error(f"❌ Error al guardar: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/check/{wallet_address}")
async def check_auth(wallet_address: str):
    """
    Verificar si hay datos de autenticación para una billetera.
    Llamado por Streamlit para verificar si el usuario se autenticó.
    """
    logger.info(f"GET /api/auth/check/{wallet_address}")
    try:
        session_id = wallet_address.lower()
        
        logger.info(f"Buscando sesión: {session_id}")
        logger.info(f"Sessions disponibles: {list(auth_sessions.keys())}")
        
        if session_id not in auth_sessions:
            logger.warning(f"No hay datos para {session_id}")
            return {
                "authenticated": False,
                "message": "No hay datos de autenticación"
            }
        
        session_data = auth_sessions[session_id]
        
        # Verificar si la sesión ha expirado
        expires = datetime.fromisoformat(session_data["expires"])
        if datetime.now() > expires:
            logger.warning(f"Sesión expirada para {session_id}")
            del auth_sessions[session_id]
            return {
                "authenticated": False,
                "message": "La sesión ha expirado"
            }
        
        # Devolver los datos
        logger.info(f"✅ Datos encontrados para {session_id}")
        return {
            "authenticated": True,
            "wallet": session_data["wallet"],
            "signature": session_data["signature"],
            "message": session_data["message"]
        }
    except Exception as e:
        logger.error(f"❌ Error al verificar: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth/clear/{wallet_address}")
async def clear_auth(wallet_address: str):
    """
    Limpiar datos de autenticación.
    Llamado por Streamlit cuando el usuario cierra sesión.
    """
    logger.info(f"DELETE /api/auth/clear/{wallet_address}")
    try:
        session_id = wallet_address.lower()
        if session_id in auth_sessions:
            del auth_sessions[session_id]
            logger.info(f"✅ Sesión limpiada para {session_id}")
        
        return {
            "status": "success",
            "message": "Sesión cerrada"
        }
    except Exception as e:
        logger.error(f"❌ Error al limpiar: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/sessions")
async def debug_sessions():
    """
    Endpoint de debugging para ver todas las sesiones actuales.
    SOLO PARA DESARROLLO - Eliminar en producción
    """
    logger.info("GET /api/debug/sessions")
    return {
        "sessions": list(auth_sessions.keys()),
        "count": len(auth_sessions),
        "data": auth_sessions
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor FastAPI en puerto 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
