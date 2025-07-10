from flask import Flask, render_template
from extensions import db
import os
from dotenv import load_dotenv
from routes import routes  

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

db.init_app(app)

app.register_blueprint(routes)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
