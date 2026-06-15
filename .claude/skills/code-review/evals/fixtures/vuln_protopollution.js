// merge user-controlled JSON into a config object (Express handler)
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
