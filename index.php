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

require __DIR__ . '/includes/header.php';
?>
<div class="app-shell">
    <?php require __DIR__ . '/includes/nav.php'; ?>

    <div class="app-main">
        <main id="main-content">
        <header class="topbar workspace-view" data-view-panel="overview">
            <div class="topbar-copy">
                <p class="eyebrow">Evidence-led RAG research</p>
                <h1>See what your RAG system <em>actually</em> knows.</h1>
                <p class="topbar-description">Ask questions against Metro State documents, preserve the retrieved evidence, and compare the signals that describe answer quality.</p>
            </div>
            <div class="topbar-actions">
                <span class="pill live-pill"><span></span> Ready for evaluation</span>
                <span class="pill muted">Local-first · evidence retained</span>
            </div>
        </header>

            <section class="workspace-section workspace-view" id="overview" data-view-panel="overview">
                <div class="section-title-row hero-overview">
                    <div>
                        <span class="panel-kicker">The research loop</span>
                        <h2>Answer, inspect, compare, learn.</h2>
                        <p>
                            Every response is paired with the source chunks that informed it. That gives you a clear trail from question to evidence to evaluation result.
                        </p>
                        <div class="hero-actions">
                            <a class="btn btn-primary" href="#ask">Ask a source-backed question</a>
                            <a class="btn btn-outline-light" href="#results">Explore saved runs</a>
                        </div>
                    </div>
                    <div class="research-signal" aria-label="Current project stage">
                        <span>Current research layer</span>
                        <strong>03</strong>
                        <small>Baseline + advanced + human review</small>
                        <div class="signal-bar"><span></span></div>
                    </div>
                </div>

                <div class="stat-grid">
                    <article class="stat-card">
                        <span class="stat-label">Source corpus</span>
                        <strong id="documentCount"><?= h((string) $sourceStats['document_count']) ?></strong>
                        <small>indexed Metro State documents</small>
                    </article>
                    <article class="stat-card">
                        <span class="stat-label">Topics</span>
                        <strong id="categoryCount"><?= h((string) $sourceStats['category_count']) ?></strong>
                        <small>distinct source categories</small>
                    </article>
                    <article class="stat-card">
                        <span class="stat-label">Reviewed prompts</span>
                        <strong id="evaluationQuestionCount">25</strong>
                        <small>questions with expected evidence</small>
                    </article>
                    <article class="stat-card">
                        <span class="stat-label">Quality lenses</span>
                        <strong id="overviewEvaluatorCount">13</strong>
                        <small>metric and model-backed evaluators</small>
                    </article>
                </div>

                <div class="workflow-strip" aria-label="Evaluation workflow">
                    <article><span>1</span><div><strong>Curate sources</strong><small>Ingest the evidence the system may retrieve.</small></div></article>
                    <article><span>2</span><div><strong>Review test cases</strong><small>Verify a sampled answer key against cited evidence.</small></div></article>
                    <article><span>3</span><div><strong>Run experiments</strong><small>Answer selected questions with fixed settings.</small></div></article>
                    <article><span>4</span><div><strong>Compare signals</strong><small>Inspect failures, disagreements, and trade-offs.</small></div></article>
                </div>
            </section>

            <div class="workspace-grid">
                <section class="panel panel-large ask-panel workspace-view" id="ask" data-view-panel="ask" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Playground</span>
                            <h2>Ask, retrieve, inspect</h2>
                            <p>Test one question interactively before promoting it into a repeatable experiment.</p>
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
                            placeholder="Example: When does Fall 2026 registration begin?"
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

                <section class="panel documents-panel workspace-view" id="documents" data-view-panel="documents" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Source library</span>
                            <h2>Curate the knowledge base</h2>
                            <p>Control which evidence is available to retrieval and verify its ingestion state.</p>
                        </div>
                        <span class="status status-ready">FP6 live</span>
                    </div>

                    <form class="upload-dropzone" id="documentUploadForm" enctype="multipart/form-data">
                        <strong>Add source material</strong>
                        <span>TXT, text-based PDF, or DOCX · server-side validation · maximum 10 MB</span>
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

                <section class="panel panel-large workspace-view" id="evaluation" data-view-panel="evaluation" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Versioned dataset</span>
                            <h2>Ground truth and test coverage</h2>
                        </div>
                        <span class="status status-ready">FP8/FP9 active</span>
                    </div>
                    <p id="evaluationDatasetSummary">Loading the versioned FP7 question set...</p>
                    <div class="evaluation-guide" aria-labelledby="datasetReviewGuideTitle">
                        <strong id="datasetReviewGuideTitle">Review the test case, not the model response</strong>
                        <p>
                            This is a sampled answer key for repeatable experiments—not every question the corpus could answer.
                            A reviewer or subject-matter expert checks the expected answer against the cited source evidence.
                        </p>
                        <dl class="evaluation-status-guide">
                            <div><dt>Reviewed</dt><dd>Source-verified and eligible for experiment runs.</dd></div>
                            <div><dt>Needs revision</dt><dd>The question, expected answer, or cited evidence needs correction.</dd></div>
                            <div><dt>Draft</dt><dd>Still being prepared and excluded from runs.</dd></div>
                        </dl>
                    </div>
                    <div class="evaluation-toolbar">
                        <label for="evaluationCategoryFilter">Category</label>
                        <select class="form-select form-select-sm" id="evaluationCategoryFilter">
                            <option value="">All categories</option>
                        </select>
                        <label for="evaluationStatusFilter">Review status</label>
                        <select class="form-select form-select-sm" id="evaluationStatusFilter">
                            <option value="">All statuses</option>
                            <option value="draft">Draft</option>
                            <option value="reviewed">Reviewed</option>
                            <option value="needs_revision">Needs revision</option>
                        </select>
                    </div>
                    <div id="evaluationQuestionList" class="evaluation-question-list" aria-live="polite"></div>
                </section>

                <section class="panel results-panel workspace-view" id="results" data-view-panel="results" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Experiments</span>
                            <h2>Compare immutable runs</h2>
                            <p>A run makes the RAG system answer a selected portion of the reviewed dataset using one fixed configuration.</p>
                        </div>
                        <span class="status status-ready">Four evidence layers</span>
                    </div>

                    <div class="experiment-summary-grid" id="evaluationResultsSummary">
                        <article>
                            <span>Reviewed test set</span>
                            <strong id="experimentDatasetCount">—</strong>
                            <small>questions available</small>
                        </article>
                        <article>
                            <span>Saved experiments</span>
                            <strong id="experimentRunCount">—</strong>
                            <small>immutable runs</small>
                        </article>
                        <article>
                            <span>Active evaluators</span>
                            <strong id="evaluatorCount">—</strong>
                            <small>8 baseline + 5 advanced</small>
                        </article>
                        <article>
                            <span>Human reviews</span>
                            <strong id="experimentHumanReviewCount">—</strong>
                            <small>current rubric decisions</small>
                        </article>
                    </div>
                    <div class="experiment-guide">
                        <span>How to read this view</span>
                        <strong>Dataset questions become responses only after an experiment is run.</strong>
                        <p id="evaluatorSummary">Loading saved FP7 runs and response results...</p>
                    </div>
                    <div class="evaluation-layer-guide" id="evaluationLayerGuide" aria-label="Evaluation evidence layers"></div>
                    <div class="experiment-workspace">
                        <aside class="experiment-browser" aria-label="Saved experiment runs">
                            <div class="subsection-heading">
                                <span>Run history</span>
                                <strong>Choose a saved response</strong>
                            </div>
                            <div id="evaluationRunList" class="evaluation-run-list"></div>
                        </aside>
                        <div id="evaluationResultDetail" class="evaluation-result-detail">
                            <div class="detail-placeholder">
                                <span>Response inspector</span>
                                <strong>Loading the newest saved response</strong>
                                <p>The generated output, reviewed reference, evaluator explanations, and retrieved chunks appear here together.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <section class="panel panel-large workspace-view" id="report" data-view-panel="report" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">FP9 analysis workspace</span>
                            <h2>Findings without a mystery grade</h2>
                            <p>Compare the same metric across configurations, then inspect disagreements and failures before drawing a conclusion.</p>
                        </div>
                        <span class="status status-ready">Live</span>
                    </div>

                    <div class="findings-summary-grid">
                        <article>
                            <span>Baseline methods</span>
                            <strong id="findingBaselineCount">—</strong>
                            <small>transparent diagnostic signals</small>
                        </article>
                        <article>
                            <span>Advanced methods</span>
                            <strong id="findingAdvancedCount">—</strong>
                            <small>RAGAS and rubric judge</small>
                        </article>
                        <article>
                            <span>Human reviews</span>
                            <strong id="findingHumanCount">—</strong>
                            <small>current independent decisions</small>
                        </article>
                    </div>

                    <section class="findings-rules" aria-labelledby="findingsRulesTitle">
                        <div class="subsection-heading">
                            <span>Interpretation rules</span>
                            <strong id="findingsRulesTitle">How conclusions are made</strong>
                        </div>
                        <ol id="findingRules"></ol>
                    </section>

                    <section class="findings-section" aria-labelledby="runComparisonTitle">
                        <div class="subsection-heading">
                            <span>Run evidence</span>
                            <strong id="runComparisonTitle">Configuration and coverage comparison</strong>
                        </div>
                        <div class="finding-run-grid" id="findingRunComparison"></div>
                    </section>

                    <section class="findings-section" aria-labelledby="metricCatalogTitle">
                        <div class="subsection-heading">
                            <span>Evaluator catalog</span>
                            <strong id="metricCatalogTitle">What every score is based on</strong>
                        </div>
                        <div class="finding-metric-catalog" id="findingMetricCatalog"></div>
                    </section>
                </section>
            </div>
        </main>

<?php require __DIR__ . '/includes/footer.php'; ?>
