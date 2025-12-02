import streamlit as st
import streamlit.components.v1 as components
import jwt
import os
import requests
from functools import lru_cache
from web3 import Web3

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

# --- CARGAR SECRETOS DE FORMA SEGURA ---
try:
    PRIVY_APP_ID = st.secrets["PRIVY_APP_ID"]
    PRIVY_APP_SECRET = st.secrets["PRIVY_APP_SECRET"]
except KeyError as e:
    st.error(f"❌ Error: El secreto '{e.args[0]}' no fue encontrado.")
    st.info("Por favor, configura los secretos en Streamlit Cloud:")
    st.code("""
PRIVY_APP_ID = "tu-app-id"
PRIVY_APP_SECRET = "tu-app-secret"
    """)
    st.stop()

# --- FUNCIÓN PARA OBTENER LA CLAVE PÚBLICA DE PRIVY ---
@lru_cache(maxsize=1)
def get_privy_public_key():
    """Obtiene la clave pública de Privy para verificar tokens JWT"""
    try:
        response = requests.get(
            f"https://auth.privy.io/api/v1/apps/{PRIVY_APP_ID}/.well-known/jwks.json",
            timeout=10
        )
        if response.status_code == 200:
            jwks = response.json()
            if jwks.get("keys"):
                return jwks["keys"][0]
    except Exception as e:
        st.warning(f"⚠️ No se pudo obtener la clave pública de Privy: {e}")
    return None

# --- FUNCIÓN PARA VERIFICAR EL TOKEN JWT DE PRIVY ---
def verify_privy_token(token):
    """
    Verifica un token JWT de Privy y extrae la información del usuario.
    Retorna un diccionario con los datos del usuario si es válido, None si no.
    """
    try:
        public_key_data = get_privy_public_key()
        
        if not public_key_data:
            st.error("❌ No se pudo obtener la clave pública de Privy")
            return None
        
        try:
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(public_key_data)
        except Exception:
            public_key = public_key_data
        
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=PRIVY_APP_ID,
            issuer="https://auth.privy.io"
        )
        
        return decoded
    
    except jwt.ExpiredSignatureError:
        st.error("❌ El token ha expirado")
        return None
    except jwt.InvalidTokenError as e:
        st.error(f"❌ Token inválido: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error al verificar el token: {e}")
        return None

# --- FUNCIÓN PARA VERIFICAR NFT CON WEB3 ---
def verify_nft_ownership(wallet_address):
    """
    Verifica si una dirección de billetera posee el NFT requerido en Arbitrum.
    Retorna True si posee el NFT, False si no.
    """
    try:
        # Conectar a Arbitrum
        w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
        
        if not w3.is_connected():
            st.error("❌ No se pudo conectar a la red Arbitrum")
            return False, None
        
        # ERC721 ABI simplificado (solo necesitamos balanceOf)
        ERC721_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Crear instancia del contrato
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(NFT_CONTRACT_ADDRESS),
            abi=ERC721_ABI
        )
        
        # Verificar balance
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        
        if balance > 0:
            return True, {"balance": balance, "contract": NFT_CONTRACT_ADDRESS}
        else:
            return False, None
            
    except Exception as e:
        st.error(f"❌ Error al verificar NFT: {e}")
        return False, None

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
        st.session_state.authenticated = False
        st.session_state.user_wallet = None
        st.session_state.user_nfts = None
        st.rerun()

else:
    st.subheader("Paso 1: Conecta tu Billetera")
    st.caption("Haz clic en el botón para conectar tu billetera de forma segura con Privy.")
    
    try:
        component_path = os.path.join('components', 'privy_component.html')
        
        if not os.path.exists(component_path):
            st.error(f"❌ Error: No se encontró el archivo '{component_path}'")
            st.info("Asegúrate de que la carpeta 'components' y el archivo 'privy_component.html' existan en tu repositorio.")
            st.stop()
        
        with open(component_path, 'r') as f:
            html_content = f.read()
        
        html_content = html_content.replace('{{PRIVY_APP_ID}}', PRIVY_APP_ID)
        
        component_value = components.html(html_content, height=100)

        # Verificar que component_value es un diccionario válido
        if component_value and isinstance(component_value, dict):
            if 'error' in component_value:
                st.error(f"❌ Error de autenticación: {component_value['error']}")
            elif 'token' in component_value:
                access_token = component_value['token']
                wallet_address = component_value.get('wallet')
                
                with st.spinner("🔍 Verificando token y buscando tu NFT..."):
                    try:
                        decoded_token = verify_privy_token(access_token)
                        
                        if decoded_token is None:
                            st.error("❌ No se pudo verificar el token")
                            st.stop()
                        
                        user_did = decoded_token.get('sub')
                        st.success(f"✅ Token verificado. Usuario: `{user_did}`")

                        if not wallet_address:
                            st.error("❌ No se pudo obtener la dirección de billetera")
                            st.info("Por favor, intenta de nuevo")
                            st.stop()
                        
                        st.success(f"✅ Billetera conectada: `{wallet_address}`")

                        st.info("🔍 Verificando NFT en Arbitrum...")
                        has_nft, nfts = verify_nft_ownership(wallet_address)

                        if has_nft:
                            st.session_state.authenticated = True
                            st.session_state.user_wallet = wallet_address
                            st.session_state.user_nfts = nfts
                            st.success("✅ ¡NFT verificado! Acceso concedido.")
                            st.rerun()
                        else:
                            st.warning("❌ Acceso Denegado")
                            st.error("La billetera conectada no posee el NFT requerido en Arbitrum.")
                            st.info(f"Contrato requerido: `{NFT_CONTRACT_ADDRESS}`")
                            st.info(f"Red: Arbitrum")

                    except Exception as e:
                        st.error(f"❌ Error durante la verificación: {str(e)}")
                        st.info("Por favor, verifica que tus credenciales sean correctas.")
        else:
            # Si no hay datos del componente, simplemente mostrar el botón de nuevo
            st.info("👆 Haz clic en el botón de arriba para conectar tu billetera")

    except FileNotFoundError:
        st.error("❌ Error: No se encontró el archivo 'components/privy_component.html'")
        st.info("Asegúrate de que la carpeta 'components' y el archivo 'privy_component.html' existan en tu repositorio.")
