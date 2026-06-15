import os
def read_file(request):
    name = request.args.get("name")
    base = os.path.realpath("/data")
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):                # confined to /data — SAFE
        raise ValueError("path escape")
    with open(full) as f:
        return f.read()
