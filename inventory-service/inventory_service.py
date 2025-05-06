from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.exceptions import BadRequest
import uuid
import time
from prometheus_client import Counter, Gauge, Histogram

app = Flask(__name__)
metrics = PrometheusMetrics(app, defaults_prefix='flask')  # Use exporter for default metrics

# Custom metrics
product_requests_total = Counter('product_requests_total', 'Total number of product requests', ['method', 'endpoint'])
product_errors_total = Counter('product_errors_total', 'Total number of errors in product requests', ['method', 'endpoint'])
product_inventory_value = Gauge('product_inventory_value', 'Total value of inventory (price * quantity)')
product_request_duration = Histogram(
    'product_request_duration_seconds',
    'Request duration for product endpoints',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 5.0]
)
product_count = Gauge('product_count', 'Total number of products in inventory')
product_creation_success_total = Counter('product_creation_success_total', 'Total number of successful product creations')
product_low_stock = Gauge('product_low_stock', 'Number of products with low stock (quantity < 10)')
product_price_distribution = Histogram(
    'product_price_distribution',
    'Distribution of product prices',
    buckets=[10, 50, 100, 500, 1000]
)

# In-memory storage for products
products = {}

def update_inventory_metrics():
    total_value = sum(p['price'] * p['quantity'] for p in products.values())
    product_inventory_value.set(total_value)
    product_count.set(len(products))
    low_stock_count = sum(1 for p in products.values() if p['quantity'] < 10)
    product_low_stock.set(low_stock_count)

# Custom decorator to track request duration
def track_duration(method, endpoint):
    def decorator(f):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                product_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                product_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
                raise e
        wrapper.__name__ = f.__name__  # Preserve function name for Flask
        return wrapper
    return decorator

@app.route('/inventory/products', methods=['GET'])
@track_duration('GET', '/products')
def get_products():
    product_requests_total.labels(method='GET', endpoint='/products').inc()
    return jsonify(list(products.values()))

@app.route('/inventory/products/<id>', methods=['GET'])
@track_duration('GET', '/products/<id>')
def get_product(id):
    product_requests_total.labels(method='GET', endpoint='/products/<id>').inc()
    if id not in products:
        product_errors_total.labels(method='GET', endpoint='/products/<id>').inc()
        return jsonify({'message': 'Product not found'}), 404
    return jsonify(products[id])

@app.route('/inventory/products', methods=['POST'])
@track_duration('POST', '/products')
def create_product():
    product_requests_total.labels(method='POST', endpoint='/products').inc()
    try:
        data = request.get_json()
    except BadRequest:
        product_errors_total.labels(method='POST', endpoint='/products').inc()
        return jsonify({'message': 'Invalid JSON data'}), 400
    if not all(key in data for key in ['name', 'price', 'quantity']):
        product_errors_total.labels(method='POST', endpoint='/products').inc()
        return jsonify({'message': 'Invalid product data'}), 400
    product_id = str(uuid.uuid1())
    product = {
        'id': product_id,
        'name': data['name'],
        'price': float(data['price']),
        'quantity': int(data['quantity'])
    }
    products[product_id] = product
    product_price_distribution.observe(product['price'])
    product_creation_success_total.inc()
    update_inventory_metrics()
    return jsonify(product), 201

@app.route('/inventory/products/<id>', methods=['PUT'])
@track_duration('PUT', '/products/<id>')
def update_product(id):
    product_requests_total.labels(method='PUT', endpoint='/products/<id>').inc()
    if id not in products:
        product_errors_total.labels(method='PUT', endpoint='/products/<id>').inc()
        return jsonify({'message': 'Product not found'}), 404
    try:
        data = request.get_json()
    except BadRequest:
        product_errors_total.labels(method='PUT', endpoint='/products/<id>').inc()
        return jsonify({'message': 'Invalid JSON data'}), 400
    if not all(key in data for key in ['name', 'price', 'quantity']):
        product_errors_total.labels(method='PUT', endpoint='/products/<id>').inc()
        return jsonify({'message': 'Invalid product data'}), 400
    product = {
        'id': id,
        'name': data['name'],
        'price': float(data['price']),
        'quantity': int(data['quantity'])
    }
    products[id] = product
    product_price_distribution.observe(product['price'])
    update_inventory_metrics()
    return jsonify(product)

@app.route('/inventory/products/<id>', methods=['DELETE'])
@track_duration('DELETE', '/products/<id>')
def delete_product(id):
    product_requests_total.labels(method='DELETE', endpoint='/products/<id>').inc()
    if id not in products:
        product_errors_total.labels(method='DELETE', endpoint='/products/<id>').inc()
        return jsonify({'message': 'Product not found'}), 404
    del products[id]
    update_inventory_metrics()
    return jsonify({}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)