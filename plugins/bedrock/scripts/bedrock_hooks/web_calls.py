"""HTTP and raw network clients: is this call a write to an outside host?"""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlparse

from bedrock_hooks.gate import Action

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", ""}
CURL_DATA = {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "-F", "--form"}
CURL_DATA |= {"-T", "--upload-file", "--json"}
CURL_DATA_PREFIXES = ("--data", "--json", "--form", "--upload-file", "-d", "-F", "-T")
CURL_VALUED = {"-H", "--header", "-o", "--output", "-u", "--user", "-A", "--user-agent", "-e"}
CURL_VALUED |= {"-X", "--request", "-d", "--data", "-F", "--form", "-T", "--upload-file"}
CURL_VALUED |= {"--data-raw", "--data-binary", "--data-urlencode", "--json", "-b", "--cookie"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def local(host: str) -> bool:
    """True for this machine's own addresses."""
    return host.lower().split(":")[0] in LOCAL_HOSTS or host.endswith(".localhost")


def _hostname(text: str) -> str:
    return urlparse(text if "://" in text else f"//{text}").hostname or ""


def _hosts(argv: list[str], valued: set[str]) -> list[str]:
    hosts, skip = [], False
    for index, arg in enumerate(argv[1:], start=1):
        if skip:
            skip = False
        elif arg == "--url" and index + 1 < len(argv):
            hosts.append(_hostname(argv[index + 1]))
            skip = True
        elif arg.startswith("--url="):
            hosts.append(_hostname(arg.split("=", 1)[1]))
        elif arg in valued:
            skip = True
        elif not arg.startswith("-") and (
            "://" in arg or "." in arg or arg.startswith("localhost")
        ):
            hosts.append(_hostname(arg))
    return hosts


def _method(argv: list[str], index: int) -> str:
    arg = argv[index]
    following = argv[index + 1] if index + 1 < len(argv) else ""
    if arg in ("-X", "--request"):
        return following
    if arg.startswith("--request="):
        return arg.split("=", 1)[1]
    if arg.startswith("-") and not arg.startswith("--") and "X" in arg:
        return arg.split("X", 1)[1] or following
    return ""


def _curl_writes(argv: list[str]) -> bool:
    for index, arg in enumerate(argv[1:], start=1):
        if _method(argv, index).upper() in WRITE_METHODS:
            return True
        if arg in CURL_DATA or any(arg.startswith(flag) for flag in CURL_DATA_PREFIXES):
            return True
        if arg.startswith("-") and not arg.startswith("--") and set(arg[1:]) & {"d", "F", "T"}:
            return True
    return False


RAW_NETWORK = {"nc", "ncat", "netcat", "socat", "telnet"}


def http_write(argv: list[str]) -> list[Action]:
    """The outward write an HTTP or raw network client would make, if any."""
    program = PurePosixPath(argv[0]).name
    if program in RAW_NETWORK or (program == "openssl" and "s_client" in argv):
        hosts = [a for a in argv[1:] if not a.startswith("-") and not a.isdigit()]
        if hosts and not all(local(h.split(":")[0]) for h in hosts):
            return [Action("http-write", "a raw network connection to an outside host")]
        return []
    if program in ("xh", "xhs", "curlie"):
        program = "http"
    if program not in ("curl", "wget", "http", "https"):
        return []
    hosts = _hosts(argv, CURL_VALUED)
    if not hosts or all(local(host) for host in hosts):
        return []
    if program == "curl":
        writes = _curl_writes(argv)
    elif program == "wget":
        writes = any(
            a.startswith(("--post-data", "--post-file", "--method", "--body")) for a in argv
        )
    else:
        writes = any(a.upper() in WRITE_METHODS for a in argv[1:3]) or any(
            "=" in a for a in argv[2:]
        )
    return [Action("http-write", "an HTTP write to an outside service")] if writes else []
