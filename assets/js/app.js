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
    let documentListRequest = null;
    let ingestionStartedAt = null;
    let ingestionTimer = null;

    $navigation.find('a[href^="#"]').on("click", function () {
        const navigation = bootstrap.Collapse.getInstance($navigation[0]);

        if (navigation) {
            navigation.hide();
        }
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
        if (!Array.isArray(documents) || documents.length === 0) {
            $("<p>").addClass("text-muted").text("No indexed documents were found.").appendTo($documentList);
            return;
        }

        const $stack = $("<div>").addClass("list-stack");
        documents.forEach(function (item) {
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

    loadDocuments();
});
