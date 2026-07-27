<?php

declare(strict_types=1);

require_once __DIR__ . '/config/env.php';
loadEnv();

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
$paidGenerationEnabled = filter_var(
    envValue('ALLOW_PAID_GENERATION', '0'),
    FILTER_VALIDATE_BOOLEAN
);
$defaultRetrievalMethod = envValue('RETRIEVAL_METHOD', 'chroma_vector');
if (!in_array($defaultRetrievalMethod, ['chroma_vector', 'mysql_keyword'], true)) {
    $defaultRetrievalMethod = 'chroma_vector';
}
$defaultTopK = max(1, min(10, (int) envValue('RETRIEVAL_TOP_K', '3')));
$defaultTemperature = max(0.0, min(1.0, (float) envValue('LLM_TEMPERATURE', '0.0')));
$defaultTopP = max(0.0, min(1.0, (float) envValue('LLM_TOP_P', '0.9')));
$topKOptions = [1, 3, 5, 8];
if (!in_array($defaultTopK, $topKOptions, true)) {
    $topKOptions[] = $defaultTopK;
    sort($topKOptions);
}
$temperatureOptions = ['0.0', '0.2', '0.5', '0.8', '1.0'];
$formattedDefaultTemperature = number_format($defaultTemperature, 1, '.', '');
if (!in_array($formattedDefaultTemperature, $temperatureOptions, true)) {
    $temperatureOptions[] = $formattedDefaultTemperature;
    sort($temperatureOptions, SORT_NUMERIC);
}
$topPOptions = ['0.7', '0.9', '1.0'];
$formattedDefaultTopP = number_format($defaultTopP, 1, '.', '');
if (!in_array($formattedDefaultTopP, $topPOptions, true)) {
    $topPOptions[] = $formattedDefaultTopP;
    sort($topPOptions, SORT_NUMERIC);
}
$chatModel = envValue('LLM_CHAT_MODEL', 'gemini-2.5-flash');
$chatModelOptions = array_values(array_unique(array_filter(array_map(
    'trim',
    explode(',', (string) envValue('LLM_CHAT_MODELS', $chatModel . ',gemini-2.5-flash-lite'))
))));
if (!in_array($chatModel, $chatModelOptions, true)) {
    array_unshift($chatModelOptions, $chatModel);
}
$chunkSize = max(1, (int) envValue('CHUNK_SIZE', '800'));
$chunkOverlap = max(0, (int) envValue('CHUNK_OVERLAP', '100'));
$maxTestRunResponses = max(1, (int) envValue('MAX_TEST_RUN_RESPONSES', '5'));

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
                <p class="eyebrow">Metro State RAG assistant</p>
                <h1>Ask, test, and improve your <em>RAG system.</em></h1>
                <p class="topbar-description">Chat with the document collection, manage its sources, run repeatable evaluations, and review what changed.</p>
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
                        <span>Current workflow</span>
                        <strong>04</strong>
                        <small>Documents · chat · gold standard · evaluation</small>
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
                        <span class="stat-label">Indexed chunks</span>
                        <strong id="overviewChunkCount">—</strong>
                        <small>searchable passages in the active index</small>
                    </article>
                    <article class="stat-card">
                        <span class="stat-label">Reviewed prompts</span>
                        <strong id="evaluationQuestionCount">25</strong>
                        <small>questions with expected evidence</small>
                    </article>
                    <article class="stat-card">
                        <span class="stat-label">Evaluation methods</span>
                        <strong id="overviewEvaluatorCount">13</strong>
                        <small>ways to inspect a saved answer</small>
                    </article>
                </div>

                <div class="workflow-strip" aria-label="Evaluation workflow">
                    <article><span>1</span><div><strong>Manage documents</strong><small>Choose the information the assistant can use.</small></div></article>
                    <article><span>2</span><div><strong>Try the chat</strong><small>Adjust retrieval and answer settings for one question.</small></div></article>
                    <article><span>3</span><div><strong>Review the gold standard</strong><small>Verify the questions, expected answers, and evidence.</small></div></article>
                    <article><span>4</span><div><strong>Evaluate saved runs</strong><small>Apply metrics and compare scores, evidence, failures, time, and cost.</small></div></article>
                </div>
            </section>

            <div class="workspace-grid">
                <section class="panel panel-large ask-panel workspace-view" id="ask" data-view-panel="ask" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Chat</span>
                            <h2>Ask the Metro State documents</h2>
                            <p>Choose how the system retrieves evidence and generates this answer. These settings affect this question and are saved with its response.</p>
                        </div>
                        <span class="status <?= $paidGenerationEnabled ? 'status-ready' : 'status-planned' ?>"><?= $paidGenerationEnabled ? 'Generation enabled' : 'Paid calls paused' ?></span>
                    </div>

                    <div class="shared-pipeline-note">
                        <strong>Chat and evaluation runs use the same retrieval-and-answer pipeline.</strong>
                        <p>Chat accepts any question. A batch run sends gold-standard questions through the same pipeline, then compares each saved answer with its reviewed answer and source.</p>
                        <a href="#evaluation">See the gold-standard questions</a>
                    </div>

                    <form class="chat-card" id="askForm" data-generation-enabled="<?= $paidGenerationEnabled ? 'true' : 'false' ?>">
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
                        <fieldset class="chat-settings" aria-describedby="chatSettingsHelp">
                            <div class="chat-settings-heading">
                                <div>
                                    <legend>Optional advanced settings</legend>
                                    <p id="chatSettingsHelp">Most people can keep the recommended defaults. Researchers can change one setting at a time when comparing behavior.</p>
                                </div>
                                <button class="btn btn-sm btn-outline-secondary" id="resetChatSettings" type="button">Reset defaults</button>
                            </div>
                            <div class="chat-settings-grid">
                                <label>
                                    <span>Answer model</span>
                                    <select class="form-select" id="chatModel" data-default="<?= h($chatModel) ?>">
                                        <?php foreach ($chatModelOptions as $model): ?>
                                            <option value="<?= h($model) ?>" <?= $chatModel === $model ? 'selected' : '' ?>><?= h($model) ?><?= $chatModel === $model ? ' · current' : '' ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                    <small>Select a deployment-approved model without editing backend code.</small>
                                </label>
                                <label>
                                    <span>Retrieval</span>
                                    <select class="form-select" id="chatRetrievalMethod" data-default="<?= h($defaultRetrievalMethod) ?>">
                                        <option value="chroma_vector" <?= $defaultRetrievalMethod === 'chroma_vector' ? 'selected' : '' ?>>Vector search (recommended)</option>
                                        <option value="mysql_keyword" <?= $defaultRetrievalMethod === 'mysql_keyword' ? 'selected' : '' ?>>Keyword search</option>
                                    </select>
                                    <small>Vector finds similar meaning; keyword favors exact words and dates.</small>
                                </label>
                                <label>
                                    <span>Sources to retrieve</span>
                                    <select class="form-select" id="chatTopK" data-default="<?= h((string) $defaultTopK) ?>">
                                        <?php foreach ($topKOptions as $value): ?>
                                            <option value="<?= $value ?>" <?= $defaultTopK === $value ? 'selected' : '' ?>><?= $value ?> chunk<?= $value === 1 ? '' : 's' ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                    <small>More chunks add context, but can also add noise.</small>
                                </label>
                                <label>
                                    <span>Temperature</span>
                                    <select class="form-select" id="chatTemperature" data-default="<?= h($formattedDefaultTemperature) ?>">
                                        <?php foreach ($temperatureOptions as $value): ?>
                                            <option value="<?= h($value) ?>" <?= $formattedDefaultTemperature === $value ? 'selected' : '' ?>><?= h($value) ?><?= (float) $value === 0.0 ? ' · repeatable' : '' ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                    <small>Higher values allow more variation in wording.</small>
                                </label>
                                <label>
                                    <span>Top-p</span>
                                    <select class="form-select" id="chatTopP" data-default="<?= h($formattedDefaultTopP) ?>">
                                        <?php foreach ($topPOptions as $value): ?>
                                            <option value="<?= h($value) ?>" <?= $formattedDefaultTopP === $value ? 'selected' : '' ?>><?= h($value) ?><?= abs((float) $value - 0.9) < 0.001 ? ' · recommended' : '' ?></option>
                                        <?php endforeach; ?>
                                    </select>
                                    <small>Controls how broad the model's word choices can be.</small>
                                </label>
                            </div>
                            <div class="chat-settings-footer">
                                <span id="chatSettingsSummary" aria-live="polite"></span>
                                <small>Chunking: <?= h((string) $chunkSize) ?> characters with <?= h((string) $chunkOverlap) ?> overlap</small>
                            </div>
                        </fieldset>
                        <div class="d-flex flex-wrap gap-2 mt-3">
                            <button class="btn btn-primary" id="askButton" type="submit" <?= $paidGenerationEnabled ? '' : 'disabled' ?>>
                                Ask question
                            </button>
                            <button class="btn btn-outline-primary" id="previewSourcesButton" type="button">
                                Preview sources
                            </button>
                            <button class="btn btn-outline-secondary" id="clearQuestionButton" type="button">
                                Clear
                            </button>
                        </div>
                        <?php if (!$paidGenerationEnabled): ?>
                            <p class="generation-safety-note">Model generation is paused until pricing and explicit paid-call flags are configured. “Preview sources” remains available and does not call the model.</p>
                        <?php endif; ?>
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
                            <p><?= $paidGenerationEnabled
                                ? 'Submit a question to see a Gemini answer and the Metro State sources used.'
                                : 'Paid model generation is paused, but you can still preview which sources the selected retrieval settings would use.' ?></p>
                        </div>

                        <div class="answer-loading" id="answerLoadingState" hidden>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span id="answerLoadingText">Retrieving sources and generating an answer...</span>
                        </div>

                        <div class="alert alert-danger mb-0" id="answerErrorState" role="alert" hidden></div>

                        <div id="answerResult" hidden>
                            <span class="preview-label" id="answerResultLabel">Grounded answer</span>
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
                        <span class="status status-ready">Indexed library</span>
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
                        <div class="duplicate-document-prompt" id="duplicateDocumentPrompt" role="alert" hidden>
                            <strong id="duplicateDocumentName"></strong>
                            <span>The current indexed document and all of its old chunks will be removed only after the new file finishes ingesting.</span>
                            <div>
                                <button class="btn btn-sm btn-primary" id="confirmDuplicateReplacement" type="button">Replace existing</button>
                                <button class="btn btn-sm btn-outline-secondary" id="cancelDuplicateUpload" type="button">Cancel upload</button>
                            </div>
                        </div>
                        <div class="alert mt-3 mb-0" id="documentMessage" role="status" hidden></div>
                    </form>

                    <div class="document-list mt-3">
                        <div class="document-library-heading">
                            <div>
                                <h3 class="h6 mb-0">Indexed documents</h3>
                                <small id="documentVisibleCount">Loading the active index…</small>
                            </div>
                            <div class="document-library-actions">
                                <button class="btn btn-sm btn-outline-secondary" id="refreshDocumentsButton" type="button">Refresh</button>
                                <button class="btn btn-sm btn-outline-danger" id="deleteAllDocumentsButton" type="button">Delete all</button>
                            </div>
                        </div>
                        <div class="document-library-toolbar" aria-label="Organize indexed documents">
                            <label>
                                <span>Search</span>
                                <input class="form-control form-control-sm" id="documentSearch" type="search" placeholder="Title or filename">
                            </label>
                            <label>
                                <span>Category</span>
                                <select class="form-select form-select-sm" id="documentCategoryFilter">
                                    <option value="">All categories</option>
                                </select>
                            </label>
                            <label>
                                <span>Type</span>
                                <select class="form-select form-select-sm" id="documentTypeFilter">
                                    <option value="">All types</option>
                                    <option value="txt">TXT</option>
                                    <option value="pdf">PDF</option>
                                    <option value="docx">DOCX</option>
                                </select>
                            </label>
                            <label>
                                <span>Sort</span>
                                <select class="form-select form-select-sm" id="documentSort">
                                    <option value="category">Category</option>
                                    <option value="name">Name</option>
                                    <option value="newest">Newest indexed</option>
                                    <option value="chunks">Most chunks</option>
                                </select>
                            </label>
                        </div>
                        <div id="documentList" aria-live="polite">
                            <p class="text-muted">Loading indexed documents...</p>
                        </div>
                    </div>
                </section>

                <section class="panel panel-large workspace-view" id="evaluation" data-view-panel="evaluation" hidden>
                    <div class="panel-header">
                        <div>
                            <span class="panel-kicker">Gold-standard answer key</span>
                            <h2>Review what the system should be tested against</h2>
                        </div>
                        <span class="status status-ready">Answer key ready</span>
                    </div>
                    <p id="evaluationDatasetSummary">Loading the reviewed test questions...</p>
                    <div class="evaluation-guide" aria-labelledby="datasetReviewGuideTitle">
                            <strong id="datasetReviewGuideTitle">This is the gold standard—not chat history</strong>
                        <p>
                            Each item defines a question, the expected answer, and the source evidence used to check it.
                            Reviewed items can be included in a repeatable batch evaluation; draft items cannot. This page reviews the questions—it does not call the model. During a guarded batch run, each reviewed question goes through the same retrieval-and-answer code used by Chat, and the saved answer is then scored under Evaluation.
                        </p>
                        <div class="evaluation-pipeline" aria-label="How a reviewed question becomes an evaluated result">
                            <span>Reviewed question</span><b aria-hidden="true">→</b>
                            <span>Same Chat pipeline</span><b aria-hidden="true">→</b>
                            <span>Saved answer</span><b aria-hidden="true">→</b>
                            <span>Metric results</span>
                        </div>
                        <dl class="evaluation-status-guide">
                            <div><dt>Reviewed</dt><dd>Source-verified and eligible for batch test runs.</dd></div>
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
                            <span class="panel-kicker">Saved-answer evaluation</span>
                            <h2>Score and inspect saved answers</h2>
                            <p>Choose a saved test, apply any missing scoring methods, and inspect each answer beside its reviewed reference and retrieved evidence.</p>
                        </div>
                        <div class="panel-header-actions">
                            <span class="status status-ready">Saved evidence</span>
                            <button class="btn btn-sm btn-primary" id="newTestRunToggle" type="button">New test run</button>
                            <a class="btn btn-sm btn-outline-secondary" href="#report">Compare runs</a>
                        </div>
                    </div>

                    <form class="new-test-run" id="newTestRunForm" hidden>
                        <div class="new-test-run-heading">
                            <div>
                                <span>Generate new answers</span>
                                <strong>Create a bounded test from the reviewed Gold Standard</strong>
                            </div>
                            <button class="btn btn-sm btn-outline-secondary" id="closeNewTestRun" type="button">Close</button>
                        </div>
                        <p>This calls the selected model once per question, saves each answer and its evidence, and applies the local eight scoring methods. Preview the calls and cost before generating anything.</p>
                        <input id="newTestDatasetId" type="hidden">
                        <div class="new-test-run-grid">
                            <label>
                                <span>Test name</span>
                                <input class="form-control form-control-sm" id="newTestName" maxlength="120" placeholder="Example: Vector search · top-k 3" required>
                            </label>
                            <label>
                                <span>Reviewed questions</span>
                                <select class="form-select form-select-sm" id="newTestLimit">
                                    <?php for ($testLimit = 1; $testLimit <= $maxTestRunResponses; $testLimit++): ?>
                                        <option value="<?= h((string) $testLimit) ?>"><?= h((string) $testLimit) ?> question<?= $testLimit === 1 ? '' : 's' ?></option>
                                    <?php endfor; ?>
                                </select>
                            </label>
                            <label>
                                <span>Model</span>
                                <select class="form-select form-select-sm" id="newTestModel">
                                    <?php foreach ($chatModelOptions as $modelOption): ?>
                                        <option value="<?= h($modelOption) ?>" <?= $modelOption === $chatModel ? 'selected' : '' ?>><?= h($modelOption) ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </label>
                            <label>
                                <span>Retrieval</span>
                                <select class="form-select form-select-sm" id="newTestRetrieval">
                                    <option value="chroma_vector">Vector search</option>
                                    <option value="mysql_keyword">Keyword search</option>
                                </select>
                            </label>
                            <label>
                                <span>Source chunks (top-k)</span>
                                <input class="form-control form-control-sm" id="newTestTopK" type="number" min="1" max="10" step="1" value="<?= h((string) $defaultTopK) ?>">
                            </label>
                            <label>
                                <span>Temperature</span>
                                <input class="form-control form-control-sm" id="newTestTemperature" type="number" min="0" max="1" step="0.1" value="<?= h($formattedDefaultTemperature) ?>">
                            </label>
                            <label>
                                <span>Top-p</span>
                                <input class="form-control form-control-sm" id="newTestTopP" type="number" min="0" max="1" step="0.1" value="<?= h($formattedDefaultTopP) ?>">
                            </label>
                        </div>
                        <small>
                            Current index: <?= h((string) $chunkSize) ?>-character chunks with <?= h((string) $chunkOverlap) ?>-character overlap.
                            Search, model, top-k, temperature, and top-p can vary per test. Testing another chunk size requires rebuilding a separate index so every answer uses one consistent corpus.
                        </small>
                        <div class="new-test-run-actions">
                            <button class="btn btn-sm btn-outline-primary" id="previewNewTestRun" type="button">Preview test</button>
                            <button class="btn btn-sm btn-primary" id="createNewTestRun" type="button" hidden>Generate test</button>
                            <span id="newTestRunStatus" role="status" aria-live="polite">Nothing has been generated.</span>
                        </div>
                    </form>

                    <div class="experiment-summary-grid" id="evaluationResultsSummary">
                        <article>
                            <span>Reviewed test set</span>
                            <strong id="experimentDatasetCount">—</strong>
                            <small>questions available</small>
                        </article>
                        <article>
                            <span>Ready test runs</span>
                            <strong id="experimentRunCount">—</strong>
                            <small id="experimentRunCountNote">completed batches</small>
                        </article>
                        <article>
                            <span>Evaluation methods</span>
                            <strong id="evaluatorCount">—</strong>
                            <small>8 local + 1 judge + 4 RAGAS</small>
                        </article>
                        <article>
                            <span>Human reviews</span>
                            <strong id="experimentHumanReviewCount">—</strong>
                            <small>current rubric decisions</small>
                        </article>
                    </div>
                    <div class="evaluation-boundary" role="note">
                        <strong>Evaluation scores answers that are already saved.</strong>
                        <p>It does not ask the LLM again. A different model, retrieval method, or generation setting requires a new test run so the old and new answers remain comparable.</p>
                    </div>
                    <div class="experiment-guide" aria-label="Evaluation workflow">
                        <span>Start here</span>
                        <strong>1. Choose a saved test · 2. Score missing methods · 3. Open a question and inspect the evidence.</strong>
                        <p id="evaluatorSummary">Loading saved tests and answer results...</p>
                    </div>
                    <details class="evaluation-method-help">
                        <summary>How the 13 scoring methods work and which ones need the Gold Standard</summary>
                        <div class="evaluation-method-note" aria-label="How to interpret the evaluation methods">
                            <strong>Every selected answer lists the methods that completed, failed, were skipped, or have not run.</strong>
                            <p>The methods are independent checks, not steps in a voting system. Do not combine unlike scores into one grade; none of them finds or generates the answer.</p>
                        </div>
                        <div class="metric-dependency-guide" aria-label="Gold-standard dependencies of the evaluation methods">
                            <article>
                                <span>Needs gold-standard data</span>
                                <strong>8 local metrics · LLM judge · RAGAS context precision and recall</strong>
                                <small>These use an expected answer, expected source, required facts, evidence, or answerability label.</small>
                            </article>
                            <article>
                                <span>No gold answer required</span>
                                <strong>RAGAS faithfulness · RAGAS response relevancy</strong>
                                <small>Faithfulness compares the answer with retrieved chunks; relevancy compares the question with the answer.</small>
                            </article>
                            <article>
                                <span>What finds the answer?</span>
                                <strong>Retrieval and the selected LLM—not a scoring method</strong>
                                <small>Scoring methods diagnose quality after the response has already been produced.</small>
                            </article>
                        </div>
                    </details>
                    <div class="experiment-workspace">
                        <aside class="experiment-browser" aria-label="Saved experiment runs">
                            <div class="subsection-heading">
                                <span>Saved tests</span>
                                <strong>Choose a test, then a question</strong>
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
                            <span class="panel-kicker">Run comparison</span>
                            <h2>Compare matching results</h2>
                            <p>Compare the same questions and scores across configurations, then inspect disagreements and failures before drawing a conclusion.</p>
                        </div>
                        <div class="panel-header-actions">
                            <span class="status status-ready">Evidence live</span>
                            <a class="btn btn-sm btn-outline-secondary" href="#results">Back to evaluation</a>
                        </div>
                    </div>

                    <div class="findings-summary-grid">
                        <article>
                            <span>Local methods</span>
                            <strong id="findingBaselineCount">—</strong>
                            <small>transparent diagnostic signals</small>
                        </article>
                        <article>
                            <span>Model-backed methods</span>
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

                    <section class="findings-section" aria-labelledby="matchedComparisonTitle">
                        <div class="subsection-heading">
                            <span>Controlled evidence</span>
                            <strong id="matchedComparisonTitle">Question-matched baseline comparisons</strong>
                        </div>
                        <p class="section-intro">A delta appears only when a comparison run names a baseline and both runs scored the same question with the same evaluator.</p>
                        <div class="matched-comparison-grid" id="findingMatchedComparisons"></div>
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
                            <strong id="metricCatalogTitle">What every score is based on—not a cross-run leaderboard</strong>
                        </div>
                        <div class="finding-metric-catalog" id="findingMetricCatalog"></div>
                    </section>
                </section>
            </div>
        </main>

<?php require __DIR__ . '/includes/footer.php'; ?>
