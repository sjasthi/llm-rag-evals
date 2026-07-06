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
                            This application supports document ingestion and grounded RAG question
                            answering. Evaluation runs and retrieval-configuration comparisons are
                            planned for later iterations.
                        </p>
                    </div>
                </div>

                <div class="stat-grid">
                    <article class="stat-card">
                        <span>Documents</span>
                        <strong id="documentCount"><?= h((string) $sourceStats['document_count']) ?></strong>
                        <small>currently indexed documents</small>
                    </article>
                    <article class="stat-card">
                        <span>Categories</span>
                        <strong id="categoryCount"><?= h((string) $sourceStats['category_count']) ?></strong>
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
                        <span class="status status-ready">Live</span>
                    </div>

                    <form class="chat-card" id="askForm">
                        <label class="form-label" for="questionInput">Question</label>
                        <textarea
                            class="form-control"
                            id="questionInput"
                            name="question"
                            rows="4"
                            maxlength="2000"
                            required
                            placeholder="Ask a question about Metro State documents..."
                        ></textarea>
                        <div class="d-flex flex-wrap gap-2 mt-3">
                            <button class="btn btn-primary" id="askButton" type="submit">
                                Ask question
                            </button>
                            <button class="btn btn-outline-secondary" id="clearQuestionButton" type="button">
                                Clear
                            </button>
                        </div>
                    </form>

                    <div class="suggestions" aria-label="Sample questions">
                        <?php foreach ($sampleQuestions as $question): ?>
                            <button
                                class="suggestion-button"
                                type="button"
                                data-question="<?= h($question) ?>"
                            ><?= h($question) ?></button>
                        <?php endforeach; ?>
                    </div>

                    <div class="answer-preview" id="answerPanel" aria-live="polite">
                        <div id="answerEmptyState">
                            <span class="preview-label">Grounded answer</span>
                            <p>Submit a question to see a Gemini answer and the Metro State sources used.</p>
                        </div>

                        <div class="answer-loading" id="answerLoadingState" hidden>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span>Retrieving sources and generating an answer...</span>
                        </div>

                        <div class="alert alert-danger mb-0" id="answerErrorState" role="alert" hidden></div>

                        <div id="answerResult" hidden>
                            <span class="preview-label">Grounded answer</span>
                            <p class="answer-copy" id="answerText"></p>
                            <div class="answer-meta" id="answerMeta"></div>

                            <div class="source-results">
                                <h3>Retrieved sources</h3>
                                <div class="source-list" id="sourceList"></div>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="panel" id="documents">
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Admin</span>
                            <h2>Documents</h2>
                        </div>
                        <span class="status status-ready">FP6 live</span>
                    </div>

                    <form class="upload-dropzone" id="documentUploadForm" enctype="multipart/form-data">
                        <strong>Upload and ingest a document</strong>
                        <span>TXT, text-based PDF, or DOCX; maximum 10 MB.</span>
                        <label class="form-label" for="documentFile">Document</label>
                        <input
                            class="form-control"
                            id="documentFile"
                            name="document"
                            type="file"
                            accept=".txt,.pdf,.docx"
                            required
                        >
                        <div class="row g-2 mt-1">
                            <div class="col-md-6">
                                <label class="form-label" for="documentTitle">Title</label>
                                <input class="form-control" id="documentTitle" name="title" maxlength="255">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label" for="documentCategory">Category</label>
                                <input
                                    class="form-control"
                                    id="documentCategory"
                                    name="category"
                                    pattern="[a-z0-9][a-z0-9_-]{1,49}"
                                    placeholder="student_support"
                                    required
                                >
                            </div>
                        </div>
                        <input id="replaceDocumentId" name="replace_document_id" type="hidden">
                        <div class="d-flex flex-wrap gap-2 mt-3">
                            <button class="btn btn-primary" id="uploadDocumentButton" type="submit">
                                Upload and ingest
                            </button>
                            <button class="btn btn-outline-secondary" id="cancelReplaceButton" type="button" hidden>
                                Cancel replacement
                            </button>
                        </div>
                        <div class="upload-selection mt-2" id="uploadSelection" aria-live="polite"></div>
                        <div class="alert mt-3 mb-0" id="documentMessage" role="status" hidden></div>
                    </form>

                    <div class="document-list mt-3">
                        <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
                            <h3 class="h6 mb-0">Indexed documents</h3>
                            <button class="btn btn-sm btn-outline-secondary" id="refreshDocumentsButton" type="button">
                                Refresh
                            </button>
                        </div>
                        <div id="documentList" aria-live="polite">
                            <p class="text-muted">Loading indexed documents...</p>
                        </div>
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
