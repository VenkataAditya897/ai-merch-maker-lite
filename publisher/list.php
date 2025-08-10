<?php

$logFile = __DIR__ . '/published.log';

if (!file_exists($logFile)) {
    echo "<h3>No products published yet.</h3>";
    exit;
}

echo "<h2>Recently Published Products</h2><pre>";
echo htmlspecialchars(file_get_contents($logFile));
echo "</pre>";
