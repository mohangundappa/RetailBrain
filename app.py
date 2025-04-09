import os
import logging
from flask import Flask
from api.routes import api_bp

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "staples-brain-secret-key")

# Register blueprints
app.register_blueprint(api_bp)

# Import and initialize Staples Brain
from brain.staples_brain import initialize_staples_brain
staples_brain = initialize_staples_brain()

logger.info("Staples Brain initialized successfully")

# Default route
@app.route('/')
def index():
    from flask import render_template
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
