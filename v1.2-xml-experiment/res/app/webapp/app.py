# -*- coding: utf-8 -*-
"""Flash 1.2 workbench shell; XML generation routes are added separately."""
from flask import Flask, jsonify, render_template

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/jobs")
def list_jobs():
    return jsonify({"jobs": []})


@app.post("/api/jobs")
def create_job():
    return jsonify({"error": "Flash 1.2 的 XML 生成任务接口尚未接入"}), 501


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5128)
