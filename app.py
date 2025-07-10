from flask import Flask, render_template
from extensions import db
import os
from routes import routes  

# Obtener la URI de la base de datos desde variables de entorno
raw_uri = os.getenv("DATABASE_URL")

# Debug (solo se verá en logs de Railway)
print("DATABASE_URL (obtenido):", raw_uri)

# Validar que la URI exista
if not raw_uri:
    raise RuntimeError("❌ ERROR: La variable de entorno DATABASE_URL no está definida.")

# Reemplazar postgres:// por postgresql:// si es necesario
if raw_uri.startswith("postgres://"):
    raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)
    print("DATABASE_URL corregido:", raw_uri)

# Configurar la aplicación Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = raw_uri
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "clave_secreta_default")

# Inicializar la extensión de base de datos
db.init_app(app)

# Registrar las rutas (blueprint)
app.register_blueprint(routes)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crear las tablas si no existen

    app.run(host='0.0.0.0', port=5000, debug=True)
