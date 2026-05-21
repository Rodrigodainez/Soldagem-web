from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route("/")
def home():

    with open("itens.json", "r", encoding="utf-8") as f:
        itens = json.load(f)

    return render_template("index.html", itens=itens)

if __name__ == "__main__":
    app.run(debug=True)