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
    const $evaluatorCount = $("#evaluatorCount");
    const $evaluatorSummary = $("#evaluatorSummary");
    const $evaluationRunList = $("#evaluationRunList");
    const $evaluationResultDetail = $("#evaluationResultDetail");
    let evaluationQuestions = [];
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
            const $actions = $("<div>").addClass("evaluation-review-actions");
            ["reviewed", "needs_revision", "draft"].forEach(function (nextStatus) {
                $actions.append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("btn btn-sm btn-outline-secondary evaluation-review-button")
                        .prop("disabled", question.review_status === nextStatus)
                        .data({ questionId: question.question_id, reviewStatus: nextStatus })
                        .text(nextStatus === "needs_revision" ? "Needs revision" : nextStatus.charAt(0).toUpperCase() + nextStatus.slice(1))
                );
            });
            $item.append($actions);
            $evaluationQuestionList.append($item);
        });
    }

    function loadEvaluationDataset() {
        $.getJSON("api/evaluations.php")
            .done(function (response) {
                const data = response.data;
                evaluationQuestions = data.questions || [];
                const dataset = data.dataset;
                if (!dataset) {
                    $evaluationDatasetSummary.text("No evaluation dataset has been seeded.");
                    return;
                }
                $evaluationQuestionCount.text(dataset.question_count);
                $evaluationDatasetSummary.text(
                    dataset.dataset_name + " " + dataset.version + ": " + dataset.reviewed_count + " of " + dataset.question_count +
                    " reviewed; " + dataset.unanswerable_count + " unanswerable cases across " + dataset.category_count + " categories."
                );
                $evaluatorCount.text((data.evaluators || []).length + " evaluator definitions registered");
                $evaluatorSummary.text(
                    (data.runs || []).length + " saved runs are available. Scores remain separate by evaluator; select a response to inspect evidence and disagreements."
                );
                const categories = [...new Set(evaluationQuestions.map(function (question) { return question.category; }))].sort();
                $evaluationCategoryFilter.find("option:not(:first)").remove();
                categories.forEach(function (value) {
                    $evaluationCategoryFilter.append($("<option>").val(value).text(value.replaceAll("_", " ")));
                });
                renderEvaluationQuestions();
                renderEvaluationRuns(data.runs || [], data.responses || []);
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
            $run.append($("<strong>").text("Run " + run.run_id + ": " + run.run_name));
            $run.append($("<span>").text(run.status + " · " + run.response_count + " responses · " + run.result_count + " evaluator results"));
            const runResponses = responses.filter(function (response) { return String(response.run_id) === String(run.run_id); });
            const $buttons = $("<div>").addClass("evaluation-response-buttons");
            runResponses.forEach(function (response) {
                $buttons.append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("btn btn-sm btn-outline-primary evaluation-response-button")
                        .data("responseId", response.response_id)
                        .text("Response " + response.response_id + ": " + response.question_text)
                );
            });
            $run.append($buttons);
            $evaluationRunList.append($run);
        });
    }

    function renderEvaluationDetail(data) {
        const response = data.response;
        $evaluationResultDetail.empty().prop("hidden", false);
        $evaluationResultDetail.append($("<h3>").addClass("h5").text("Response " + response.response_id + " inspection"));
        $evaluationResultDetail.append($("<strong>").text(response.question_text));
        $evaluationResultDetail.append($("<p>").text(response.answer_text));
        if (response.expected_answer) {
            $evaluationResultDetail.append($("<p>").addClass("evaluation-expected").text("Expected: " + response.expected_answer));
        }
        const $scores = $("<div>").addClass("evaluation-score-list");
        (data.results || []).forEach(function (result) {
            const score = result.normalized_score === null ? "N/A" : Number(result.normalized_score).toFixed(3);
            const $score = $("<article>").addClass("evaluation-score");
            $score.append($("<strong>").text(result.display_name + ": " + score));
            $score.append($("<span>").text(result.dimension + " · " + result.family + " · " + result.runtime_ms + " ms"));
            $score.append($("<p>").text(result.error_message || result.explanation));
            $scores.append($score);
        });
        $evaluationResultDetail.append($scores);
        const $contexts = $("<details>");
        $contexts.append($("<summary>").text("Retrieved evidence (" + (data.contexts || []).length + ")"));
        (data.contexts || []).forEach(function (context) {
            $contexts.append($("<strong>").text("Rank " + context.rank_position + ": " + (context.source_path || "unknown source")));
            $contexts.append($("<p>").text(context.context_excerpt));
        });
        $evaluationResultDetail.append($contexts);
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
        const $button = $(this);
        $button.prop("disabled", true);
        $.getJSON("api/evaluations.php", { response_id: $button.data("responseId") })
            .done(function (response) {
                renderEvaluationDetail(response.data);
                $evaluationResultDetail[0].scrollIntoView({ behavior: "smooth", block: "nearest" });
            })
            .always(function () { $button.prop("disabled", false); });
    });

    loadDocuments();
    loadEvaluationDataset();
    activateWorkspaceView(window.location.hash.slice(1) || "overview", false);
});
