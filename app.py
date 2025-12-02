import streamlit as st
import requests
import time
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="NFT Gated App",
    page_icon="🔐",
    layout="centered"
)

# --- CONFIGURACIÓN DEL TOKEN GATING ---
NFT_CONTRACT_ADDRESS = "0xF4820467171695F4d2760614C77503147A9CB1E8"
CHAIN = "arbitrum"
ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

# URL del servidor FastAPI - CAMBIAR ESTO A TU URL DE RAILWAY
FASTAPI_SERVER_URL = "https://privy-moralis-streamlit-production.up.railway.app"  # Cambiar a tu URL de Railway

# --- INTERFAZ DE USUARIO ---
st.title("🔐 Acceso Exclusivo para Holders")
st.write("Conecta tu billetera para verificar que posees el NFT requerido y accede al contenido exclusivo.")
st.divider()

# --- LÓGICA DE AUTENTICACIÓN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user_wallet' not in st.session_state:
    st.session_state.user_wallet = None

if 'user_nfts' not in st.session_state:
    st.session_state.user_nfts = None

# --- FUNCIÓN PARA VERIFICAR NFT CON WEB3 ---
def verify_nft_ownership(wallet_address):
    """
    Verifica si una dirección de billetera posee el NFT requerido en Arbitrum.
    """
    try:
        w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
        if not w3.is_connected():
            st.error("❌ No se pudo conectar a la red Arbitrum")
            return False, None
        
        ERC721_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS),
            abi=ERC721_ABI
        )
        
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        
        if balance > 0:
            return True, {"balance": balance, "contract": NFT_CONTRACT_ADDRESS}
        else:
            return False, None
            
    except Exception as e:
        st.error(f"❌ Error al verificar NFT: {e}")
        return False, None

# --- FUNCIÓN PARA VERIFICAR FIRMA ---
def verify_signature(wallet_address, message, signature):
    """
    Verifica que la firma fue creada por la billetera especificada.
    """
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        st.error(f"❌ Error al verificar firma: {e}")
        return False

# --- FUNCIÓN PARA CONSULTAR EL SERVIDOR FASTAPI ---
def check_auth_on_server(wallet_address):
    """
    Consultar el servidor FastAPI para ver si hay datos de autenticación.
    """
    try:
        response = requests.get(
            f"{FASTAPI_SERVER_URL}/api/auth/check/{wallet_address}",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"authenticated": False}
    except Exception as e:
        st.error(f"❌ Error al conectar con el servidor: {e}")
        return {"authenticated": False}

# --- FUNCIÓN PARA LIMPIAR AUTENTICACIÓN EN EL SERVIDOR ---
def clear_auth_on_server(wallet_address):
    """
    Limpiar datos de autenticación del servidor.
    """
    try:
        requests.delete(
            f"{FASTAPI_SERVER_URL}/api/auth/clear/{wallet_address}",
            timeout=5
        )
    except:
        pass

# Si el usuario está autenticado, muestra el contenido
if st.session_state.authenticated:
    st.success("✅ ¡Autenticación y verificación completadas! Bienvenido.")
    st.balloons()
    
    st.info(f"Billetera conectada: `{st.session_state.user_wallet}`")
    
    if st.session_state.user_nfts:
        st.subheader("📜 Información del NFT")
        st.write(f"**Balance:** {st.session_state.user_nfts.get('balance', 0)} NFT(s)")
        st.write(f"**Contrato:** `{st.session_state.user_nfts.get('contract', 'N/A')}`")
    
    st.header("🎁 Contenido Exclusivo")
    st.write("""
    Este es el contenido que solo pueden ver los holders del NFT.
    
    Aquí puedes poner:
    - Documentos privados
    - Videos exclusivos
    - Acceso a herramientas especiales
    - Información confidencial
    - Lo que necesites proteger
    """)
    
    if st.button("🚪 Cerrar Sesión"):
        clear_auth_on_server(st.session_state.user_wallet)
        st.session_state.authenticated = False
        st.session_state.user_wallet = None
        st.session_state.user_nfts = None
        st.rerun()

else:
    st.subheader("Paso 1: Conecta tu Billetera")
    st.caption("Haz clic en el botón para abrir la ventana de autenticación.")
    
    # Botón para abrir la ventana de autenticación
    st.link_button("🔗 Conectar Billetera", f"{FASTAPI_SERVER_URL}")
    
    st.info("Después de autenticarte, vuelve a esta página y pega tu dirección de billetera en el campo de abajo.")
    
    st.divider()
    st.subheader("Paso 2: Verifica tu Autenticación")
    st.caption("Pega tu dirección de billetera después de autenticarte:")
    
    wallet_input = st.text_input("Dirección de billetera (0x...):")
    
    if wallet_input:
        if not wallet_input.startswith("0x") or len(wallet_input) != 42:
            st.error("❌ Dirección inválida. Debe empezar con 0x y tener 42 caracteres.")
        else:
            # Mostrar un spinner mientras verificamos
            with st.spinner("🔍 Verificando autenticación y NFT..."):
                # Consultar el servidor para ver si hay datos de autenticación
                auth_result = check_auth_on_server(wallet_input)
                
                if auth_result.get("authenticated"):
                    wallet_address = auth_result.get("wallet")
                    signature = auth_result.get("signature")
                    message = auth_result.get("message")
                    
                    # Verificar la firma
                    if verify_signature(wallet_address, message, signature):
                        st.success(f"✅ Firma verificada. Billetera: `{wallet_address}`")
                        
                        # Verificar NFT
                        has_nft, nfts = verify_nft_ownership(wallet_address)
                        if has_nft:
                            st.session_state.authenticated = True
                            st.session_state.user_wallet = wallet_address
                            st.session_state.user_nfts = nfts
                            st.success("✅ ¡NFT verificado! Acceso concedido.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("❌ Acceso Denegado")
                            st.error("La billetera conectada no posee el NFT requerido en Arbitrum.")
                            st.info(f"Contrato requerido: `{NFT_CONTRACT_ADDRESS}`")
                            st.info(f"Red: Arbitrum")
                    else:
                        st.error("❌ La firma no es válida")
                else:
                    st.warning("⚠️ No se encontraron datos de autenticación para esta billetera.")
                    st.info("Asegúrate de haber completado el proceso de autenticación en la ventana emergente.")
                    st.info("Si ya completaste el proceso, intenta pegar tu dirección de nuevo.")
