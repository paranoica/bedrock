<?php
// POP-chain object injection: attacker controls which objects are built and
// which magic methods (__wakeup/__destruct) fire -> RCE / file write.
$data = unserialize($_GET["state"]);
echo render($data);
