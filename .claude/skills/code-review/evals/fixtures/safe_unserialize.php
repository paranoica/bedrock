<?php
// structured data only; no PHP objects are reconstructed from input
$data = json_decode($_GET["state"], true, 32, JSON_THROW_ON_ERROR);
echo render($data);
