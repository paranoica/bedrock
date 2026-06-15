import subprocess
def ping(request):
    host = request.args.get("host")
    return subprocess.check_output(["ping", "-c1", host])  # arg vector, no shell — SAFE
