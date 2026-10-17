# Cause record (D048 step 6)

```
Symptom: <what the user or the test sees, exactly>
Seen: <all n occurrences; "explains k/n"; several mechanisms may add up>
Rule broken: <the invariant, decision or contract the code broke>
Elsewhere: <other places with the same pattern>
Change: <the fix, in the shared place, for every caller>
```

k < n means the cause is not found yet: keep experimenting. A correlation is not a cause:
the record names the mechanism, and the loop proves it by going green when only that changes.
