package main

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
