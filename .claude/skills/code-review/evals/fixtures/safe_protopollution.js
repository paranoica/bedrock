// same merge, but proto-keys are rejected and the recursion is null-proto
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
