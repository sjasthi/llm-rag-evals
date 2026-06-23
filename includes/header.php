<?php

$pageTitle = $pageTitle ?? 'RAG Evaluation App | ICS 499';
$metaDescription = $metaDescription
    ?? 'Starter application shell for evaluating RAG configurations with Metro State documents.';
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta
        name="description"
        content="<?= htmlspecialchars($metaDescription, ENT_QUOTES, 'UTF-8') ?>"
    >
    <title><?= htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8') ?></title>
    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
        crossorigin="anonymous"
    >
    <link rel="stylesheet" href="assets/css/styles.css">
</head>
<body class="app-body">
    <a class="skip-link" href="#main-content">Skip to main content</a>
