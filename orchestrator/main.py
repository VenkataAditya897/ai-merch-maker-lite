from flask import Flask, render_template
from state import StateDB

app = Flask(__name__)

@app.route('/')
def products():
    db = StateDB()
    products = db.get_all_records()  
    return render_template('products.html', products=products)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
