from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
import hashlib
import json
from os import getenv
from sys import argv
from threading import Event, Lock, Thread
import time
from uuid import uuid4

app = Flask(__name__)
CORS(app)


pending_requests = {}
lock = Lock()

def load_data():
    global data
    try:
        with open("data.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = { "usage": []}

load_data()


@app.route("/v1/completions", methods=["POST"])
def handle_request():
    params = request.get_json()

    load_data()
    
    if "prompt" not in params:
        return jsonify({"error": "prompt is required"}), 400

    
    with open("data.json", "w") as f:
        json.dump(data, f)
    
    # change this to take models params["model"] = "code-davinci-002"

    prompt = params["prompt"]
    shared_params = {k: v for k, v in params.items() if k != "prompt"}

    event = Event()

    sha256 = hashlib.sha256()
    sha256.update(json.dumps(tuple(sorted(params.items()))).encode("utf-8"))
    key = sha256.digest()
    value = {"prompt": prompt, "event": event}

    with lock:
        if key not in pending_requests:
            pending_requests[key] = {"shared_params": shared_params, "values": [value]}
        else:
            pending_requests[key]["values"].append(value)

    event.wait()

    with lock:
        for value in pending_requests[key]["values"]:
            if value["prompt"] == prompt:
                return jsonify(value["response"])
        

def handle_pending_requests():
    while True:
        with lock:
            if not pending_requests:
                continue

            key = next(iter(pending_requests))
            shared_params = pending_requests[key]["shared_params"]
            values = pending_requests[key]["values"]

            prompts = [value["prompt"] for value in values]

            response = #TODO: Add response logic

            if "n" in shared_params:
                n = shared_params["n"]
            else:
                n = 1
            choices = response["choices"]
            grouped_choices = [choices[i:i + n] for i in range(0, len(choices), n)]

            for value, choices in zip(values, grouped_choices):
                value["response"] = {"choices": choices}
                value["event"].set()

            key_to_delete = key

        time.sleep(3)

        with lock:
            del pending_requests[key_to_delete]



if __name__ == "__main__":
    # TODO: take name of model as arg
    Thread(target=handle_pending_requests, daemon=True).start()
    app.run()
    
