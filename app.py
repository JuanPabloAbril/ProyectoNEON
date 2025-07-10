from flask import Flask, render_template
from extensions import db
import os
from dotenv import load_dotenv
from routes import routes  

# Carga variables de entorno desde .env si está local
load_dotenv()

# Debug: imprime la URL de la base de datos
raw_uri = os.getenv("DATABASE_URL")
print("DATABASE_URL (original):", raw_uri)

# Valida que la URI exista
if not raw_uri:
    raise RuntimeError("❌ ERROR: La variable de entorno DATABASE_URL no está definida.")

# Reemplaza postgres:// por postgresql:// si es necesario
if raw_uri.startswith("postgres://"):
    raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)
    print("DATABASE_URL corregido:", raw_uri)

# Configuración de la app Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = raw_uri
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "clave_secreta_default")

# Inicializar SQLAlchemy con la app
db.init_app(app)

# Registrar rutas
app.register_blueprint(routes)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    # Crear las tablas si no existen
    with app.app_context():
        db.create_all()

    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=5000, debug=True)

