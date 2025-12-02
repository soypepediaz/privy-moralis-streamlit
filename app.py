import streamlit as st
import streamlit.components.v1 as components
import os
from web3 import Web3
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

# --- FUNCIÓN PARA VERIFICAR FIRMA ---
def verify_signature(wallet_address, message, signature):
    """
    Verifica que la firma fue creada por la billetera especificada.
    """
    try:
        # Crear el mensaje con el formato de Ethereum
        message_hash = encode_defunct(text=message)
        
        # Recuperar la dirección que firmó el mensaje
        recovered_address = Web3.eth.Account.recover_message(message_hash, signature=signature)
        
        # Comparar direcciones (case-insensitive)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        st.error(f"❌ Error al verificar firma: {e}")
        return False

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
    st.caption("Haz clic en el botón para conectar tu billetera de forma segura con WalletConnect.")
    
    try:
        component_path = os.path.join('components', 'walletconnect_component.html')
        
        if not os.path.exists(component_path):
            st.error(f"❌ Error: No se encontró el archivo '{component_path}'")
            st.info("Asegúrate de que la carpeta 'components' y el archivo 'walletconnect_component.html' existan en tu repositorio.")
            st.stop()
        
        with open(component_path, 'r') as f:
            html_content = f.read()
        
        component_value = components.html(html_content, height=100)

        # Verificar que component_value es un diccionario válido
        if component_value and isinstance(component_value, dict):
            if 'error' in component_value:
                st.error(f"❌ Error de autenticación: {component_value['error']}")
            elif 'wallet' in component_value:
                wallet_address = component_value['wallet']
                signature = component_value.get('signature')
                message = component_value.get('message')
                
                with st.spinner("🔍 Verificando firma y buscando tu NFT..."):
                    try:
                        # Verificar que la firma es válida
                        if not verify_signature(wallet_address, message, signature):
                            st.error("❌ La firma no es válida")
                            st.stop()
                        
                        st.success(f"✅ Firma verificada. Billetera: `{wallet_address}`")

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
                        st.info("Por favor, intenta de nuevo.")
        else:
            # Si no hay datos del componente, simplemente mostrar el botón de nuevo
            st.info("👆 Haz clic en el botón de arriba para conectar tu billetera")

    except FileNotFoundError:
        st.error("❌ Error: No se encontró el archivo 'components/walletconnect_component.html'")
        st.info("Asegúrate de que la carpeta 'components' y el archivo 'walletconnect_component.html' existan en tu repositorio.")
