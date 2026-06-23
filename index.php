<?php

declare(strict_types=1);

$pageTitle = 'RAG Evaluation Workspace | ICS 499';
$documentRoot = __DIR__ . '/data/metrostate_documents';

function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

function sourceDocumentStats(string $documentRoot): array
{
    if (!is_dir($documentRoot)) {
        return ['document_count' => 0, 'category_count' => 0];
    }

    $documents = glob($documentRoot . '/*/*.txt') ?: [];
    $categories = [];

    foreach ($documents as $document) {
        $categories[basename(dirname($document))] = true;
    }

    return [
        'document_count' => count($documents),
        'category_count' => count($categories),
    ];
}

$sourceStats = sourceDocumentStats($documentRoot);

$sampleQuestions = [
    'When does Fall 2026 registration begin?',
    'What GPA is required for automatic first-year admission?',
    'What does financial aid pay first?',
];

$plannedDocuments = [
    ['title' => 'Registration overview', 'type' => 'TXT', 'status' => 'Source file ready'],
    ['title' => 'Financial aid overview', 'type' => 'TXT', 'status' => 'Source file ready'],
    ['title' => 'Academic calendar documents', 'type' => 'TXT', 'status' => 'Source files ready'],
];

$plannedRuns = [
    [
        'name' => 'MySQL keyword baseline',
        'retrieval' => 'MySQL',
        'chunk_size' => 'N/A',
        'top_k' => 5,
        'temperature' => '0.0',
        'score' => 'TBD',
    ],
    [
        'name' => 'ChromaDB vector baseline',
        'retrieval' => 'ChromaDB',
        'chunk_size' => 800,
        'top_k' => 5,
        'temperature' => '0.0',
        'score' => 'TBD',
    ],
    [
        'name' => 'Higher recall',
        'retrieval' => 'ChromaDB',
        'chunk_size' => 800,
        'top_k' => 8,
        'temperature' => '0.0',
        'score' => 'TBD',
    ],
];

require __DIR__ . '/includes/header.php';
?>
<div class="app-shell">
    <?php require __DIR__ . '/includes/nav.php'; ?>

    <div class="app-main">
        <header class="topbar">
            <div>
                <p class="eyebrow">Metro State document evaluation</p>
                <h1>RAG Evaluation Workspace</h1>
            </div>
            <div class="topbar-actions">
                <span class="pill">Local demo</span>
                <span class="pill muted">PHP + MySQL + ChromaDB</span>
            </div>
        </header>

        <main id="main-content">
            <section class="workspace-section" id="overview">
                <div class="section-title-row">
                    <div>
                        <h2>Project Snapshot</h2>
                        <p>
                            This application will support document ingestion, RAG question answering,
                            evaluation runs, and comparison between MySQL keyword retrieval and
                            ChromaDB vector retrieval.
                        </p>
                    </div>
                </div>

                <div class="stat-grid">
                    <article class="stat-card">
                        <span>Documents</span>
                        <strong><?= h((string) $sourceStats['document_count']) ?></strong>
                        <small>Metro State source files</small>
                    </article>
                    <article class="stat-card">
                        <span>Categories</span>
                        <strong><?= h((string) $sourceStats['category_count']) ?></strong>
                        <small>document groups imported</small>
                    </article>
                    <article class="stat-card">
                        <span>Questions</span>
                        <strong>30-50</strong>
                        <small>planned gold dataset</small>
                    </article>
                    <article class="stat-card">
                        <span>Storage</span>
                        <strong>2</strong>
                        <small>MySQL and ChromaDB</small>
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
                        <span class="status status-planned">FP6</span>
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
                            <button type="button" disabled><?= h($question) ?></button>
                        <?php endforeach; ?>
                    </div>

                    <div class="answer-preview">
                        <span class="preview-label">Answer preview</span>
                        <p>
                            Once implemented, this area will show the generated answer, retrieved
                            source documents, and settings used for the response.
                        </p>
                    </div>
                </section>

                <section class="panel" id="documents">
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Admin</span>
                            <h2>Documents</h2>
                        </div>
                        <span class="status status-ready">Source ready</span>
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
                                    <strong><?= h($document['title']) ?></strong>
                                    <span><?= h($document['status']) ?></span>
                                </div>
                                <small><?= h($document['type']) ?></small>
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
                        <span class="status status-planned">FP7-FP8</span>
                    </div>

                    <div class="table-responsive">
                        <table class="table app-table align-middle">
                            <thead>
                                <tr>
                                    <th scope="col">Run</th>
                                    <th scope="col">Retrieval</th>
                                    <th scope="col">Chunk</th>
                                    <th scope="col">Top-K</th>
                                    <th scope="col">Temp</th>
                                    <th scope="col">Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($plannedRuns as $run): ?>
                                    <tr>
                                        <th scope="row"><?= h($run['name']) ?></th>
                                        <td><?= h($run['retrieval']) ?></td>
                                        <td><?= h((string) $run['chunk_size']) ?></td>
                                        <td><?= h((string) $run['top_k']) ?></td>
                                        <td><?= h($run['temperature']) ?></td>
                                        <td><?= h($run['score']) ?></td>
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

<?php require __DIR__ . '/includes/footer.php'; ?>
