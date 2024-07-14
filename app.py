from flask import Flask, request, jsonify, render_template
from sqlalchemy import create_engine, Column, Integer, String, Numeric, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import subprocess
import json
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import openai
import yaml
import logging
import re

# Ensure the OpenAI API key is set from the environment
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
openai.api_key = openai_api_key

# Set up the SQLite database connection
engine = create_engine('sqlite:///products.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Define the Product model
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Numeric, nullable=False)

class ProductData(Base):
    __tablename__ = 'product_data'
    id = Column(Integer, primary_key=True)
    data = Column(JSON)
    tags = Column(String)

print("Defining Product model...")

# Create the table in the database
print("Creating database tables...")
Base.metadata.create_all(engine)
print("Database tables created.")

# Define the main application object
app = Flask(__name__, static_folder='static', template_folder='templates')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_keyword_mappings():
    config_path = os.path.join(os.path.dirname(__file__), 'keyword_mappings.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def load_spider_rules():
    config_path = os.path.join(os.path.dirname(__file__), 'spider_rules.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def update_keyword_mappings(new_mappings):
    config_path = os.path.join(os.path.dirname(__file__), 'keyword_mappings.yaml')
    with open(config_path, 'w') as file:
        yaml.safe_dump(new_mappings, file)

def update_spider_rules(new_rules):
    config_path = os.path.join(os.path.dirname(__file__), 'spider_rules.yaml')
    with open(config_path, 'w') as file:
        yaml.safe_dump(new_rules, file)

def analyze_data(data):
    tags = []
    keyword_mappings = load_keyword_mappings()

    # Ensure data is a string and normalize it
    if isinstance(data, dict):
        data_str = json.dumps(data).lower()
    elif isinstance(data, str):
        data_str = data.lower()
    else:
        logging.error("Unsupported data type for analysis")
        return tags

    # Match product keywords
    for keyword, tag in keyword_mappings['products'].items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', data_str):
            tags.append(tag)

    # Match regulation keywords
    for keyword, tag in keyword_mappings['regulations'].items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', data_str):
            tags.append(tag)

    # Match additional tags
    for keyword, tag in keyword_mappings['tags'].items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', data_str):
            tags.append(tag)

    logging.info(f"Data analyzed with tags: {tags}")
    return tags

def process_new_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        validate_data(data)
        tags = analyze_data(data)
        store_data(data, tags)
        move_data(file_path, tags)
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")

def validate_data(data):
    if not isinstance(data, (str, dict)):
        raise ValueError("Data must be a string or dictionary")
    return True

def store_data(data, tags):
    try:
        existing_data = session.query(ProductData).filter_by(tags=','.join(tags)).first()
        if existing_data:
            existing_data.data.update(data)
            session.commit()
        else:
            new_data = ProductData(data=data, tags=','.join(tags))
            session.add(new_data)
            session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Error storing data: {e}")

def move_data(file_path, tags):
    try:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        if 'product' in tags:
            target_folder = os.path.join(desktop_path, 'product_data')
        elif 'regulation' in tags:
            target_folder = os.path.join(desktop_path, 'regsdata')
        else:
            target_folder = desktop_path  # Default target if no tag matches

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        os.rename(file_path, os.path.join(target_folder, os.path.basename(file_path)))
    except Exception as e:
        logging.error(f"Error moving file {file_path}: {e}")

class DataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_new_file(event.src_path)

def start_monitoring(path):
    observer = Observer()
    observer.schedule(DataHandler(), path=path, recursive=False)
    observer.start()

# Start file monitoring in a separate thread
monitoring_thread = threading.Thread(target=start_monitoring, args=(os.path.join(os.path.expanduser('~'), 'Desktop', 'spidertest'),))
monitoring_thread.start()

# Define the route for the recommendation endpoint
@app.route('/recommend', methods=['POST'])
def recommend():
    print("Request Headers:", request.headers)
    print("Request Data:", request.data)

    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported Media Type"}), 415

    data = request.json
    print("Parsed JSON Data:", data)
    query = data.get('query', '')

    matching_products = session.query(Product).filter(Product.name.contains(query)).all()

    return jsonify([{
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': str(product.price)
    } for product in matching_products])

# Endpoint to start the Scrapy spider
@app.route('/start_spider', methods=['POST'])
def start_spider():
    config = request.json
    urls = config.get('urls', [])
    description = config.get('description', '')

    if not urls or not description:
        return jsonify({'error': 'URLs and description are required'}), 400

    try:
        # Here we assume 'product_spider' is the name of the spider and it can accept multiple URLs
        for url in urls:
            result = subprocess.run(['scrapy', 'crawl', 'product_spider', '-a', f'url={url}', '-a', f'description={description}'], check=True, capture_output=True, text=True)
            print(result.stdout)  # Logging output for debugging
        return jsonify({'message': 'Spider started successfully for all URLs'}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({'error': str(e), 'output': e.output}), 500

@app.route('/stop_spider', methods=['POST'])
def stop_spider():
    # Implement the logic to stop the spider
    # This is a placeholder implementation
    return jsonify({'message': 'Stop Spider functionality to be implemented'}), 200

@app.route('/organize_dumped_info', methods=['POST'])
def organize_dumped_info():
    info = request.json.get('info')
    if not info:
        return jsonify({"error": "No info provided"}), 400

    try:
        region = info.get('region', '').lower()
        if region not in ['uk', 'usa', 'australia']:
            return jsonify({"error": "Invalid region"}), 400

        categories = ['products', 'regulations', 'images']
        base_path = os.path.join(os.path.expanduser('~'), 'Desktop', region.capitalize())

        for category in categories:
            target_folder = os.path.join(base_path, category)
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)

            for item in info.get(category, []):
                item_path = os.path.join(target_folder, item['filename'])
                with open(item_path, 'w') as f:
                    json.dump(item, f)

        return jsonify({"message": "Info organized successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to recommend products based on local JSON file
@app.route('/local_recommend', methods=['POST'])
def local_recommend():
    data = request.json
    query = data.get('query', '')

    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'spidertest')
    file_path = os.path.join(desktop_path, 'products.json')

    try:
        with open(file_path, 'r') as f:
            products = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to load products: {e}"}), 500

    recommendations = [product for product in products if query.lower() in product['name'].lower()]

    return jsonify(recommendations)

# Route to serve the chatbox HTML
@app.route('/')
def index():
    return render_template('chatbox.html')

# Route to handle chatbox interactions
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"response": "No message received"}), 400

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"You: {user_message}\nAI:",
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.9,
        )
        ai_message = response.choices[0].text.strip()
        return jsonify({"response": ai_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_keyword_mappings', methods=['POST'])
def update_keyword_mappings():
    new_mappings = request.json
    update_keyword_mappings(new_mappings)
    return jsonify({"message": "Keyword mappings updated successfully"})

@app.route('/update_spider_rules', methods=['POST'])
def update_spider_rules():
    new_rules = request.json
    update_spider_rules(new_rules)
    return jsonify({"message": "Spider rules updated successfully"})

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True, host='0.0.0.0', port=5001)
