import os
def read_file(request):
    name = request.args.get("name")                       # untrusted source
    with open(os.path.join("/data", name)) as f:          # ../ escapes /data [VULN: path]
        return f.read()
