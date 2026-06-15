package main

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
