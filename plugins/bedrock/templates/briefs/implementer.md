Reason: a — {why the session should not write this itself}
Task: {one task, in one or two sentences}
Cause: {path of the cause record for a fix, or "feature"}
Files: {the only files you may change, comma-separated}
Done when: {the named test passes, and it failed before the change}
Read: {exact paths, in order}
Keep true: {rules, decisions and invariants}
Known: {what is known and tried}
Commands: {the task's tests, through `bedrock test` / `bedrock cmd`; wait for each}
Ask when: {another file needs changing; the test cannot be made to fail first}
Verify: {1. the test; 2. the task's goal}
Stop when: {done only when the test fails before and passes after; stop if a listed file is
not enough}
Report: {path}
Estimate: {expected weighted tokens}
