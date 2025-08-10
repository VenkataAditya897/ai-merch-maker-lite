<?php
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    http_response_code(200);
    echo json_encode(['status' => 'ok', 'message' => 'Publisher server is running']);
    exit;
}

$input = file_get_contents("php://input");
$data = json_decode($input, true);

// Validate input (title & price are required)
if (!$data || !isset($data['title']) || !isset($data['price'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid product data']);
    exit;
}

$logFile = __DIR__ . '/published.log';
$existingId = null;

// Check for duplicate by title in log
if (file_exists($logFile)) {
    $lines = file($logFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos($line, $data['title']) !== false) {
            // Extract fake_product_id from JSON in the log line
            $parts = explode(" | ", $line);
            if (isset($parts[1])) {
                $jsonData = json_decode($parts[1], true);
                if ($jsonData && isset($jsonData['fake_product_id'])) {
                    $existingId = $jsonData['fake_product_id'];
                } else {
                    // If fake_product_id not stored, fallback to new ID creation
                    $existingId = 'FP-EXISTING';
                }
            }
            break;
        }
    }
}

if ($existingId) {
    // Return existing ID for duplicate
    echo json_encode([
        'status' => 'duplicate',
        'fake_product_id' => $existingId,
        'message' => 'Product already published'
    ]);
    exit;
}

// Create fake product ID
$fakeId = 'FP-' . rand(1000, 9999);

// Add fake_product_id to data for logging
$data['fake_product_id'] = $fakeId;

// Append to log
$logEntry = date('Y-m-d H:i:s') . " | " . json_encode($data) . PHP_EOL;
file_put_contents($logFile, $logEntry, FILE_APPEND);

// Return response
echo json_encode([
    'status' => 'success',
    'fake_product_id' => $fakeId
]);
