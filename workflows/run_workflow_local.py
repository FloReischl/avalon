#!/usr/bin/env python3
"""Local Workflow Runner for testing Avalon workflow scripts offline/standalone."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
import httpx
import yaml

from pathlib import Path

# Standalone Defaults
BACKEND_URL = "http://127.0.0.1:8095"
DEFAULT_AGENT_ID = 1  # Standard Agent ID in Avalon


def get_agent_config(name: str) -> dict :
    # blueprint file
    agents_yaml = Path(Path(__file__).parent, "../data/blueprints/user.avalon/agents.yaml")
    with agents_yaml.open("r") as fs:
        y = yaml.safe_load(fs)

    for _, section in enumerate(y["agents"]):
        if section["name"] != name: continue

        return { 
            "model_persona": section["persona"],
            "model_instructions": section["instructions"]
        }

    raise KeyError(f"Agent '{name}' not found.")


def get_agent_token(backend_url: str, agent_id: int) -> str:
    resp = httpx.get(f"{backend_url}/api/v1/ui/token", params={"agent_id": agent_id})
    resp.raise_for_status()
    return resp.json()["agentBearerToken"]


def run_workflow(script_path: str, avalon_args: dict | None = None, payload: list | dict | None = None) -> None:
    avalon_args = avalon_args or dict()

    def get_avalon_arg(key: str, default: object):
        return { key: avalon_args.get(key, default) }

    token = avalon_args["bearer_token"] if "bearer_token" in avalon_args else get_agent_token(BACKEND_URL, DEFAULT_AGENT_ID)

    # Das Envelope, das Avalon normalerweise via stdin an den Workflow übergibt
    envelope = {
        "avalon": {
            "backend_url": BACKEND_URL,
            "bearer_token": token,
            **get_avalon_arg("workflow_execution_id", 99999),
            **get_avalon_arg("model_persona", None),
            **get_avalon_arg("model_instructions", None),
            **get_avalon_arg("model_context", None),
            **get_avalon_arg("current_datetime", datetime.now().isoformat()),
        },
        "payload": payload or [],
    }

    envelope_json = json.dumps(envelope)

    print(f"🚀 Starte Workflow-Skript: {script_path}")
    print(f"📡 Backend: {BACKEND_URL}")
    print("=" * 60)

    try:
        # Ausführung des Skripts mit sys.executable und Piping des Envelopes in stdin
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            text=True,
        )
        process.communicate(input=envelope_json)

        print("=" * 60)
        if process.returncode == 0:
            print("✅ Workflow erfolgreich beendet (Exit Code 0).")
        else:
            print(f"❌ Workflow fehlgeschlagen (Exit Code {process.returncode}).", file=sys.stderr)

    except Exception as e:
        print(f"❌ Fehler beim Ausführen des Skripts: {e}", file=sys.stderr)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Run an Avalon workflow script locally.")
    # parser.add_argument("script", help="Pfad zum Python-Workflow-Skript (z.B. organize-mail.py)")
    # args = parser.parse_args()

    config = get_agent_config("Cortana")
    config["bearer_token"] = get_agent_token(BACKEND_URL, 4)
    run_workflow("workflows/gmail-organizer.py", config, None)

    # run_workflow(args.script)

