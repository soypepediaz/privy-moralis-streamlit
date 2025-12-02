from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime, timedelta
import json

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
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    return FileResponse(template_path)

@app.post("/api/auth/save")
async def save_auth(data: dict):
    """
    Guardar datos de autenticación.
    Llamado por la ventana emergente después de firmar.
    """
    try:
        wallet = data.get("wallet")
        signature = data.get("signature")
        message = data.get("message")
        
        if not wallet or not signature or not message:
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
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Datos guardados correctamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/check/{wallet_address}")
async def check_auth(wallet_address: str):
    """
    Verificar si hay datos de autenticación para una billetera.
    Llamado por Streamlit para verificar si el usuario se autenticó.
    """
    try:
        session_id = wallet_address.lower()
        
        if session_id not in auth_sessions:
            return {
                "authenticated": False,
                "message": "No hay datos de autenticación"
            }
        
        session_data = auth_sessions[session_id]
        
        # Verificar si la sesión ha expirado
        expires = datetime.fromisoformat(session_data["expires"])
        if datetime.now() > expires:
            del auth_sessions[session_id]
            return {
                "authenticated": False,
                "message": "La sesión ha expirado"
            }
        
        # Devolver los datos
        return {
            "authenticated": True,
            "wallet": session_data["wallet"],
            "signature": session_data["signature"],
            "message": session_data["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth/clear/{wallet_address}")
async def clear_auth(wallet_address: str):
    """
    Limpiar datos de autenticación.
    Llamado por Streamlit cuando el usuario cierra sesión.
    """
    try:
        session_id = wallet_address.lower()
        if session_id in auth_sessions:
            del auth_sessions[session_id]
        
        return {
            "status": "success",
            "message": "Sesión cerrada"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
