<?php
$currentYear = date('Y');

$sampleQuestions = [
    'When does Fall 2026 registration begin?',
    'What GPA is required for automatic first-year admission?',
    'What does financial aid pay first?',
];

$plannedDocuments = [
    ['title' => 'Registration overview', 'type' => 'TXT', 'status' => 'Pending ingest'],
    ['title' => 'Financial aid overview', 'type' => 'PDF', 'status' => 'Pending ingest'],
    ['title' => 'Graduation requirements', 'type' => 'DOCX', 'status' => 'Pending ingest'],
];

$plannedRuns = [
    ['name' => 'Baseline', 'chunk_size' => 500, 'top_k' => 3, 'temperature' => '0.0', 'score' => 'TBD'],
    ['name' => 'More context', 'chunk_size' => 800, 'top_k' => 5, 'temperature' => '0.0', 'score' => 'TBD'],
    ['name' => 'Higher recall', 'chunk_size' => 800, 'top_k' => 8, 'temperature' => '0.3', 'score' => 'TBD'],
];
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta
        name="description"
        content="Starter application shell for evaluating RAG configurations with Metro State documents."
    >
    <title>RAG Evaluation App | ICS 499</title>
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

    <div class="app-shell">
        <aside class="app-sidebar" aria-label="Application navigation">
            <a class="app-brand" href="index.php">
                <span class="brand-mark">RE</span>
                <span>
                    <strong>RAG Eval</strong>
                    <small>ICS 499 Capstone</small>
                </span>
            </a>

            <nav class="side-nav">
                <a class="active" href="#overview">Overview</a>
                <a href="#ask">Ask</a>
                <a href="#documents">Documents</a>
                <a href="#evaluation">Evaluation</a>
                <a href="#results">Results</a>
                <a href="#report">Report</a>
            </nav>

            <div class="sidebar-note">
                <span class="status-dot"></span>
                <div>
                    <strong>FP3 build</strong>
                    <p>Starter shell. Backend features begin in FP4.</p>
                </div>
            </div>
        </aside>

        <div class="app-main">
            <header class="topbar">
                <div>
                    <p class="eyebrow">Metro State document evaluation</p>
                    <h1>RAG Evaluation Workspace</h1>
                </div>
                <div class="topbar-actions">
                    <span class="pill">Local demo</span>
                    <span class="pill muted">PHP + MySQL</span>
                </div>
            </header>

            <main id="main-content">
                <section class="workspace-section" id="overview">
                    <div class="section-title-row">
                        <div>
                            <h2>Project Snapshot</h2>
                            <p>
                                This starter application shows the screens that will support document
                                ingestion, RAG question answering, evaluation runs, and result comparison.
                            </p>
                        </div>
                    </div>

                    <div class="stat-grid">
                        <article class="stat-card">
                            <span>Documents</span>
                            <strong>TBD</strong>
                            <small>Metro State source files</small>
                        </article>
                        <article class="stat-card">
                            <span>Questions</span>
                            <strong>30-50</strong>
                            <small>planned gold dataset</small>
                        </article>
                        <article class="stat-card">
                            <span>Metrics</span>
                            <strong>3+</strong>
                            <small>similarity, sources, judge</small>
                        </article>
                        <article class="stat-card">
                            <span>Deployment</span>
                            <strong>Local</strong>
                            <small>class demonstration</small>
                        </article>
                    </div>
                </section>

                <div class="workspace-grid">
                    <section class="panel panel-large" id="ask">
                        <div class="panel-header">
                            <div>
                                <span class="panel-kicker">Ask</span>
                                <h2>Question Answering</h2>
                            </div>
                            <span class="status status-planned">Planned</span>
                        </div>

                        <div class="chat-card">
                            <label class="form-label" for="questionInput">Question</label>
                            <textarea
                                class="form-control"
                                id="questionInput"
                                rows="4"
                                disabled
                                placeholder="Ask a question about Metro State documents..."
                            ></textarea>
                            <div class="d-flex flex-wrap gap-2 mt-3">
                                <button class="btn btn-primary" type="button" disabled>Ask question</button>
                                <button class="btn btn-outline-secondary" type="button" disabled>Clear</button>
                            </div>
                        </div>

                        <div class="suggestions" aria-label="Sample questions">
                            <?php foreach ($sampleQuestions as $question): ?>
                                <button type="button" disabled><?= htmlspecialchars($question, ENT_QUOTES, 'UTF-8') ?></button>
                            <?php endforeach; ?>
                        </div>

                        <div class="answer-preview">
                            <span class="preview-label">Answer preview</span>
                            <p>
                                Once implemented, this area will show the generated answer, the
                                retrieved source documents, and the settings used for the response.
                            </p>
                        </div>
                    </section>

                    <section class="panel" id="documents">
                        <div class="panel-header">
                            <div>
                                <span class="panel-kicker">Admin</span>
                                <h2>Documents</h2>
                            </div>
                            <span class="status status-planned">Planned</span>
                        </div>

                        <div class="upload-dropzone">
                            <strong>Upload documents</strong>
                            <span>TXT first, PDF/DOCX after parsing is confirmed.</span>
                            <input class="form-control" type="file" disabled>
                        </div>

                        <div class="list-stack">
                            <?php foreach ($plannedDocuments as $document): ?>
                                <article class="list-item">
                                    <div>
                                        <strong><?= htmlspecialchars($document['title'], ENT_QUOTES, 'UTF-8') ?></strong>
                                        <span><?= htmlspecialchars($document['status'], ENT_QUOTES, 'UTF-8') ?></span>
                                    </div>
                                    <small><?= htmlspecialchars($document['type'], ENT_QUOTES, 'UTF-8') ?></small>
                                </article>
                            <?php endforeach; ?>
                        </div>
                    </section>

                    <section class="panel panel-large" id="evaluation">
                        <div class="panel-header">
                            <div>
                                <span class="panel-kicker">Evaluation</span>
                                <h2>Configuration Runs</h2>
                            </div>
                            <span class="status status-planned">Planned</span>
                        </div>

                        <div class="table-responsive">
                            <table class="table app-table align-middle">
                                <thead>
                                    <tr>
                                        <th scope="col">Run</th>
                                        <th scope="col">Chunk</th>
                                        <th scope="col">Top-K</th>
                                        <th scope="col">Temp</th>
                                        <th scope="col">Score</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php foreach ($plannedRuns as $run): ?>
                                        <tr>
                                            <th scope="row"><?= htmlspecialchars($run['name'], ENT_QUOTES, 'UTF-8') ?></th>
                                            <td><?= htmlspecialchars((string) $run['chunk_size'], ENT_QUOTES, 'UTF-8') ?></td>
                                            <td><?= htmlspecialchars((string) $run['top_k'], ENT_QUOTES, 'UTF-8') ?></td>
                                            <td><?= htmlspecialchars($run['temperature'], ENT_QUOTES, 'UTF-8') ?></td>
                                            <td><?= htmlspecialchars($run['score'], ENT_QUOTES, 'UTF-8') ?></td>
                                        </tr>
                                    <?php endforeach; ?>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section class="panel" id="results">
                        <div class="panel-header">
                            <div>
                                <span class="panel-kicker">Results</span>
                                <h2>Comparison</h2>
                            </div>
                            <span class="status status-planned">Planned</span>
                        </div>

                        <div class="empty-state">
                            <strong>No evaluation results yet</strong>
                            <p>Scores will appear after the RAG pipeline and evaluation runner are implemented.</p>
                        </div>
                    </section>

                    <section class="panel panel-large" id="report">
                        <div class="panel-header">
                            <div>
                                <span class="panel-kicker">Report</span>
                                <h2>Final Recommendation</h2>
                            </div>
                            <span class="status status-planned">Planned</span>
                        </div>

                        <div class="report-grid">
                            <article>
                                <strong>Best configuration</strong>
                                <p>Which settings performed best and why.</p>
                            </article>
                            <article>
                                <strong>Failure cases</strong>
                                <p>Questions where retrieval or generation failed.</p>
                            </article>
                            <article>
                                <strong>Trade-offs</strong>
                                <p>Accuracy, latency, source quality, and cost.</p>
                            </article>
                        </div>
                    </section>
                </div>
            </main>

            <footer class="app-footer">
                <span>LLM RAG Evaluation Project</span>
                <span>ICS 499 · <?= htmlspecialchars($currentYear, ENT_QUOTES, 'UTF-8') ?></span>
            </footer>
        </div>
    </div>

    <script
        src="https://code.jquery.com/jquery-3.7.1.min.js"
        integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
        crossorigin="anonymous"
    ></script>
    <script
        src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
        crossorigin="anonymous"
    ></script>
    <script src="assets/js/app.js"></script>
</body>
</html>
