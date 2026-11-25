import os
from flask import Flask, render_template, jsonify

app = Flask(_name_)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/config")
def config():
    return jsonify({
        "supabaseUrl": os.environ.get("SUPABASE_URL", ""),
        "supabaseKey": os.environ.get("SUPABASE_KEY", "")
    })

@app.route("/health")
def health():
    return jsonify({"status": "online"})

if _name_ == "_main_":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
