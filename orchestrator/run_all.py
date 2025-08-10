import subprocess
import time
import requests
import sys

# Config for each service
SERVICES = {
    "generator": {
        "cmd": ["uvicorn", "main:app", "--host", "localhost", "--port", "8001"],
        "cwd": "../generator",
        "url": "http://localhost:8001/"
    },
    "mockup": {
        "cmd": ["node", "server.js"],
        "cwd": "../mockup",
        "url": "http://localhost:3000/"
    },
    "publisher": {
        "cmd": ["php", "-S", "localhost:8000"],
        "cwd": "../publisher",
        "url": "http://localhost:8000/api.php"  
    }
}

def wait_for_service(url, retries=10, delay=3):
    for i in range(retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"Service at {url} is up.")
                return True
        except Exception:
            pass
        print(f"Waiting for service at {url} ({i+1}/{retries})...")
        time.sleep(delay)
    return False
def print_process_logs(name, proc):
    try:
        stdout, stderr = proc.communicate(timeout=5)
        if stdout:
            print(f"[{name} STDOUT]\n{stdout.decode()}")
        if stderr:
            print(f"[{name} STDERR]\n{stderr.decode()}")
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"[{name}] Process killed after timeout while reading logs.")


def main():
    procs = {}
    try:
        # Start all services
        for name, svc in SERVICES.items():
            print(f"Starting {name} server...")
            procs[name] = subprocess.Popen(
                svc["cmd"],
                cwd=svc["cwd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False  # required for Windows sometimes, but can be adjusted
            )

        # Wait for all services to be ready
        for name, svc in SERVICES.items():
            if not wait_for_service(svc["url"]):
                print(f"Error: {name} service failed to start in time.")
                print_process_logs(name, procs[name])
                raise Exception(f"{name} service not ready")

        # Run the orchestrator
        print("All services running. Starting orchestrator...")
        orchestrator_proc = subprocess.run(
            ["python", "run.py"],
            cwd=".",
            capture_output=True,
            text=True
        )
        print("Orchestrator output:")
        print(orchestrator_proc.stdout)
        if orchestrator_proc.returncode != 0:
            print("Orchestrator failed:", orchestrator_proc.stderr)
            sys.exit(1)

    except Exception as e:
        print("Error during startup or orchestrator run:", e)
    finally:
        # Terminate all started services
        print("Terminating all services...")
        for proc in procs.values():
            proc.terminate()
            print_process_logs(name, proc)
        print("All services terminated.")

if __name__ == "__main__":
    main()
