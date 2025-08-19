import json

def update_env_from_json():
    try:
        # Lee el archivo JSON
        with open('serviceAccountKey.json', 'r') as f:
            creds = json.load(f)
        
        # Lee el archivo .env actual para mantener variables no relacionadas con Firebase
        env_other_vars = {}
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.strip() and not line.strip().startswith('#'):
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if not key.startswith('FIREBASE_'):
                                env_other_vars[key] = value
        except:
            pass

        # La clave privada necesita un tratamiento especial
        private_key = creds['private_key'].replace('\n', '\\n')

        # Crea el nuevo contenido del .env
        env_content = [
            "# Firebase Configuration",
            f"FIREBASE_TYPE={creds['type']}",
            f"FIREBASE_PROJECT_ID={creds['project_id']}",
            f"FIREBASE_PRIVATE_KEY_ID={creds['private_key_id']}",
            f"FIREBASE_PRIVATE_KEY={private_key}",  # Sin comillas triples
            f"FIREBASE_CLIENT_EMAIL={creds['client_email']}",
            f"FIREBASE_CLIENT_ID={creds['client_id']}",
            f"FIREBASE_AUTH_URI={creds['auth_uri']}",
            f"FIREBASE_TOKEN_URI={creds['token_uri']}",
            f"FIREBASE_AUTH_PROVIDER_X509_CERT_URL={creds['auth_provider_x509_cert_url']}",
            f"FIREBASE_CLIENT_X509_CERT_URL={creds['client_x509_cert_url']}",
            f"FIREBASE_API_KEY=AIzaSyCKE2jIyXfEbaXIoWmjKRYj0A0v7sTx-mY",
            f"FIREBASE_WEB_API_KEY=AIzaSyCKE2jIyXfEbaXIoWmjKRYj0A0v7sTx-mY",
            "",
            "# Other Configuration"
        ]

        # Añade las otras variables que no son de Firebase
        for key, value in env_other_vars.items():
            if key not in ['FIREBASE_API_KEY', 'FIREBASE_WEB_API_KEY']:
                env_content.append(f"{key}={value}")

        # Guarda el nuevo archivo .env
        with open('.env', 'w') as f:
            f.write('\n'.join(env_content))
        
        print("✅ Archivo .env actualizado correctamente")
        
    except Exception as e:
        print(f"❌ Error actualizando .env: {str(e)}")

if __name__ == "__main__":
    update_env_from_json()