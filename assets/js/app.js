$(function () {
    const $navigation = $("#mainNavigation");
    const $askForm = $("#askForm");
    const $questionInput = $("#questionInput");
    const $askButton = $("#askButton");
    const $clearButton = $("#clearQuestionButton");
    const $suggestionButtons = $(".suggestion-button");
    const $emptyState = $("#answerEmptyState");
    const $loadingState = $("#answerLoadingState");
    const $errorState = $("#answerErrorState");
    const $answerResult = $("#answerResult");
    const $answerText = $("#answerText");
    const $answerMeta = $("#answerMeta");
    const $sourceList = $("#sourceList");
    const $documentForm = $("#documentUploadForm");
    const $documentFile = $("#documentFile");
    const $documentTitle = $("#documentTitle");
    const $documentCategory = $("#documentCategory");
    const $replaceDocumentId = $("#replaceDocumentId");
    const $cancelReplaceButton = $("#cancelReplaceButton");
    const $uploadDocumentButton = $("#uploadDocumentButton");
    const $uploadSelection = $("#uploadSelection");
    const $documentMessage = $("#documentMessage");
    const $documentList = $("#documentList");
    const $refreshDocumentsButton = $("#refreshDocumentsButton");
    const $documentCount = $("#documentCount");
    const $categoryCount = $("#categoryCount");
    const $evaluationQuestionCount = $("#evaluationQuestionCount");
    const $evaluationDatasetSummary = $("#evaluationDatasetSummary");
    const $evaluationQuestionList = $("#evaluationQuestionList");
    const $evaluationCategoryFilter = $("#evaluationCategoryFilter");
    const $evaluationStatusFilter = $("#evaluationStatusFilter");
    const $experimentDatasetCount = $("#experimentDatasetCount");
    const $experimentRunCount = $("#experimentRunCount");
    const $evaluatorCount = $("#evaluatorCount");
    const $overviewEvaluatorCount = $("#overviewEvaluatorCount");
    const $experimentHumanReviewCount = $("#experimentHumanReviewCount");
    const $evaluatorSummary = $("#evaluatorSummary");
    const $evaluationLayerGuide = $("#evaluationLayerGuide");
    const $evaluationRunList = $("#evaluationRunList");
    const $evaluationResultDetail = $("#evaluationResultDetail");
    const $findingBaselineCount = $("#findingBaselineCount");
    const $findingAdvancedCount = $("#findingAdvancedCount");
    const $findingHumanCount = $("#findingHumanCount");
    const $findingRules = $("#findingRules");
    const $findingRunComparison = $("#findingRunComparison");
    const $findingMetricCatalog = $("#findingMetricCatalog");
    let evaluationQuestions = [];
    let evaluationDatasetQuestionCount = 0;
    let evaluatorCatalog = [];
    let currentEvaluationResponseId = null;
    let documentListRequest = null;
    let ingestionStartedAt = null;
    let ingestionTimer = null;

    const $workspaceViews = $("[data-view-panel]");

    function activateWorkspaceView(viewName, updateHistory) {
        const normalizedView = $workspaceViews.filter('[data-view-panel="' + viewName + '"]').length
            ? viewName
            : "overview";
        $workspaceViews.each(function () {
            $(this).prop("hidden", $(this).data("viewPanel") !== normalizedView);
        });
        $navigation.find("[data-view]").each(function () {
            const isActive = $(this).data("view") === normalizedView;
            $(this).toggleClass("active", isActive).attr("aria-current", isActive ? "page" : null);
        });
        if (updateHistory) {
            window.history.replaceState(null, "", "#" + normalizedView);
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    $(document).on("click", 'a[href^="#"]', function (event) {
        const viewName = String($(this).attr("href") || "").slice(1);
        if ($workspaceViews.filter('[data-view-panel="' + viewName + '"]').length) {
            event.preventDefault();
            activateWorkspaceView(viewName, true);
        }
    });

    $(window).on("hashchange", function () {
        activateWorkspaceView(window.location.hash.slice(1), false);
    });

    function setBusy(isBusy) {
        $questionInput.prop("disabled", isBusy);
        $askButton.prop("disabled", isBusy);
        $clearButton.prop("disabled", isBusy);
        $suggestionButtons.prop("disabled", isBusy);
    }

    function showLoading() {
        $emptyState.prop("hidden", true);
        $errorState.prop("hidden", true).text("");
        $answerResult.prop("hidden", true);
        $loadingState.prop("hidden", false);
        setBusy(true);
    }

    function showError(message) {
        $emptyState.prop("hidden", true);
        $loadingState.prop("hidden", true);
        $answerResult.prop("hidden", true);
        $errorState.prop("hidden", false).text(message);
    }

    function resetAnswer() {
        $loadingState.prop("hidden", true);
        $errorState.prop("hidden", true).text("");
        $answerResult.prop("hidden", true);
        $emptyState.prop("hidden", false);
        $answerText.text("");
        $answerMeta.empty();
        $sourceList.empty();
    }

    function addMeta(label, value) {
        $("<span>")
            .append($("<strong>").text(label + ": "))
            .append(document.createTextNode(value))
            .appendTo($answerMeta);
    }

    function renderSources(sources) {
        $sourceList.empty();

        if (!Array.isArray(sources) || sources.length === 0) {
            $("<p>").addClass("text-muted mb-0").text("No sources were returned.").appendTo($sourceList);
            return;
        }

        sources.forEach(function (source) {
            const distance = Number(source.distance);
            const scoreText = Number.isFinite(distance) ? distance.toFixed(6) : "n/a";
            const $card = $("<article>").addClass("source-card");
            const $heading = $("<div>").addClass("source-heading");

            $("<strong>").text(source.rank + ". " + source.source_path).appendTo($heading);
            $("<span>")
                .text("Chunk " + source.chunk_index + " · distance " + scoreText)
                .appendTo($heading);

            $heading.appendTo($card);
            $("<p>").text(source.text).appendTo($card);
            $card.appendTo($sourceList);
        });
    }

    function showAnswer(result) {
        $loadingState.prop("hidden", true);
        $emptyState.prop("hidden", true);
        $errorState.prop("hidden", true).text("");
        $answerResult.prop("hidden", false);

        $answerText.text(result.answer || "No answer was returned.");
        $answerMeta.empty();
        addMeta("Provider", result.provider || "unknown");
        addMeta("Model", result.model || "unknown");
        addMeta("Top-k", String(result.top_k ?? "unknown"));
        addMeta("Latency", String(result.latency_ms ?? "unknown") + " ms");
        if (result.response_id !== null && result.response_id !== undefined) {
            addMeta("Saved response", "#" + result.response_id);
        }
        if (result.persistence_error) {
            addMeta("Storage warning", result.persistence_error);
        }

        renderSources(result.sources);
    }

    $askForm.on("submit", function (event) {
        event.preventDefault();
        const question = $questionInput.val().trim();

        if (!question) {
            showError("Enter a question before submitting.");
            $questionInput.trigger("focus");
            return;
        }

        showLoading();
        $.ajax({
            url: "api/ask.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ question: question }),
        })
            .done(function (response) {
                if (!response || response.ok !== true || !response.data) {
                    showError("The server returned an incomplete answer.");
                    return;
                }
                showAnswer(response.data);
            })
            .fail(function (xhr, status) {
                if (status === "abort") {
                    return;
                }
                const message = xhr.responseJSON?.error || "The answer could not be generated. Try again.";
                showError(message);
            })
            .always(function () {
                setBusy(false);
            });
    });

    $clearButton.on("click", function () {
        $questionInput.val("").prop("disabled", false).trigger("focus");
        $askButton.prop("disabled", false);
        $suggestionButtons.prop("disabled", false);
        resetAnswer();
    });

    $suggestionButtons.on("click", function () {
        $questionInput.val($(this).data("question")).trigger("focus");
    });

    $questionInput.on("keydown", function (event) {
        if (event.ctrlKey && event.key === "Enter") {
            $askForm.trigger("submit");
        }
    });

    function showDocumentMessage(message, type) {
        $documentMessage
            .removeClass("alert-success alert-danger alert-info")
            .addClass("alert-" + type)
            .text(message)
            .prop("hidden", false);
    }

    function resetReplacement() {
        $replaceDocumentId.val("");
        $cancelReplaceButton.prop("hidden", true);
        $uploadDocumentButton.text("Upload and ingest");
        $uploadSelection.text("");
    }

    function renderDocumentList(documents) {
        $documentList.empty();
        const documentItems = Array.isArray(documents) ? documents : [];
        const categories = new Set(documentItems.map(function (item) {
            return item.category;
        }));
        $documentCount.text(String(documentItems.length));
        $categoryCount.text(String(categories.size));
        if (documentItems.length === 0) {
            $("<p>").addClass("text-muted").text("No indexed documents were found.").appendTo($documentList);
            return;
        }

        const $stack = $("<div>").addClass("list-stack");
        documentItems.forEach(function (item) {
            const $row = $("<article>").addClass("list-item document-item");
            const $details = $("<div>").addClass("document-details");
            $("<strong>").text(item.title).appendTo($details);
            $("<span>")
                .text(item.original_filename + " · " + item.category + " · " + item.chunk_count + " chunks")
                .appendTo($details);
            if (item.ingestion_error) {
                $("<span>").addClass("text-danger").text(item.ingestion_error).appendTo($details);
            }
            $details.appendTo($row);

            const $actions = $("<div>").addClass("document-actions");
            $("<small>").text(String(item.source_type).toUpperCase() + " · " + item.status).appendTo($actions);
            if (String(item.source_path).startsWith("storage/uploads/")) {
                $("<button>")
                    .addClass("btn btn-sm btn-outline-secondary replace-document-button")
                    .attr("type", "button")
                    .data("document", item)
                    .text("Replace")
                    .appendTo($actions);
                $("<button>")
                    .addClass("btn btn-sm btn-outline-danger delete-document-button")
                    .attr("type", "button")
                    .data("document", item)
                    .text("Delete")
                    .appendTo($actions);
            }
            $actions.appendTo($row);
            $row.appendTo($stack);
        });
        $stack.appendTo($documentList);
    }

    function loadDocuments() {
        if (documentListRequest) {
            return documentListRequest;
        }

        const hasRenderedDocuments = $documentList.find(".document-item").length > 0;
        if (!hasRenderedDocuments) {
            $documentList.html('<p class="text-muted">Loading indexed documents...</p>');
        }
        $refreshDocumentsButton.prop("disabled", true).text("Refreshing...");

        const delayedMessage = window.setTimeout(function () {
            if (!hasRenderedDocuments) {
                $documentList.html(
                    '<p class="text-muted">The local server is still working. ' +
                    "If a document is being ingested, this list will appear when it finishes.</p>"
                );
            }
        }, 4000);

        documentListRequest = $.ajax({
            url: "api/documents.php",
            method: "GET",
            dataType: "json",
            timeout: 130000,
        })
            .done(function (response) {
                if (response?.ok !== true) {
                    showDocumentMessage("The document list could not be loaded.", "danger");
                    return;
                }
                renderDocumentList(response.data);
            })
            .fail(function (xhr) {
                showDocumentMessage(xhr.responseJSON?.error || "The document list could not be loaded.", "danger");
                if (!hasRenderedDocuments) {
                    $documentList.html('<p class="text-danger">Document data is unavailable. Use Refresh to try again.</p>');
                }
            })
            .always(function () {
                window.clearTimeout(delayedMessage);
                documentListRequest = null;
                $refreshDocumentsButton.prop("disabled", false).text("Refresh");
            });

        return documentListRequest;
    }

    function startIngestionProgress() {
        ingestionStartedAt = Date.now();
        $refreshDocumentsButton.prop("disabled", true);
        ingestionTimer = window.setInterval(function () {
            const elapsedSeconds = Math.max(1, Math.floor((Date.now() - ingestionStartedAt) / 1000));
            showDocumentMessage(
                "Parsing, chunking, and embedding the document (" + elapsedSeconds + " seconds). " +
                "The first upload after startup can take longer.",
                "info"
            );
        }, 1000);
    }

    function stopIngestionProgress() {
        window.clearInterval(ingestionTimer);
        ingestionTimer = null;
        ingestionStartedAt = null;
    }

    $documentFile.on("change", function () {
        const file = this.files[0];
        if (!file) {
            $uploadSelection.text("");
            return;
        }
        $uploadSelection.text(file.name + " · " + Math.ceil(file.size / 1024) + " KB");
        if (!$documentTitle.val().trim()) {
            $documentTitle.val(file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
        }
    });

    $documentList.on("click", ".replace-document-button", function () {
        const item = $(this).data("document");
        $replaceDocumentId.val(item.document_id);
        $documentTitle.val(item.title);
        $documentCategory.val(item.category);
        $cancelReplaceButton.prop("hidden", false);
        $uploadDocumentButton.text("Replace and re-ingest");
        showDocumentMessage("Choose a new " + String(item.source_type).toUpperCase() + " file for " + item.title + ".", "info");
        $documentFile.trigger("focus");
    });

    $documentList.on("click", ".delete-document-button", function () {
        const $button = $(this);
        const item = $button.data("document");
        if (!window.confirm("Delete " + item.title + " from MySQL, ChromaDB, and upload storage?")) {
            return;
        }

        $button.prop("disabled", true).text("Deleting...");
        showDocumentMessage("Removing the document and its indexed chunks...", "info");
        $.ajax({
            url: "api/documents.php",
            method: "DELETE",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ document_id: item.document_id }),
        })
            .done(function () {
                showDocumentMessage("Document deleted.", "success");
                loadDocuments();
            })
            .fail(function (xhr) {
                showDocumentMessage(xhr.responseJSON?.error || "Document deletion failed.", "danger");
                $button.prop("disabled", false).text("Delete");
            });
    });

    $cancelReplaceButton.on("click", function () {
        resetReplacement();
        $documentForm[0].reset();
        $documentMessage.prop("hidden", true).text("");
    });

    $refreshDocumentsButton.on("click", function () {
        loadDocuments();
    });

    $documentForm.on("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(this);
        $uploadDocumentButton.prop("disabled", true).text("Parsing and ingesting...");
        $cancelReplaceButton.prop("disabled", true);
        showDocumentMessage(
            "Parsing, chunking, and embedding the document. Keep this page open; the indexed list will remain visible.",
            "info"
        );
        startIngestionProgress();

        $.ajax({
            url: "api/documents.php",
            method: "POST",
            data: formData,
            processData: false,
            contentType: false,
            dataType: "json",
        })
            .done(function (response) {
                showDocumentMessage("Document ingested with " + response.data.chunk_count + " chunks.", "success");
                $documentForm[0].reset();
                resetReplacement();
                loadDocuments();
            })
            .fail(function (xhr) {
                showDocumentMessage(xhr.responseJSON?.error || "Document ingestion failed.", "danger");
            })
            .always(function () {
                stopIngestionProgress();
                $uploadDocumentButton.prop("disabled", false);
                $cancelReplaceButton.prop("disabled", false);
                $refreshDocumentsButton.prop("disabled", false);
                $uploadDocumentButton.text($replaceDocumentId.val() ? "Replace and re-ingest" : "Upload and ingest");
            });
    });

    function renderEvaluationQuestions() {
        const category = $evaluationCategoryFilter.val();
        const status = $evaluationStatusFilter.val();
        const filtered = evaluationQuestions.filter(function (question) {
            return (!category || question.category === category) && (!status || question.review_status === status);
        });
        $evaluationQuestionList.empty();
        if (!filtered.length) {
            $evaluationQuestionList.append($("<p>").addClass("text-muted").text("No questions match these filters."));
            return;
        }
        filtered.forEach(function (question) {
            const $item = $("<article>").addClass("evaluation-question");
            const $heading = $("<div>").addClass("evaluation-question-heading");
            $heading.append($("<strong>").text(question.display_order + ". " + question.question_text));
            $heading.append($("<span>").addClass("status status-" + (question.review_status === "reviewed" ? "ready" : "planned")).text(question.review_status.replace("_", " ")));
            $item.append($heading);
            $item.append($("<p>").text(question.expected_answer));
            $item.append($("<small>").text(question.category + " · " + question.difficulty + " · " + (Number(question.is_answerable) ? "answerable" : "unanswerable")));
            if (question.expected_source || question.expected_evidence) {
                const $evidence = $("<details>").addClass("evaluation-reference");
                $evidence.append($("<summary>").text("Review cited source evidence"));
                if (question.expected_source) {
                    $evidence.append($("<strong>").text("Expected source: " + question.expected_source));
                }
                if (question.expected_evidence) {
                    $evidence.append($("<blockquote>").text(question.expected_evidence));
                }
                $item.append($evidence);
            }
            const $actions = $("<div>").addClass("evaluation-review-actions").attr("aria-label", "Test-case review status");
            ["reviewed", "needs_revision", "draft"].forEach(function (nextStatus) {
                const labels = {
                    reviewed: "Mark reviewed",
                    needs_revision: "Mark needs revision",
                    draft: "Mark draft",
                };
                $actions.append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("btn btn-sm btn-outline-secondary evaluation-review-button")
                        .prop("disabled", question.review_status === nextStatus)
                        .data({ questionId: question.question_id, reviewStatus: nextStatus })
                        .text(question.review_status === nextStatus ? labels[nextStatus].replace("Mark ", "Currently ") : labels[nextStatus])
                );
            });
            $item.append($actions);
            $evaluationQuestionList.append($item);
        });
    }

    function readable(value, fallback) {
        if (value === null || value === undefined || value === "") {
            return fallback || "Not recorded";
        }
        return String(value).replaceAll("_", " ");
    }

    function compactNumber(value, digits) {
        const number = Number(value);
        return Number.isFinite(number) ? number.toFixed(digits === undefined ? 3 : digits) : "N/A";
    }

    function renderEvaluationLayers(findings) {
        const layerCounts = findings.layers || {};
        const layers = [
            {
                key: "baseline",
                number: "01",
                title: "Baseline diagnostics",
                text: (layerCounts.baseline || 0) + " transparent rules and similarity measures expose basic strengths and failures.",
            },
            {
                key: "advanced",
                number: "02",
                title: "Advanced evaluators",
                text: (layerCounts.advanced || 0) + " RAGAS or rubric-judge methods assess grounded quality with model-backed reasoning.",
            },
            {
                key: "human",
                number: "03",
                title: "Human review",
                text: (findings.human_review_count || 0) + " current rubric decisions provide calibration evidence—not automatic ground truth.",
            },
            {
                key: "operations",
                number: "04",
                title: "Operations",
                text: "Latency, attempts, failures, token use, and estimated cost show whether a method is practical and repeatable.",
            },
        ];
        $evaluationLayerGuide.empty();
        layers.forEach(function (layer) {
            const $card = $("<article>").addClass("evaluation-layer layer-" + layer.key);
            $card.append($("<span>").text(layer.number));
            $card.append($("<div>").append($("<strong>").text(layer.title), $("<p>").text(layer.text)));
            $evaluationLayerGuide.append($card);
        });
    }

    function appendContract($container, configuration) {
        const contract = configuration || {};
        const direction = contract.direction === "higher_is_better" ? "score ≥"
            : contract.direction === "lower_is_better" ? "score ≤" : readable(contract.direction, "score");
        const $details = $("<details>").addClass("score-contract");
        $details.append($("<summary>").text("What this score means"));
        const fields = [
            ["Question", contract.question],
            ["Compared with", contract.comparison_target],
            ["Calculation", contract.calculation],
            ["Scale", contract.scale],
            ["Review rule", contract.threshold === null || contract.threshold === undefined
                ? "No threshold; inspect the value directly."
                : direction + " " + contract.threshold + " (" + readable(contract.threshold_status, "status unknown") + ")"],
            ["Limitation", contract.limitation],
        ];
        const $list = $("<dl>");
        fields.forEach(function (field) {
            if (field[1] !== null && field[1] !== undefined && field[1] !== "") {
                $list.append($("<div>").append($("<dt>").text(field[0]), $("<dd>").text(field[1])));
            }
        });
        $details.append($list);
        $container.append($details);
    }

    function renderFindings(data) {
        const findings = data.findings || {};
        const layers = findings.layers || {};
        $findingBaselineCount.text(layers.baseline || 0);
        $findingAdvancedCount.text(layers.advanced || 0);
        $findingHumanCount.text(findings.human_review_count || 0);

        $findingRules.empty();
        (findings.interpretation_rules || []).forEach(function (rule) {
            $findingRules.append($("<li>").text(rule));
        });

        $findingRunComparison.empty();
        (data.runs || []).forEach(function (run) {
            const $card = $("<article>").addClass("finding-run-card");
            const configuration = run.run_configuration_json || {};
            const coverage = Number(run.dataset_question_count)
                ? Math.round((Number(run.response_count) / Number(run.dataset_question_count)) * 100)
                : 0;
            $card.append($("<div>").addClass("finding-run-title").append(
                $("<span>").text("Run " + run.run_id),
                $("<strong>").text(run.run_name),
                $("<em>").addClass("run-status run-status-" + run.status).text(run.status)
            ));
            $card.append($("<p>").text(
                readable(run.retrieval_method, "retrieval unknown") + " retrieval · top " + run.top_k +
                " · " + (run.response_count || 0) + "/" + (run.dataset_question_count || evaluationDatasetQuestionCount) +
                " responses (" + coverage + "% coverage)"
            ));
            const $facts = $("<dl>").addClass("finding-run-facts");
            [
                ["Experiment", run.experiment_key || "not labeled"],
                ["Corpus", run.corpus_variant_key || "full corpus"],
                ["Evaluator results", (run.result_count || 0) + " canonical"],
                ["Evaluator attempts", (run.evaluator_attempt_count || 0) + " retained"],
                ["Skipped / failed", (run.evaluator_skipped_count || 0) + " / " + (run.evaluator_error_count || 0)],
                ["Evaluator runtime", compactNumber((Number(run.evaluator_runtime_ms) || 0) / 1000, 2) + " s"],
                ["Recorded evaluator cost", "$" + compactNumber(run.evaluator_estimated_cost || 0, 6)],
            ].forEach(function (fact) {
                $facts.append($("<div>").append($("<dt>").text(fact[0]), $("<dd>").text(fact[1])));
            });
            $card.append($facts);
            if (configuration.change_from_baseline) {
                $card.append($("<p>").addClass("finding-change-note").text("Changed variable: " + configuration.change_from_baseline));
            }
            $findingRunComparison.append($card);
        });
        if (!$findingRunComparison.children().length) {
            $findingRunComparison.append($("<p>").addClass("text-muted").text("No experiment runs have been saved."));
        }

        $findingMetricCatalog.empty();
        (findings.metric_summaries || []).forEach(function (metric) {
            const config = metric.configuration_json || {};
            const $card = $("<article>").addClass("finding-metric metric-" + (metric.layer || "baseline"));
            $card.append($("<div>").addClass("finding-metric-heading").append(
                $("<span>").text(readable(metric.layer, "baseline")),
                $("<strong>").text(metric.display_name)
            ));
            $card.append($("<p>").text(config.question || "No score question documented."));
            const completed = Number(metric.completed_count) || 0;
            $card.append($("<small>").text(completed
                ? completed + " completed · observed mean " + compactNumber(metric.mean_score) +
                    " · range " + compactNumber(metric.min_score) + "–" + compactNumber(metric.max_score)
                : "Not run yet · no observed scores are being inferred"
            ));
            $card.append($("<small>").addClass("metric-operations").text(
                (metric.attempt_count || 0) + " attempts · mean runtime " +
                compactNumber(metric.mean_runtime_ms || 0, 1) + " ms · recorded cost $" +
                compactNumber(metric.estimated_cost || 0, 6)
            ));
            appendContract($card, config);
            $findingMetricCatalog.append($card);
        });
    }

    function loadEvaluationDataset() {
        $.getJSON("api/evaluations.php")
            .done(function (response) {
                const data = response.data;
                evaluationQuestions = data.questions || [];
                evaluatorCatalog = data.evaluators || [];
                const dataset = data.dataset;
                if (!dataset) {
                    evaluationDatasetQuestionCount = 0;
                    $evaluationDatasetSummary.text("No evaluation dataset has been seeded.");
                    return;
                }
                evaluationDatasetQuestionCount = Number(dataset.question_count) || 0;
                $evaluationQuestionCount.text(dataset.question_count);
                $experimentDatasetCount.text(dataset.question_count);
                $experimentRunCount.text((data.runs || []).length);
                $evaluationDatasetSummary.text(
                    dataset.dataset_name + " " + dataset.version + ": " + dataset.reviewed_count + " of " + dataset.question_count +
                    " reviewed; " + dataset.unanswerable_count + " unanswerable cases across " + dataset.category_count + " categories."
                );
                $evaluatorCount.text(evaluatorCatalog.length);
                $overviewEvaluatorCount.text(evaluatorCatalog.length);
                $experimentHumanReviewCount.text(data.findings?.human_review_count || 0);
                $evaluatorSummary.text(
                    "Each method answers a different quality question. Open a response to inspect its basis, threshold status, attempts, and exact evidence; do not combine unlike scores into one grade."
                );
                const categories = [...new Set(evaluationQuestions.map(function (question) { return question.category; }))].sort();
                $evaluationCategoryFilter.find("option:not(:first)").remove();
                categories.forEach(function (value) {
                    $evaluationCategoryFilter.append($("<option>").val(value).text(value.replaceAll("_", " ")));
                });
                renderEvaluationQuestions();
                renderEvaluationLayers(data.findings || {});
                renderEvaluationRuns(data.runs || [], data.responses || []);
                renderFindings(data);
            })
            .fail(function () {
                $evaluationDatasetSummary.text("Evaluation data could not be loaded. Run the FP7 schema and seed commands.");
            });
    }

    function renderEvaluationRuns(runs, responses) {
        $evaluationRunList.empty();
        if (!runs.length) {
            $evaluationRunList.append($("<p>").addClass("text-muted").text("No controlled evaluation runs have been saved yet."));
            return;
        }
        runs.forEach(function (run) {
            const $run = $("<article>").addClass("evaluation-run");
            const responseCount = Number(run.response_count) || 0;
            const resultCount = Number(run.result_count) || 0;
            const coverage = evaluationDatasetQuestionCount
                ? responseCount + " of " + evaluationDatasetQuestionCount + " dataset questions answered"
                : responseCount + " responses";
            const $runHeading = $("<div>").addClass("evaluation-run-heading");
            $runHeading.append($("<strong>").text("Run " + run.run_id));
            $runHeading.append($("<span>").addClass("run-status run-status-" + run.status).text(run.status));
            $run.append($runHeading);
            $run.append($("<h3>").text(run.run_name));
            $run.append($("<span>").addClass("evaluation-run-meta").text(
                coverage + " · " + resultCount + " results · " + readable(run.retrieval_method, "unknown") + " retrieval"
            ));
            const skipped = Number(run.evaluator_skipped_count) || 0;
            const failed = Number(run.evaluator_error_count) || 0;
            if (skipped || failed) {
                $run.append($("<p>").addClass("evaluation-run-note").text(
                    skipped + " evaluator skips · " + failed + " evaluator failures (not treated as zero scores)."
                ));
            }
            if (run.status === "failed") {
                $run.append($("<p>").addClass("evaluation-run-warning").text(
                    "This setup attempt failed. A response may have been saved before evaluation stopped, so zero evaluator results is expected."
                ));
            } else if (evaluationDatasetQuestionCount && responseCount < evaluationDatasetQuestionCount) {
                $run.append($("<p>").addClass("evaluation-run-note").text(
                    "Limited proof run: this is not a complete evaluation of the " + evaluationDatasetQuestionCount + "-question dataset."
                ));
            }
            const runResponses = responses.filter(function (response) { return String(response.run_id) === String(run.run_id); });
            const $buttons = $("<div>").addClass("evaluation-response-buttons");
            runResponses.forEach(function (response) {
                const layers = (response.baseline_result_count || 0) + " baseline · " +
                    (response.advanced_result_count || 0) + " advanced · " +
                    (response.human_review_count || 0) + " human";
                $buttons.append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("btn btn-sm btn-outline-primary evaluation-response-button")
                        .data("responseId", response.response_id)
                        .append(
                            $("<strong>").text("Response " + response.response_id + ": " + response.question_text),
                            $("<small>").text(layers)
                        )
                );
            });
            if (!runResponses.length) {
                $buttons.append($("<p>").addClass("text-muted mb-0").text("No saved responses are available for this run."));
            }
            $run.append($buttons);
            $evaluationRunList.append($run);
        });
        let $responseToOpen = $evaluationRunList.find(".evaluation-response-button").first();
        if (currentEvaluationResponseId) {
            const $current = $evaluationRunList.find(".evaluation-response-button").filter(function () {
                return Number($(this).data("responseId")) === currentEvaluationResponseId;
            }).first();
            if ($current.length) {
                $responseToOpen = $current;
            }
        }
        if ($responseToOpen.length) {
            loadEvaluationResponse($responseToOpen, false);
        }
    }

    function renderScoreCard(result, attempts) {
        const status = result.status || "completed";
        const passed = result.passed === null ? null : Number(result.passed) === 1;
        const cardState = status === "failed" ? "score-failed"
            : status === "skipped" ? "score-skipped"
                : passed === null ? "score-neutral" : passed ? "score-pass" : "score-review";
        const $score = $("<article>").addClass("evaluation-score " + cardState);
        const $scoreHeader = $("<div>").addClass("score-heading");
        $scoreHeader.append($("<strong>").text(result.display_name));
        $scoreHeader.append($("<b>").text(status === "completed" ? compactNumber(result.normalized_score) : readable(status)));
        $score.append($scoreHeader);
        $score.append($("<span>").text(
            readable(result.dimension) + " · " + readable(result.family) + " · " + (result.runtime_ms || 0) + " ms"
        ));
        $score.append($("<p>").text(result.error_message || result.explanation || "No explanation was recorded."));

        const attemptCount = Number(result.attempt_count) || 0;
        if (attemptCount > 1) {
            $score.append($("<p>").addClass("attempt-summary").text(
                attemptCount + " attempts · mean " + compactNumber(result.attempt_mean) +
                " · range " + compactNumber(result.attempt_min) + "–" + compactNumber(result.attempt_max) +
                " · σ " + compactNumber(result.attempt_stddev)
            ));
        } else {
            $score.append($("<p>").addClass("attempt-summary").text(attemptCount + " recorded attempt" + (attemptCount === 1 ? "" : "s")));
        }
        appendContract($score, result.configuration_json || {});
        const latestAttempt = attempts.length ? attempts[attempts.length - 1] : null;
        const auditConfiguration = Object.assign(
            {},
            result.configuration_json || {},
            latestAttempt?.configuration_json || {}
        );
        const $audit = $("<details>").addClass("score-audit");
        $audit.append($("<summary>").text("Run and version details"));
        const $auditList = $("<dl>");
        [
            ["Evaluator version", auditConfiguration.evaluator_version || result.version],
            ["Implementation", auditConfiguration.implementation],
            ["Framework", auditConfiguration.framework],
            ["Provider / model", [auditConfiguration.provider, auditConfiguration.model].filter(Boolean).join(" / ")],
            ["Embedding model", auditConfiguration.embedding_model],
            ["Rubric version", auditConfiguration.rubric_version],
            ["Prompt hash", auditConfiguration.prompt_hash],
            ["Attempt policy", auditConfiguration.canonical_policy],
            ["Tokens", latestAttempt?.total_tokens],
            ["Recorded cost", latestAttempt?.estimated_cost === null || latestAttempt?.estimated_cost === undefined
                ? null : "$" + compactNumber(latestAttempt.estimated_cost, 8)],
        ].forEach(function (field) {
            if (field[1] !== null && field[1] !== undefined && field[1] !== "") {
                $auditList.append($("<div>").append($("<dt>").text(field[0]), $("<dd>").text(field[1])));
            }
        });
        $audit.append($auditList);
        if (latestAttempt?.details_json && Object.keys(latestAttempt.details_json).length) {
            $audit.append($("<strong>").text("Structured result details"));
            $audit.append($("<pre>").text(JSON.stringify(latestAttempt.details_json, null, 2)));
        }
        if (latestAttempt?.raw_provider_output) {
            $audit.append($("<strong>").text("Raw provider output"));
            $audit.append($("<pre>").text(latestAttempt.raw_provider_output));
        }
        $score.append($audit);
        return $score;
    }

    function appendHumanReviewSection(data) {
        const reviews = data.human_reviews || [];
        const $section = $("<section>").addClass("human-review-section");
        const $heading = $("<div>").addClass("subsection-heading").append(
            $("<span>").text("Human layer"),
            $("<strong>").text(reviews.length ? reviews.length + " current review" + (reviews.length === 1 ? "" : "s") : "No review recorded yet")
        );
        $section.append($heading);
        reviews.forEach(function (review) {
            const $review = $("<article>").addClass("human-review-card");
            $review.append($("<div>").append(
                $("<strong>").text(review.reviewer_alias),
                $("<span>").text(readable(review.overall_decision))
            ));
            const ratings = ["correctness", "completeness", "faithfulness", "relevance", "refusal_correctness"]
                .filter(function (key) { return review[key] !== null; })
                .map(function (key) { return readable(key) + " " + review[key] + "/5"; });
            $review.append($("<small>").text(ratings.length ? ratings.join(" · ") : "No numeric ratings supplied"));
            if (review.failure_category) {
                $review.append($("<p>").text("Failure category: " + readable(review.failure_category)));
            }
            if (review.notes) {
                $review.append($("<p>").text(review.notes));
            }
            $section.append($review);
        });

        const $form = $("<form>").addClass("human-review-form").attr("id", "humanReviewForm");
        $form.append($("<p>").text("Rate only dimensions you can support from the reference and retrieved evidence. Blank ratings are allowed."));
        const $identityRow = $("<div>").addClass("review-form-grid");
        $identityRow.append($("<label>").text("Reviewer name").append(
            $("<input>").addClass("form-control").attr({ name: "reviewer_alias", maxlength: 120, required: true, placeholder: "Your name or initials" })
        ));
        $identityRow.append($("<label>").text("Overall decision").append(
            $("<select>").addClass("form-select").attr({ name: "overall_decision", required: true }).append(
                $("<option>").val("").text("Choose a decision"),
                $("<option>").val("acceptable").text("Acceptable"),
                $("<option>").val("needs_revision").text("Needs revision"),
                $("<option>").val("incorrect").text("Incorrect"),
                $("<option>").val("not_applicable").text("Not applicable")
            )
        ));
        $form.append($identityRow);
        const $ratings = $("<div>").addClass("review-rating-grid");
        ["correctness", "completeness", "faithfulness", "relevance", "refusal_correctness"].forEach(function (key) {
            const $select = $("<select>").addClass("form-select").attr("name", key)
                .append($("<option>").val("").text("Not rated"));
            for (let rating = 1; rating <= 5; rating += 1) {
                $select.append($("<option>").val(rating).text(rating + (rating === 1 ? " — poor" : rating === 5 ? " — strong" : "")));
            }
            $ratings.append($("<label>").text(readable(key)).append($select));
        });
        $form.append($ratings);
        $form.append($("<label>").text("Failure category").append(
            $("<select>").addClass("form-select").attr("name", "failure_category").append(
                ["none", "retrieval_miss", "source_ranked_low", "insufficient_context", "unsupported_generation", "incomplete_answer", "incorrect_answer", "incorrect_refusal", "over_refusal", "misleading_metric", "evaluator_failure", "ambiguous_question"]
                    .map(function (value) { return $("<option>").val(value).text(readable(value)); })
            )
        ));
        $form.append($("<label>").text("Evidence-backed notes").append(
            $("<textarea>").addClass("form-control").attr({ name: "notes", rows: 3, maxlength: 5000, placeholder: "Explain the specific fact, evidence, or failure that supports this decision." })
        ));
        $form.append($("<div>").addClass("review-submit-row").append(
            $("<button>").addClass("btn btn-primary").attr("type", "submit").text("Save human review"),
            $("<span>").addClass("human-review-message").attr({ role: "status", "aria-live": "polite" })
        ));
        $section.append($form);
        $evaluationResultDetail.append($section);
    }

    function renderEvaluationDetail(data) {
        const response = data.response;
        currentEvaluationResponseId = Number(response.response_id);
        $evaluationResultDetail.empty().prop("hidden", false);
        const $header = $("<div>").addClass("response-detail-header");
        const $headerCopy = $("<div>");
        $headerCopy.append($("<span>").text("Run " + response.run_id + " · Response " + response.response_id));
        $headerCopy.append($("<h3>").text(response.question_text));
        $header.append($headerCopy);
        $header.append($("<small>").text(response.run_name || "Saved experiment"));
        $evaluationResultDetail.append($header);

        const $comparison = $("<div>").addClass("answer-comparison");
        $comparison.append($("<article>").append(
            $("<span>").text("Generated answer"), $("<p>").text(response.answer_text)
        ));
        $comparison.append($("<article>").addClass("reference-answer").append(
            $("<span>").text("Reviewed reference"), $("<p>").text(response.expected_answer || "No reference answer applies.")
        ));
        $evaluationResultDetail.append($comparison);

        const $meta = $("<div>").addClass("response-meta");
        $meta.append($("<span>").text((Number(response.is_answerable) ? "Answerable" : "Unanswerable") + " test case"));
        $meta.append($("<span>").text(readable(response.retrieval_method) + " retrieval"));
        $meta.append($("<span>").text((response.latency_ms || 0) + " ms answer latency"));
        if (response.chat_model) {
            $meta.append($("<span>").text(response.chat_model));
        }
        if (response.expected_source) {
            $meta.append($("<span>").text("Expected source: " + response.expected_source));
        }
        $evaluationResultDetail.append($meta);

        const results = data.results || [];
        const resultAttempts = data.attempts || [];
        ["baseline", "advanced"].forEach(function (layer) {
            const layerResults = results.filter(function (result) { return result.layer === layer; });
            const catalogMethods = evaluatorCatalog.filter(function (evaluator) { return evaluator.layer === layer; });
            const $section = $("<section>").addClass("score-layer-section");
            $section.append($("<div>").addClass("subsection-heading").append(
                $("<span>").text(layer + " layer"),
                $("<strong>").text(layerResults.length + " of " + catalogMethods.length + " methods recorded")
            ));
            if (layerResults.length) {
                const $scores = $("<div>").addClass("evaluation-score-list");
                layerResults.forEach(function (result) {
                    const attempts = resultAttempts.filter(function (attempt) {
                        return attempt.evaluator_key === result.evaluator_key;
                    });
                    $scores.append(renderScoreCard(result, attempts));
                });
                $section.append($scores);
            } else {
                $section.append($("<div>").addClass("layer-empty-state").append(
                    $("<strong>").text(layer === "advanced" ? "Advanced evaluation has not been run for this response." : "No baseline results were saved."),
                    $("<p>").text(layer === "advanced"
                        ? "This is missing evidence, not a zero score. Run the FP8 advanced evaluator command after reviewing its paid-call preflight."
                        : "Run the local baseline evaluator to create transparent diagnostic results.")
                ));
            }
            $evaluationResultDetail.append($section);
        });

        const disagreements = data.disagreements || [];
        if (disagreements.length) {
            const $disagreement = $("<section>").addClass("disagreement-panel").append($("<strong>").text("Signals worth investigating"));
            disagreements.forEach(function (item) {
                $disagreement.append($("<article>").append($("<span>").text(item.title), $("<p>").text(item.explanation)));
            });
            $evaluationResultDetail.append($disagreement);
        }

        appendHumanReviewSection(data);

        const $contexts = $("<details>").addClass("retrieved-evidence").prop("open", true);
        $contexts.append($("<summary>").text("Retrieved evidence (" + (data.contexts || []).length + ")"));
        (data.contexts || []).forEach(function (context) {
            const $context = $("<article>").toggleClass("expected-evidence", Boolean(context.is_expected_source));
            $context.append($("<strong>").text(
                "Rank " + context.rank_position + ": " + (context.source_path || "unknown source") +
                (context.is_expected_source ? " · expected source" : "")
            ));
            $context.append($("<p>").text(context.context_excerpt));
            $contexts.append($context);
        });
        $evaluationResultDetail.append($contexts);
    }

    function loadEvaluationResponse($button, shouldScroll) {
        $evaluationRunList.find(".evaluation-response-button").removeClass("active").attr("aria-pressed", "false");
        $button.addClass("active").attr("aria-pressed", "true").prop("disabled", true);
        $.getJSON("api/evaluations.php", { response_id: $button.data("responseId") })
            .done(function (response) {
                renderEvaluationDetail(response.data);
                if (shouldScroll) {
                    $evaluationResultDetail[0].scrollIntoView({ behavior: "smooth", block: "start" });
                }
            })
            .fail(function () {
                $evaluationResultDetail.empty().append(
                    $("<div>").addClass("alert alert-danger mb-0").text("The saved response could not be loaded.")
                );
            })
            .always(function () { $button.prop("disabled", false); });
    }

    $evaluationCategoryFilter.add($evaluationStatusFilter).on("change", renderEvaluationQuestions);
    $evaluationQuestionList.on("click", ".evaluation-review-button", function () {
        const $button = $(this);
        $button.prop("disabled", true);
        $.ajax({
            url: "api/evaluations.php",
            method: "PATCH",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ question_id: $button.data("questionId"), review_status: $button.data("reviewStatus") }),
        }).done(loadEvaluationDataset).fail(function () {
            $button.prop("disabled", false);
        });
    });

    $evaluationRunList.on("click", ".evaluation-response-button", function () {
        loadEvaluationResponse($(this), true);
    });

    $evaluationResultDetail.on("submit", "#humanReviewForm", function (event) {
        event.preventDefault();
        const $form = $(this);
        const $button = $form.find('button[type="submit"]');
        const $message = $form.find(".human-review-message");
        const payload = { action: "human_review", response_id: currentEvaluationResponseId };
        $form.serializeArray().forEach(function (field) {
            payload[field.name] = field.value;
        });
        $button.prop("disabled", true);
        $message.removeClass("text-danger review-success").text("Saving evidence-backed review…");
        $.ajax({
            url: "api/evaluations.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify(payload),
        }).done(function () {
            $message.addClass("review-success").text("Review saved. Updating the evidence view…");
            loadEvaluationDataset();
        }).fail(function (xhr) {
            $message.addClass("text-danger").text(xhr.responseJSON?.error || "The review could not be saved.");
            $button.prop("disabled", false);
        });
    });

    loadDocuments();
    loadEvaluationDataset();
    activateWorkspaceView(window.location.hash.slice(1) || "overview", false);
});
