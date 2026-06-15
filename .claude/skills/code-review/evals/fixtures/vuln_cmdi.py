import subprocess
def ping(request):
    host = request.args.get("host")                       # untrusted source
    return subprocess.check_output(f"ping -c1 {host}", shell=True)  # cmd-inj sink [VULN: cmdi]
