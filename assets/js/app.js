$(function () {
    const $navigation = $("#mainNavigation");
    const $askForm = $("#askForm");
    const $questionInput = $("#questionInput");
    const $askButton = $("#askButton");
    const $previewSourcesButton = $("#previewSourcesButton");
    const $clearButton = $("#clearQuestionButton");
    const $resetChatSettings = $("#resetChatSettings");
    const $chatModel = $("#chatModel");
    const $chatRetrievalMethod = $("#chatRetrievalMethod");
    const $chatTopK = $("#chatTopK");
    const $chatTemperature = $("#chatTemperature");
    const $chatTopP = $("#chatTopP");
    const $chatSettingsControls = $chatModel.add($chatRetrievalMethod).add($chatTopK).add($chatTemperature).add($chatTopP);
    const $chatSettingsSummary = $("#chatSettingsSummary");
    const $suggestionButtons = $(".suggestion-button");
    const $emptyState = $("#answerEmptyState");
    const $loadingState = $("#answerLoadingState");
    const $loadingText = $("#answerLoadingText");
    const $errorState = $("#answerErrorState");
    const $answerResult = $("#answerResult");
    const $answerResultLabel = $("#answerResultLabel");
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
    const $duplicateDocumentPrompt = $("#duplicateDocumentPrompt");
    const $duplicateDocumentName = $("#duplicateDocumentName");
    const $confirmDuplicateReplacement = $("#confirmDuplicateReplacement");
    const $cancelDuplicateUpload = $("#cancelDuplicateUpload");
    const $documentMessage = $("#documentMessage");
    const $documentList = $("#documentList");
    const $refreshDocumentsButton = $("#refreshDocumentsButton");
    const $deleteAllDocumentsButton = $("#deleteAllDocumentsButton");
    const $documentSearch = $("#documentSearch");
    const $documentCategoryFilter = $("#documentCategoryFilter");
    const $documentTypeFilter = $("#documentTypeFilter");
    const $documentSort = $("#documentSort");
    const $documentVisibleCount = $("#documentVisibleCount");
    const $documentCount = $("#documentCount");
    const $categoryCount = $("#categoryCount");
    const $overviewChunkCount = $("#overviewChunkCount");
    const $evaluationQuestionCount = $("#evaluationQuestionCount");
    const $evaluationDatasetSummary = $("#evaluationDatasetSummary");
    const $evaluationQuestionList = $("#evaluationQuestionList");
    const $evaluationCategoryFilter = $("#evaluationCategoryFilter");
    const $evaluationStatusFilter = $("#evaluationStatusFilter");
    const $experimentDatasetCount = $("#experimentDatasetCount");
    const $experimentRunCount = $("#experimentRunCount");
    const $experimentRunCountNote = $("#experimentRunCountNote");
    const $evaluatorCount = $("#evaluatorCount");
    const $overviewEvaluatorCount = $("#overviewEvaluatorCount");
    const $experimentHumanReviewCount = $("#experimentHumanReviewCount");
    const $evaluatorSummary = $("#evaluatorSummary");
    const $evaluationRunList = $("#evaluationRunList");
    const $evaluationResultDetail = $("#evaluationResultDetail");
    const $newTestRunToggle = $("#newTestRunToggle");
    const $newTestRunForm = $("#newTestRunForm");
    const $closeNewTestRun = $("#closeNewTestRun");
    const $newTestDatasetId = $("#newTestDatasetId");
    const $newTestName = $("#newTestName");
    const $newTestLimit = $("#newTestLimit");
    const $newTestModel = $("#newTestModel");
    const $newTestRetrieval = $("#newTestRetrieval");
    const $newTestTopK = $("#newTestTopK");
    const $newTestTemperature = $("#newTestTemperature");
    const $newTestTopP = $("#newTestTopP");
    const $previewNewTestRun = $("#previewNewTestRun");
    const $createNewTestRun = $("#createNewTestRun");
    const $newTestRunStatus = $("#newTestRunStatus");
    const $findingBaselineCount = $("#findingBaselineCount");
    const $findingAdvancedCount = $("#findingAdvancedCount");
    const $findingHumanCount = $("#findingHumanCount");
    const $findingRules = $("#findingRules");
    const $findingMatchedComparisons = $("#findingMatchedComparisons");
    const $findingRunComparison = $("#findingRunComparison");
    const $findingMetricCatalog = $("#findingMetricCatalog");
    const generationEnabled = $askForm.data("generationEnabled") === true;
    let evaluationQuestions = [];
    let evaluationDatasetQuestionCount = 0;
    let evaluatorCatalog = [];
    let currentEvaluationResponseId = null;
    let evaluationResponseContexts = new Map();
    let indexedDocuments = [];
    let pendingDuplicateDocument = null;
    let documentListRequest = null;
    let ingestionStartedAt = null;
    let ingestionTimer = null;

    const $workspaceViews = $("[data-view-panel]");

    function preferredScrollBehavior() {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    }

    function activateWorkspaceView(viewName, updateHistory, focusHeading) {
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
            window.history.pushState({ view: normalizedView }, "", "#" + normalizedView);
        }
        window.scrollTo({ top: 0, behavior: preferredScrollBehavior() });
        if (focusHeading) {
            const $heading = $workspaceViews
                .filter('[data-view-panel="' + normalizedView + '"]')
                .find("h1, h2")
                .first();
            if ($heading.length) {
                $heading.attr("tabindex", "-1").trigger("focus");
            }
        }
    }

    $(document).on("click", 'a[href^="#"]', function (event) {
        const viewName = String($(this).attr("href") || "").slice(1);
        if ($workspaceViews.filter('[data-view-panel="' + viewName + '"]').length) {
            event.preventDefault();
            activateWorkspaceView(viewName, true, true);
        }
    });

    $(window).on("hashchange", function () {
        activateWorkspaceView(window.location.hash.slice(1), false);
    });

    $(window).on("popstate", function () {
        activateWorkspaceView(window.location.hash.slice(1), false);
    });

    function setBusy(isBusy) {
        $questionInput.prop("disabled", isBusy);
        $askButton.prop("disabled", isBusy || !generationEnabled);
        $clearButton.prop("disabled", isBusy);
        $previewSourcesButton.prop("disabled", isBusy);
        $resetChatSettings.prop("disabled", isBusy);
        $chatSettingsControls.prop("disabled", isBusy);
        $suggestionButtons.prop("disabled", isBusy);
    }

    function showLoading(previewOnly) {
        $emptyState.prop("hidden", true);
        $errorState.prop("hidden", true).text("");
        $answerResult.prop("hidden", true);
        $loadingState.prop("hidden", false);
        $loadingText.text(previewOnly
            ? "Retrieving the sources these settings would use..."
            : "Retrieving sources and generating an answer...");
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
            const finalScore = Number(source.retrieval_score);
            const scoreParts = [];
            if (Number.isFinite(distance)) {
                scoreParts.push("distance " + distance.toFixed(6));
            }
            if (source.keyword_score !== null && source.keyword_score !== undefined) {
                scoreParts.push("lexical " + compactNumber(source.keyword_score, 3));
            }
            if (Number.isFinite(finalScore)) {
                scoreParts.push("final " + finalScore.toFixed(6));
            }
            const $card = $("<article>").addClass("source-card");
            const $heading = $("<div>").addClass("source-heading");

            $("<strong>").text(source.rank + ". " + source.source_path).appendTo($heading);
            $("<span>")
                .text("Chunk " + source.chunk_index + " · " + (scoreParts.join(" · ") || "score unavailable"))
                .appendTo($heading);

            $heading.appendTo($card);
            $("<p>").text(source.text).appendTo($card);
            $card.appendTo($sourceList);
        });
    }

    function showAnswer(result, previewOnly) {
        $loadingState.prop("hidden", true);
        $emptyState.prop("hidden", true);
        $errorState.prop("hidden", true).text("");
        $answerResult.prop("hidden", false);

        $answerResultLabel.text(previewOnly ? "Source preview" : "Grounded answer");
        $answerText.text(previewOnly
            ? "No model was called. These are the source chunks the selected retrieval settings would send to the model."
            : (result.answer || "No answer was returned."));
        $answerMeta.empty();
        if (!previewOnly) {
            addMeta("Provider", result.provider || "unknown");
            addMeta("Model", result.model || "unknown");
        }
        addMeta("Retrieval", readable(result.retrieval_method, "unknown"));
        addMeta("Top-k", String(result.top_k ?? "unknown"));
        if (!previewOnly) {
            addMeta("Temperature", String(result.temperature ?? "unknown"));
            addMeta("Top-p", String(result.top_p ?? "unknown"));
            addMeta("Latency", String(result.latency_ms ?? "unknown") + " ms");
        }
        if (result.response_id !== null && result.response_id !== undefined) {
            addMeta("Saved response", "#" + result.response_id);
        }
        if (result.persistence_error) {
            addMeta("Storage warning", result.persistence_error);
        }

        renderSources(result.sources);
    }

    function chatConfiguration() {
        return {
            model: String($chatModel.val()),
            retrieval_method: String($chatRetrievalMethod.val()),
            top_k: Number($chatTopK.val()),
            temperature: Number($chatTemperature.val()),
            top_p: Number($chatTopP.val()),
        };
    }

    function updateChatSettingsSummary() {
        const configuration = chatConfiguration();
        const retrievalLabel = configuration.retrieval_method === "mysql_keyword"
            ? "Keyword search"
            : "Vector search";
        $chatSettingsSummary.text(
            configuration.model + " · " + retrievalLabel + " · " + configuration.top_k + " source chunk" +
            (configuration.top_k === 1 ? "" : "s") + " · temperature " +
            configuration.temperature.toFixed(1) + " · top-p " + configuration.top_p.toFixed(1)
        );
    }

    function requestChat(action) {
        const question = $questionInput.val().trim();

        if (!question) {
            showError("Enter a question before submitting.");
            $questionInput.trigger("focus");
            return;
        }

        const previewOnly = action === "preview";
        const configuration = chatConfiguration();
        showLoading(previewOnly);
        $.ajax({
            url: "api/ask.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({
                question: question,
                action: action,
                model: configuration.model,
                retrieval_method: configuration.retrieval_method,
                top_k: configuration.top_k,
                temperature: configuration.temperature,
                top_p: configuration.top_p,
            }),
        })
            .done(function (response) {
                if (!response || response.ok !== true || !response.data) {
                    showError("The server returned an incomplete answer.");
                    return;
                }
                showAnswer(response.data, previewOnly);
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
    }

    $askForm.on("submit", function (event) {
        event.preventDefault();
        requestChat("answer");
    });

    $previewSourcesButton.on("click", function () {
        requestChat("preview");
    });

    $clearButton.on("click", function () {
        $questionInput.val("").prop("disabled", false).trigger("focus");
        setBusy(false);
        resetAnswer();
    });

    $resetChatSettings.on("click", function () {
        $chatSettingsControls.each(function () {
            $(this).val(String($(this).data("default")));
        });
        updateChatSettingsSummary();
    });

    $chatSettingsControls.on("change", updateChatSettingsSummary);
    updateChatSettingsSummary();

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
        pendingDuplicateDocument = null;
        $cancelReplaceButton.prop("hidden", true);
        $duplicateDocumentPrompt.prop("hidden", true);
        $duplicateDocumentName.text("");
        $uploadDocumentButton.prop("disabled", false);
        $uploadDocumentButton.text("Upload and ingest");
        $uploadSelection.text("");
    }

    function selectReplacement(item) {
        $replaceDocumentId.val(item.document_id);
        pendingDuplicateDocument = null;
        $duplicateDocumentPrompt.prop("hidden", true);
        $duplicateDocumentName.text("");
        $documentTitle.val(item.title);
        $documentCategory.val(item.category);
        $cancelReplaceButton.prop("hidden", false);
        $uploadDocumentButton.prop("disabled", false);
        $uploadDocumentButton.text("Replace and re-ingest");
        showDocumentMessage(
            "The new file will replace " + item.title + " after ingestion succeeds.",
            "info"
        );
    }

    function updateDocumentFilterOptions(documents) {
        const currentCategory = String($documentCategoryFilter.val() || "");
        const categories = [...new Set(documents.map(function (item) { return item.category; }))].sort();
        $documentCategoryFilter.find("option:not(:first)").remove();
        categories.forEach(function (category) {
            $documentCategoryFilter.append(
                $("<option>").val(category).text(readable(category))
            );
        });
        if (categories.includes(currentCategory)) {
            $documentCategoryFilter.val(currentCategory);
        }
    }

    function documentRow(item) {
        const $row = $("<article>").addClass("list-item document-item");
        const $details = $("<div>").addClass("document-details");
        $("<strong>").text(item.title).appendTo($details);
        $("<span>")
            .text(item.original_filename + " · " + item.chunk_count + " chunks")
            .appendTo($details);
        if (item.ingestion_error) {
            $("<span>").addClass("text-danger").text(item.ingestion_error).appendTo($details);
        }
        $details.appendTo($row);

        const isUploaded = String(item.source_path).startsWith("storage/uploads/");
        const $actions = $("<div>").addClass("document-actions");
        $("<small>").text(
            String(item.source_type).toUpperCase() + " · " + item.status + " · " +
            (isUploaded ? "uploaded" : "bundled source")
        ).appendTo($actions);
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
        $actions.appendTo($row);
        return $row;
    }

    function renderDocumentList() {
        $documentList.empty();
        const documentItems = indexedDocuments;
        const categories = new Set(documentItems.map(function (item) {
            return item.category;
        }));
        $documentCount.text(String(documentItems.length));
        $categoryCount.text(String(categories.size));
        $overviewChunkCount.text(String(documentItems.reduce(function (total, item) {
            return total + (Number(item.chunk_count) || 0);
        }, 0)));
        if (documentItems.length === 0) {
            $documentVisibleCount.text("0 indexed documents");
            $("<p>").addClass("text-muted").text("No indexed documents were found.").appendTo($documentList);
            return;
        }

        const query = String($documentSearch.val() || "").trim().toLowerCase();
        const category = String($documentCategoryFilter.val() || "");
        const type = String($documentTypeFilter.val() || "");
        const sort = String($documentSort.val() || "category");
        const visible = documentItems.filter(function (item) {
            const haystack = (item.title + " " + item.original_filename).toLowerCase();
            return (!query || haystack.includes(query)) &&
                (!category || item.category === category) &&
                (!type || item.source_type === type);
        });
        const comparators = {
            category: function (left, right) {
                return String(left.category).localeCompare(String(right.category)) ||
                    String(left.title).localeCompare(String(right.title));
            },
            name: function (left, right) { return String(left.title).localeCompare(String(right.title)); },
            newest: function (left, right) { return Number(right.document_id) - Number(left.document_id); },
            chunks: function (left, right) { return Number(right.chunk_count) - Number(left.chunk_count); },
        };
        visible.sort(comparators[sort] || comparators.category);
        $documentVisibleCount.text(
            visible.length + " of " + documentItems.length + " indexed document" +
            (documentItems.length === 1 ? "" : "s")
        );
        if (!visible.length) {
            $("<p>").addClass("text-muted").text("No documents match these filters.").appendTo($documentList);
            return;
        }

        if (sort === "category") {
            const grouped = new Map();
            visible.forEach(function (item) {
                if (!grouped.has(item.category)) {
                    grouped.set(item.category, []);
                }
                grouped.get(item.category).push(item);
            });
            grouped.forEach(function (items, groupName) {
                const $group = $("<section>").addClass("document-group");
                $group.append($("<div>").addClass("document-group-heading").append(
                    $("<strong>").text(readable(groupName)),
                    $("<span>").text(items.length + " document" + (items.length === 1 ? "" : "s"))
                ));
                const $stack = $("<div>").addClass("list-stack");
                items.forEach(function (item) { $stack.append(documentRow(item)); });
                $group.append($stack);
                $documentList.append($group);
            });
            return;
        }

        const $stack = $("<div>").addClass("list-stack");
        visible.forEach(function (item) { $stack.append(documentRow(item)); });
        $documentList.append($stack);
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
                indexedDocuments = Array.isArray(response.data) ? response.data : [];
                updateDocumentFilterOptions(indexedDocuments);
                renderDocumentList();
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
            pendingDuplicateDocument = null;
            $duplicateDocumentPrompt.prop("hidden", true);
            if (!$replaceDocumentId.val()) {
                $uploadDocumentButton.prop("disabled", false);
            }
            return;
        }
        $uploadSelection.text(file.name + " · " + Math.ceil(file.size / 1024) + " KB");
        if (!$documentTitle.val().trim()) {
            $documentTitle.val(file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
        }
        const duplicate = indexedDocuments.find(function (item) {
            return String(item.original_filename).toLowerCase() === file.name.toLowerCase();
        });
        if (duplicate && !$replaceDocumentId.val()) {
            pendingDuplicateDocument = duplicate;
            $duplicateDocumentName.text(
                "A document named " + file.name + " already exists (" + duplicate.chunk_count + " chunks)."
            );
            $duplicateDocumentPrompt.prop("hidden", false);
            $uploadDocumentButton.prop("disabled", true);
            $documentMessage.prop("hidden", true).text("");
        } else {
            pendingDuplicateDocument = null;
            $duplicateDocumentPrompt.prop("hidden", true);
            $duplicateDocumentName.text("");
            $uploadDocumentButton.prop("disabled", false);
        }
    });

    $confirmDuplicateReplacement.on("click", function () {
        if (!pendingDuplicateDocument) {
            return;
        }
        selectReplacement(pendingDuplicateDocument);
    });

    $cancelDuplicateUpload.on("click", function () {
        $documentFile.val("");
        resetReplacement();
        $documentForm[0].reset();
        showDocumentMessage("Duplicate upload cancelled. The existing indexed document was not changed.", "info");
        $documentFile.trigger("focus");
    });

    $documentList.on("click", ".replace-document-button", function () {
        const item = $(this).data("document");
        selectReplacement(item);
        $documentFile.trigger("focus");
    });

    $documentList.on("click", ".delete-document-button", function () {
        const $button = $(this);
        const item = $button.data("document");
        const isUploaded = String(item.source_path).startsWith("storage/uploads/");
        const detail = isUploaded
            ? "Its uploaded file, live chunks, and embeddings will be removed."
            : "Its live chunks and embeddings will be removed; the bundled seed file will remain available for restoration.";
        if (!window.confirm("Delete " + item.title + " from the active index?\n\n" + detail)) {
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
                resetAnswer();
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

    $documentSearch.on("input", renderDocumentList);
    $documentCategoryFilter.add($documentTypeFilter).add($documentSort).on("change", renderDocumentList);

    $deleteAllDocumentsButton.on("click", function () {
        if (!indexedDocuments.length) {
            showDocumentMessage("The active document index is already empty.", "info");
            return;
        }
        const confirmation = window.prompt(
            "This removes every document, live chunk, and embedding from the active index. " +
            "Bundled source files remain available for restoration. Type DELETE ALL to continue."
        );
        if (confirmation !== "DELETE ALL") {
            return;
        }
        $deleteAllDocumentsButton.prop("disabled", true).text("Deleting all…");
        showDocumentMessage("Clearing all documents, chunks, and embeddings from the active index…", "info");
        $.ajax({
            url: "api/documents.php",
            method: "DELETE",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify({ action: "delete_all", confirmation: confirmation }),
        })
            .done(function (response) {
                showDocumentMessage((response.data?.deleted_count || 0) + " documents removed from the active index.", "success");
                resetAnswer();
                loadDocuments();
            })
            .fail(function (xhr) {
                showDocumentMessage(xhr.responseJSON?.error || "The active index could not be cleared.", "danger");
            })
            .always(function () {
                $deleteAllDocumentsButton.prop("disabled", false).text("Delete all");
            });
    });

    $documentForm.on("submit", function (event) {
        event.preventDefault();
        if (pendingDuplicateDocument) {
            showDocumentMessage("Choose Replace existing or Cancel upload before continuing.", "info");
            $confirmDuplicateReplacement.trigger("focus");
            return;
        }
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
                const replacementText = Number(response.data.replaced_document_count)
                    ? " Previous same-name index record replaced."
                    : "";
                showDocumentMessage(
                    "Document ingested with " + response.data.chunk_count + " chunks." + replacementText,
                    "success"
                );
                resetAnswer();
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

    function evaluatorMethodKey(evaluator) {
        if (Number(evaluator.is_local) === 1) {
            return "local";
        }
        if (evaluator.evaluator_key === "llm_judge") {
            return "judge";
        }
        if (String(evaluator.evaluator_key || "").startsWith("ragas_")) {
            return "ragas";
        }
        return "model";
    }

    function evaluatorMethodLabel(evaluator) {
        return {
            local: "Local metric",
            judge: "LLM judge",
            ragas: "RAGAS",
            model: "Model-backed metric",
        }[evaluatorMethodKey(evaluator)];
    }

    function requiresGoldStandard(evaluator) {
        return !["ragas_faithfulness", "ragas_response_relevancy"].includes(
            String(evaluator.evaluator_key || "")
        );
    }

    function methodStatusCounts(results) {
        return {
            completed: results.filter(function (result) { return result.status === "completed"; }).length,
            failed: results.filter(function (result) { return result.status === "failed"; }).length,
            skipped: results.filter(function (result) { return result.status === "skipped"; }).length,
        };
    }

    function methodStatusDetails(counts, total, recorded) {
        const details = [];
        if (counts.failed) {
            details.push(counts.failed + " failed");
        }
        if (counts.skipped) {
            details.push(counts.skipped + " skipped");
        }
        const notRun = Math.max(0, total - recorded);
        if (notRun) {
            details.push(notRun + " not run");
        }
        return details.length ? details.join(" · ") : "No failures, skips, or missing methods";
    }

    function renderEvaluationMethodSummary(data) {
        const results = data.results || [];
        const reviews = data.human_reviews || [];
        const definitions = [
            { key: "local", label: "Local metrics" },
            { key: "judge", label: "LLM judge" },
            { key: "ragas", label: "RAGAS" },
        ];
        const $section = $("<section>").addClass("response-method-section");
        $section.append($("<div>").addClass("subsection-heading").append(
            $("<span>").text("How this answer was evaluated"),
            $("<strong>").text("Completed, failed, and missing checks are kept separate")
        ));
        const $summary = $("<div>").addClass("response-method-summary");
        definitions.forEach(function (definition) {
            const methodResults = results.filter(function (result) {
                return evaluatorMethodKey(result) === definition.key;
            });
            const total = evaluatorCatalog.filter(function (evaluator) {
                return evaluatorMethodKey(evaluator) === definition.key;
            }).length;
            const counts = methodStatusCounts(methodResults);
            let headline = counts.completed + " of " + total + " completed";
            if (definition.key === "judge" && total === 1) {
                headline = counts.completed ? "Completed" : counts.failed ? "Failed" : counts.skipped ? "Skipped" : "Not run";
            }
            $summary.append($("<article>").addClass("method-summary method-summary-" + definition.key).append(
                $("<span>").text(definition.label),
                $("<strong>").text(headline),
                $("<small>").text(methodStatusDetails(counts, total, methodResults.length))
            ));
        });
        $summary.append($("<article>").addClass("method-summary method-summary-human").append(
            $("<span>").text("Human review"),
            $("<strong>").text(reviews.length ? "Reviewed" : "Not reviewed"),
            $("<small>").text(reviews.length
                ? reviews.length + " current rubric decision" + (reviews.length === 1 ? "" : "s") + "; supporting evidence, not an automatic metric"
                : "Supporting evidence, not an automatic metric")
        ));
        $section.append($summary);
        $evaluationResultDetail.append($section);
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

        $findingMatchedComparisons.empty();
        (findings.matched_comparisons || []).forEach(function (comparison) {
            const delta = Number(comparison.mean_delta);
            const $card = $("<article>").addClass("matched-comparison-card");
            $card.append($("<span>").text(
                "Run " + comparison.comparison_run_id + " vs " + comparison.baseline_run_id
            ));
            $card.append($("<strong>").text(comparison.display_name));
            $card.append($("<b>").text(
                (delta >= 0 ? "+" : "") + compactNumber(delta) + " mean delta"
            ));
            $card.append($("<p>").text(
                comparison.paired_question_count + " matched question" +
                (Number(comparison.paired_question_count) === 1 ? "" : "s") +
                " · baseline " + compactNumber(comparison.baseline_mean) +
                " · comparison " + compactNumber(comparison.comparison_mean)
            ));
            $findingMatchedComparisons.append($card);
        });
        if (!$findingMatchedComparisons.children().length) {
            $findingMatchedComparisons.append($("<div>").addClass("matched-comparison-empty").append(
                $("<strong>").text("No valid paired comparison exists yet."),
                $("<p>").text("No completed baseline pair currently shares scored question/evaluator rows. Scores remain run-scoped descriptive evidence, so no improvement claim is calculated.")
            ));
        }

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
                ["Test purpose", run.experiment_key || "not labeled"],
                ["Corpus", run.corpus_variant_key || "full corpus"],
                ["Completed checks", (run.completed_result_count || 0) + " completed"],
                ["Stored status rows", (run.result_count || 0) + " total"],
                ["Evaluator attempts", (run.evaluator_attempt_count || 0) + " retained"],
                ["Skipped / failed", (run.evaluator_skipped_count || 0) + " / " + (run.evaluator_error_count || 0)],
                ["Evaluator runtime", compactNumber((Number(run.evaluator_runtime_ms) || 0) / 1000, 2) + " s"],
                ["Generation cost", Number(run.generation_unpriced_count)
                    ? "Unknown for " + run.generation_unpriced_count + " response(s)"
                    : "$" + compactNumber(run.answer_estimated_cost || 0, 6)],
                ["Provider evaluator cost", Number(run.evaluator_unpriced_count)
                    ? "Unknown for " + run.evaluator_unpriced_count + " attempt(s)"
                    : run.evaluator_priced_count
                        ? "$" + compactNumber(run.evaluator_estimated_cost, 6)
                        : "No provider attempts"],
            ].forEach(function (fact) {
                $facts.append($("<div>").append($("<dt>").text(fact[0]), $("<dd>").text(fact[1])));
            });
            $card.append($facts);
            if (configuration.change_from_baseline) {
                $card.append($("<p>").addClass("finding-change-note").text("Changed variable: " + configuration.change_from_baseline));
            }
            const scopedMetrics = (findings.run_metric_summaries || []).filter(function (metric) {
                return Number(metric.run_id) === Number(run.run_id);
            });
            if (scopedMetrics.length) {
                const $scoped = $("<details>").addClass("run-scoped-metrics");
                $scoped.append($("<summary>").text("Run-scoped metric means (" + scopedMetrics.length + ")"));
                const $list = $("<dl>");
                scopedMetrics.forEach(function (metric) {
                    $list.append($("<div>").append(
                        $("<dt>").text(metric.display_name + " · n=" + metric.question_count),
                        $("<dd>").text(compactNumber(metric.mean_score))
                    ));
                });
                $scoped.append($list);
                $card.append($scoped);
            }
            $findingRunComparison.append($card);
        });
        if (!$findingRunComparison.children().length) {
            $findingRunComparison.append($("<p>").addClass("text-muted").text("No batch test runs have been saved."));
        }

        $findingMetricCatalog.empty();
        (findings.metric_summaries || []).forEach(function (metric) {
            const config = metric.configuration_json || {};
            const $card = $("<article>").addClass("finding-metric metric-" + (metric.layer || "baseline"));
            $card.append($("<div>").addClass("finding-metric-heading").append(
                $("<span>").text(evaluatorMethodLabel(metric)),
                $("<strong>").text(metric.display_name)
            ));
            $card.append($("<p>").text(config.question || "No score question documented."));
            $card.append($("<small>").addClass("metric-dependency").text(
                requiresGoldStandard(metric)
                    ? "Gold-standard data required · post-answer evaluation"
                    : "No gold answer required · post-answer evaluation"
            ));
            const completed = Number(metric.completed_count) || 0;
            $card.append($("<small>").text(completed
                ? completed + " completed across stored responses · inspect run-scoped or matched evidence above"
                : "Not run yet · no observed scores are being inferred"
            ));
            const costText = Number(metric.is_local)
                ? "local method; no provider cost"
                : Number(metric.unpriced_attempt_count)
                    ? "cost unknown for " + metric.unpriced_attempt_count + " provider attempt(s)"
                : Number(metric.priced_attempt_count)
                    ? "recorded cost $" + compactNumber(metric.estimated_cost, 6)
                    : "no provider cost";
            $card.append($("<small>").addClass("metric-operations").text(
                (metric.attempt_count || 0) + " attempts · mean runtime " +
                compactNumber(metric.mean_runtime_ms || 0, 1) + " ms · " + costText
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
                $newTestDatasetId.val(dataset.dataset_id);
                $evaluationQuestionCount.text(dataset.question_count);
                $experimentDatasetCount.text(dataset.question_count);
                const readyRunCount = (data.runs || []).filter(function (run) {
                    return run.status === "completed";
                }).length;
                const attentionRunCount = Math.max(0, (data.runs || []).length - readyRunCount);
                $experimentRunCount.text(readyRunCount);
                $experimentRunCountNote.text(
                    attentionRunCount
                        ? attentionRunCount + " earlier attempt needs attention"
                        : "completed batches"
                );
                $evaluationDatasetSummary.text(
                    dataset.dataset_name + " " + dataset.version + ": " + dataset.reviewed_count + " of " + dataset.question_count +
                    " reviewed; " + dataset.unanswerable_count + " unanswerable cases across " + dataset.category_count + " categories."
                );
                $evaluatorCount.text(evaluatorCatalog.length);
                $overviewEvaluatorCount.text(evaluatorCatalog.length);
                $experimentHumanReviewCount.text(data.findings?.human_review_count || 0);
                $evaluatorSummary.text(
                    "Start with a completed test below. Scoring can reuse finished results, add missing local checks without an API call, or apply all 13 methods to one exact saved answer after a call preview."
                );
                const categories = [...new Set(evaluationQuestions.map(function (question) { return question.category; }))].sort();
                $evaluationCategoryFilter.find("option:not(:first)").remove();
                categories.forEach(function (value) {
                    $evaluationCategoryFilter.append($("<option>").val(value).text(value.replaceAll("_", " ")));
                });
                renderEvaluationQuestions();
                renderEvaluationRuns(data.runs || [], data.responses || [], data.findings || {});
                renderFindings(data);
            })
            .fail(function () {
                $evaluationDatasetSummary.text("Evaluation data could not be loaded. Verify the local database setup and try again.");
            });
    }

    function savedTestDate(value) {
        if (!value) {
            return "Date unavailable";
        }
        const parsed = new Date(String(value).replace(" ", "T"));
        return Number.isNaN(parsed.getTime())
            ? String(value)
            : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(parsed);
    }

    function runScoringState(run, runResponses) {
        const responseCount = runResponses.length;
        const recorded = runResponses.reduce(function (total, response) {
            return total + (Number(response.result_count) || 0);
        }, 0);
        const localCompleted = runResponses.reduce(function (total, response) {
            return total + (Number(response.local_completed_count) || 0);
        }, 0);
        if (run.status !== "completed") {
            return {
                label: recorded ? "Earlier attempt" : "Needs scoring",
                className: "run-status-attention",
            };
        }
        if (responseCount && recorded >= responseCount * 13) {
            return { label: "All 13 available", className: "run-status-completed" };
        }
        if (responseCount && localCompleted >= responseCount * 8) {
            return { label: "Local 8 available", className: "run-status-local" };
        }
        return { label: "Partially scored", className: "run-status-attention" };
    }

    function renderRunCard(run, responses, findings) {
        const runResponses = responses.filter(function (response) {
            return String(response.run_id) === String(run.run_id);
        });
        const responseCount = runResponses.length;
        const recordedCount = runResponses.reduce(function (total, response) {
            return total + (Number(response.result_count) || 0);
        }, 0);
        const completedCount = runResponses.reduce(function (total, response) {
            return total + (Number(response.completed_result_count) || 0);
        }, 0);
        const expectedSlots = responseCount * evaluatorCatalog.length;
        const state = runScoringState(run, runResponses);
        const $run = $("<article>").addClass("evaluation-run").attr("data-run-id", run.run_id);
        const $runHeading = $("<div>").addClass("evaluation-run-heading");
        $runHeading.append($("<strong>").text("Saved " + savedTestDate(run.completed_at || run.started_at)));
        $runHeading.append($("<span>").addClass("run-status " + state.className).text(state.label));
        $run.append($runHeading);
        $run.append($("<h3>").text(run.run_name));
        $run.append($("<span>").addClass("evaluation-run-meta").text(
            responseCount + " saved answer" + (responseCount === 1 ? "" : "s") + " · " +
            recordedCount + " of " + expectedSlots + " method results saved"
        ));
        $run.append($("<p>").addClass("evaluation-run-scope").text(
            "Saved scope: " + responseCount + " answer" + (responseCount === 1 ? "" : "s") +
            (evaluationDatasetQuestionCount ? " from the " + evaluationDatasetQuestionCount + "-question Gold Standard." : ".")
        ));

        const skipped = Number(run.evaluator_skipped_count) || 0;
        const failed = Number(run.evaluator_error_count) || 0;
        if (skipped || failed) {
            $run.append($("<p>").addClass("evaluation-run-note").text(
                completedCount + " completed · " + skipped + " skipped · " + failed +
                " failed. Missing, skipped, and failed methods are not treated as zero scores."
            ));
        }
        if (run.status !== "completed") {
            $run.append($("<p>").addClass("evaluation-run-warning").text(
                responseCount
                    ? "The original test stopped early, but its saved answer is still available. Use Score saved answers to add the missing checks."
                    : "The original test stopped before it saved an answer. It is preserved only as technical history."
            ));
        }

        const $settings = $("<details>").addClass("run-settings");
        $settings.append($("<summary>").text("Settings and technical record"));
        $settings.append($("<p>").text(
            readable(run.retrieval_method, "unknown") + " retrieval · " +
            readable(run.chat_model, "unknown model") + " · top-k " + readable(run.top_k, "unknown") +
            " · temperature " + readable(run.temperature, "unknown") +
            " · top-p " + readable(run.top_p, "unknown") + " · internal run ID " + run.run_id
        ));
        $run.append($settings);

        const $evaluateActions = $("<div>").addClass("run-evaluation-actions");
        const $evaluateToggle = $("<button>")
            .attr("type", "button")
            .addClass("btn btn-sm btn-primary evaluate-run-toggle")
            .prop("disabled", !responseCount)
            .text("Score saved answers");
        const $evaluatePanel = $("<div>")
            .addClass("run-evaluation-panel")
            .prop("hidden", true)
            .data({ runId: run.run_id, responseCount: responseCount });
        $evaluatePanel.append($("<p>").addClass("run-evaluation-explainer").text(
            "This applies scoring methods to the saved text above. It will not ask the LLM to generate another answer."
        ));
        const $scopeLabel = $("<label>").addClass("run-evaluation-field").append(
            $("<span>").text("What should be scored?")
        );
        const $scope = $("<select>")
            .addClass("form-select form-select-sm run-evaluation-scope")
            .attr("aria-label", "Scoring scope")
            .append(
                $("<option>").val("local8").text("Local 8 · every saved answer · no API calls"),
                $("<option>").val("all13").text("All 13 · one selected answer · may use API quota")
            );
        $scopeLabel.append($scope);
        const $targetSelect = $("<select>")
            .addClass("form-select form-select-sm run-evaluation-target-select")
            .attr("aria-label", "Saved answer to score");
        runResponses.forEach(function (response, index) {
            const questionNumber = Number(response.run_question_number) || index + 1;
            $targetSelect.append(
                $("<option>").val(response.response_id).text(
                    "Question " + questionNumber + ": " + response.question_text
                )
            );
        });
        const $targetLabel = $("<label>")
            .addClass("run-evaluation-field run-evaluation-target")
            .prop("hidden", true)
            .append($("<span>").text("Which saved answer?"), $targetSelect);
        const $advancedOptions = $("<details>").addClass("run-evaluation-advanced");
        $advancedOptions.append($("<summary>").text("Advanced option"));
        $advancedOptions.append($("<label>").addClass("run-evaluation-force").append(
            $("<input>").attr("type", "checkbox").addClass("form-check-input run-evaluation-force-input"),
            $("<span>").text("Replace scores that already completed")
        ));
        const $preview = $("<button>")
            .attr("type", "button")
            .addClass("btn btn-sm btn-outline-primary preflight-run-evaluation")
            .text("Check what will run");
        const $execute = $("<button>")
            .attr("type", "button")
            .addClass("btn btn-sm btn-primary execute-run-evaluation")
            .prop("hidden", true)
            .text("Apply scores");
        const $status = $("<p>").addClass("run-evaluation-status").attr({ role: "status", "aria-live": "polite" }).text(
            "Start with the local eight. Completed scores will be reused unless the advanced replacement option is selected."
        );
        $evaluatePanel.append(
            $scopeLabel,
            $targetLabel,
            $advancedOptions,
            $("<div>").addClass("run-evaluation-buttons").append($preview, $execute),
            $status
        );
        $evaluateActions.append($evaluateToggle, $evaluatePanel);
        $run.append($evaluateActions);

        const $questionHeading = $("<div>").addClass("run-question-heading").append(
            $("<strong>").text("Answered questions"),
            $("<small>").text("Open inspects evidence · Evaluate prepares all 13 methods for that answer")
        );
        $run.append($questionHeading);
        const $buttons = $("<div>").addClass("evaluation-response-buttons");
        runResponses.forEach(function (response, index) {
            const questionNumber = Number(response.run_question_number) || index + 1;
            const completed = Number(response.completed_result_count) || 0;
            const failedResults = Number(response.failed_result_count) || 0;
            const skippedResults = Number(response.skipped_result_count) || 0;
            const notRun = Math.max(0, evaluatorCatalog.length - (Number(response.result_count) || 0));
            const statusParts = [completed + " completed"];
            if (failedResults) {
                statusParts.push(failedResults + " failed");
            }
            if (skippedResults) {
                statusParts.push(skippedResults + " skipped");
            }
            if (notRun) {
                statusParts.push(notRun + " not run");
            }
            evaluationResponseContexts.set(Number(response.response_id), {
                label: "Question " + questionNumber + " of " + responseCount,
                runName: run.run_name,
                runId: Number(run.run_id),
            });
            const $responseRow = $("<div>").addClass("evaluation-response-row");
            $responseRow.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-sm btn-outline-primary evaluation-response-button")
                    .data({ responseId: response.response_id, runId: run.run_id })
                    .append(
                        $("<span>").addClass("evaluation-question-number").text("Question " + questionNumber + " of " + responseCount),
                        $("<strong>").text(response.question_text),
                        $("<small>").text(statusParts.join(" · "))
                    )
            );
            $responseRow.append(
                $("<button>")
                    .attr({
                        type: "button",
                        title: "Check and apply all 13 evaluation methods to this saved answer",
                    })
                    .addClass("btn btn-sm btn-primary evaluate-response-button")
                    .data({ responseId: response.response_id, runId: run.run_id })
                    .text("Evaluate")
            );
            $buttons.append($responseRow);
        });
        if (!runResponses.length) {
            $buttons.append($("<p>").addClass("text-muted mb-0").text("No saved answers are available for this test."));
        }
        $run.append($buttons);

        const scopedMetrics = (findings.run_metric_summaries || []).filter(function (metric) {
            return Number(metric.run_id) === Number(run.run_id);
        });
        const globalMetrics = findings.metric_summaries || [];
        const $metricComparison = $("<details>").addClass("run-metric-comparison");
        $metricComparison.append($("<summary>").text("Metric averages for this test and all tests"));
        const $metricTable = $("<div>").addClass("run-metric-table");
        $metricTable.append($("<div>").addClass("run-metric-row run-metric-header").append(
            $("<strong>").text("Method"),
            $("<strong>").text("This test"),
            $("<strong>").text("All tests")
        ));
        evaluatorCatalog.forEach(function (evaluator) {
            const current = scopedMetrics.find(function (metric) {
                return metric.evaluator_key === evaluator.evaluator_key;
            });
            const overall = globalMetrics.find(function (metric) {
                return metric.evaluator_key === evaluator.evaluator_key;
            });
            $metricTable.append($("<div>").addClass("run-metric-row").append(
                $("<span>").append(
                    $("<b>").text(evaluator.display_name),
                    $("<small>").text(
                        evaluatorMethodLabel(evaluator) + " · " +
                        (requiresGoldStandard(evaluator) ? "needs gold standard" : "no gold answer required")
                    )
                ),
                $("<span>").text(current
                    ? compactNumber(current.mean_score) + " · n=" + current.question_count
                    : "Not completed"),
                $("<span>").text(overall && overall.mean_score !== null
                    ? compactNumber(overall.mean_score) + " · n=" + overall.completed_count
                    : "Not completed")
            ));
        });
        $metricComparison.append($metricTable);
        $run.append($metricComparison);
        return $run;
    }

    function renderEvaluationRuns(runs, responses, findings) {
        $evaluationRunList.empty();
        evaluationResponseContexts = new Map();
        if (!runs.length) {
            $evaluationRunList.append($("<p>").addClass("text-muted").text("No saved tests are available yet."));
            return;
        }
        const readyRuns = runs.filter(function (run) { return run.status === "completed"; });
        const attentionRuns = runs.filter(function (run) { return run.status !== "completed"; });
        readyRuns.forEach(function (run) {
            $evaluationRunList.append(renderRunCard(run, responses, findings));
        });
        if (attentionRuns.length) {
            const $history = $("<details>").addClass("run-attention-history");
            $history.append($("<summary>").text(
                "Earlier attempts needing attention (" + attentionRuns.length + ")"
            ));
            $history.append($("<p>").text(
                "These records are kept for research history. A saved answer can still be inspected or scored; an attempt with no answer cannot be recovered."
            ));
            const $historyRuns = $("<div>").addClass("run-attention-list");
            attentionRuns.forEach(function (run) {
                $historyRuns.append(renderRunCard(run, responses, findings));
            });
            $history.append($historyRuns);
            $evaluationRunList.append($history);
        }
        let $responseToOpen = $evaluationRunList.find(".evaluation-response-button").first();
        if (currentEvaluationResponseId) {
            const $current = $evaluationRunList.find(".evaluation-response-button").filter(function () {
                return Number($(this).data("responseId")) === currentEvaluationResponseId;
            }).first();
            if ($current.length) {
                $responseToOpen = $current;
                $current.closest(".run-attention-history").prop("open", true);
            }
        }
        if ($responseToOpen.length) {
            loadEvaluationResponse($responseToOpen, false);
        }
    }

    function newTestRunPayload(action) {
        return {
            action: action,
            dataset_id: Number($newTestDatasetId.val()),
            name: String($newTestName.val() || "").trim(),
            limit: Number($newTestLimit.val()),
            model: String($newTestModel.val() || ""),
            retrieval_method: String($newTestRetrieval.val() || ""),
            top_k: Number($newTestTopK.val()),
            temperature: Number($newTestTemperature.val()),
            top_p: Number($newTestTopP.val()),
        };
    }

    function resetNewTestRunPreview(message) {
        $createNewTestRun.prop("hidden", true).removeData("preflight");
        $newTestRunStatus.text(message || "Settings changed. Preview the test again before generating answers.");
    }

    $newTestRunToggle.on("click", function () {
        const willOpen = $newTestRunForm.prop("hidden");
        $newTestRunForm.prop("hidden", !willOpen);
        if (willOpen) {
            if (!$newTestName.val().trim()) {
                $newTestName.val(
                    "Test " + new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date()) +
                    " · " + readable($newTestRetrieval.val()) + " · top-k " + $newTestTopK.val()
                );
            }
            $newTestName.trigger("focus");
        }
    });

    $closeNewTestRun.on("click", function () {
        $newTestRunForm.prop("hidden", true);
        $newTestRunToggle.trigger("focus");
    });

    $newTestRunForm.find("input, select").on("change input", function () {
        resetNewTestRunPreview();
    });

    $newTestRunForm.on("submit", function (event) {
        event.preventDefault();
        $previewNewTestRun.trigger("click");
    });

    $previewNewTestRun.on("click", function () {
        const payload = newTestRunPayload("preflight");
        if (!payload.name || !payload.dataset_id) {
            $newTestRunStatus.text("Give the test a name and wait for the Gold Standard to finish loading.");
            return;
        }
        $previewNewTestRun.prop("disabled", true).text("Checking…");
        resetNewTestRunPreview("Checking model calls and estimated cost…");
        $.ajax({
            url: "api/test_runs.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify(payload),
        })
            .done(function (response) {
                const plan = response.data?.preflight;
                if (!plan) {
                    $newTestRunStatus.text("The server returned an incomplete test preview.");
                    return;
                }
                const estimated = plan.estimated_cost === null
                    ? "cost unavailable"
                    : "$" + compactNumber(plan.estimated_cost, 6) + " estimated";
                $newTestRunStatus.text(
                    plan.response_count + " model call" + (Number(plan.response_count) === 1 ? "" : "s") +
                    " · " + plan.response_count + " new saved answer" + (Number(plan.response_count) === 1 ? "" : "s") +
                    " · local 8 scored automatically · " + estimated
                );
                $createNewTestRun.prop("hidden", false).data("preflight", plan);
            })
            .fail(function (xhr) {
                $newTestRunStatus.text(xhr.responseJSON?.error || "The test preview could not be completed.");
            })
            .always(function () {
                $previewNewTestRun.prop("disabled", false).text("Preview test");
            });
    });

    $createNewTestRun.on("click", function () {
        const plan = $createNewTestRun.data("preflight") || {};
        if (Number(plan.paid_call_count) > 0 && !window.confirm(
            "Generate " + plan.response_count + " new answer" + (Number(plan.response_count) === 1 ? "" : "s") +
            " using " + plan.paid_call_count + " configured model call" +
            (Number(plan.paid_call_count) === 1 ? "" : "s") + "?"
        )) {
            return;
        }
        const payload = newTestRunPayload("create");
        $createNewTestRun.prop("disabled", true).text("Generating…");
        $previewNewTestRun.prop("disabled", true);
        $newTestRunStatus.text("Generating and saving the test answers, then applying the local eight scores…");
        $.ajax({
            url: "api/test_runs.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            timeout: 310000,
            data: JSON.stringify(payload),
        })
            .done(function (response) {
                const answerCount = response.data?.responses?.length || 0;
                $newTestRunStatus.text(
                    "Test saved with " + answerCount + " answer" + (answerCount === 1 ? "" : "s") +
                    " and the local eight scores. It is now available below."
                );
                $createNewTestRun.prop("hidden", true).removeData("preflight");
                loadEvaluationDataset();
            })
            .fail(function (xhr) {
                $newTestRunStatus.text(xhr.responseJSON?.error || "The test run could not be completed.");
                $createNewTestRun.prop("hidden", false);
            })
            .always(function () {
                $createNewTestRun.prop("disabled", false).text("Generate test");
                $previewNewTestRun.prop("disabled", false);
            });
    });

    function runEvaluationPayload($panel, action) {
        const includeAdvanced = $panel.find(".run-evaluation-scope").val() === "all13";
        const payload = {
            action: action,
            run_id: Number($panel.data("runId")),
            include_advanced: includeAdvanced,
            limit: includeAdvanced ? 1 : Math.max(1, Number($panel.data("responseCount")) || 1),
            force: $panel.find(".run-evaluation-force-input").is(":checked"),
        };
        if (includeAdvanced) {
            payload.response_id = Number($panel.find(".run-evaluation-target-select").val());
        }
        return payload;
    }

    $evaluationRunList.on("click", ".evaluate-run-toggle", function () {
        const $panel = $(this).siblings(".run-evaluation-panel");
        const willOpen = $panel.prop("hidden");
        $panel.prop("hidden", !willOpen);
        $(this).text(willOpen ? "Close scoring" : "Score saved answers");
    });

    $evaluationRunList.on("click", ".evaluate-response-button", function () {
        const $button = $(this);
        const $run = $button.closest(".evaluation-run");
        const $panel = $run.find(".run-evaluation-panel");
        $panel.prop("hidden", false);
        $run.find(".evaluate-run-toggle").text("Close scoring");
        $panel.find(".run-evaluation-scope").val("all13");
        $panel.find(".run-evaluation-target-select").val(String($button.data("responseId")));
        $panel.find(".run-evaluation-scope").trigger("change");
        $panel.find(".preflight-run-evaluation").trigger("click");
        $panel[0].scrollIntoView({ behavior: preferredScrollBehavior(), block: "nearest" });
    });

    $evaluationRunList.on("change", ".run-evaluation-scope, .run-evaluation-target-select, .run-evaluation-force-input", function () {
        const $panel = $(this).closest(".run-evaluation-panel");
        const includeAdvanced = $panel.find(".run-evaluation-scope").val() === "all13";
        $panel.find(".run-evaluation-target").prop("hidden", !includeAdvanced);
        $panel.find(".execute-run-evaluation").prop("hidden", true).removeData("preflight");
        $panel.find(".run-evaluation-status").text(
            includeAdvanced
                ? "All 13 methods will target the exact saved answer selected above. Check the plan before applying scores."
                : "The local eight will be applied to every saved answer without an external evaluator call. Check the plan first."
        );
    });

    $evaluationRunList.on("click", ".preflight-run-evaluation", function () {
        const $button = $(this);
        const $panel = $button.closest(".run-evaluation-panel");
        const $status = $panel.find(".run-evaluation-status");
        $button.prop("disabled", true).text("Checking…");
        $panel.find(".execute-run-evaluation").prop("hidden", true);
        $.ajax({
            url: "api/run_evaluation.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify(runEvaluationPayload($panel, "preflight")),
        })
            .done(function (response) {
                const plan = response.data?.preflight;
                if (!plan) {
                    $status.text("The server returned an incomplete preflight.");
                    return;
                }
                const estimated = plan.estimated_cost === null
                    ? "cost unknown"
                    : "$" + compactNumber(plan.estimated_cost, 6) + " estimated";
                $status.text(
                    plan.responses + " saved answer" + (Number(plan.responses) === 1 ? "" : "s") +
                    " selected · " + plan.requested_metric_count + " methods each · " +
                    plan.application_count + " missing scores to add · " + plan.reused_count +
                    " completed scores reused · " + plan.paid_application_count +
                    " external calls · " + estimated
                );
                $panel.find(".execute-run-evaluation").prop("hidden", false).data("preflight", plan);
            })
            .fail(function (xhr) {
                $status.text(xhr.responseJSON?.error || "The evaluation preflight failed.");
            })
            .always(function () {
                $button.prop("disabled", false).text("Check what will run");
            });
    });

    $evaluationRunList.on("click", ".execute-run-evaluation", function () {
        const $button = $(this);
        const $panel = $button.closest(".run-evaluation-panel");
        const plan = $button.data("preflight") || {};
        if (Number(plan.paid_application_count) > 0 && !window.confirm(
            "This will make " + plan.paid_application_count +
            " external evaluator calls using the configured API quota. Continue?"
        )) {
            return;
        }
        const $status = $panel.find(".run-evaluation-status");
        $button.prop("disabled", true).text("Applying…");
        $panel.find(".preflight-run-evaluation").prop("disabled", true);
        $status.text("Applying the selected scoring methods. Keep this page open…");
        $.ajax({
            url: "api/run_evaluation.php",
            method: "POST",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            timeout: 310000,
            data: JSON.stringify(runEvaluationPayload($panel, "evaluate")),
        })
            .done(function () {
                $status.text("Scoring completed. Refreshing the saved results…");
                loadEvaluationDataset();
            })
            .fail(function (xhr) {
                $status.text(xhr.responseJSON?.error || "The selected scoring request failed.");
                $button.prop("disabled", false).text("Apply scores");
                $panel.find(".preflight-run-evaluation").prop("disabled", false);
            });
    });

    function renderScoreCard(result, attempts) {
        const status = result.status || "completed";
        const passed = result.passed === null ? null : Number(result.passed) === 1;
        const cardState = status === "failed" ? "score-failed"
            : status === "skipped" ? "score-skipped"
                : passed === null ? "score-neutral" : passed ? "score-pass" : "score-review";
        const methodKey = evaluatorMethodKey(result);
        const $score = $("<article>").addClass("evaluation-score " + cardState);
        $score.append($("<span>").addClass("metric-origin metric-origin-" + methodKey).text(evaluatorMethodLabel(result)));
        const $scoreHeader = $("<div>").addClass("score-heading");
        $scoreHeader.append($("<strong>").text(result.display_name));
        $score.append($scoreHeader);
        const allRunsCompleted = Number(result.all_runs_completed_count) || 0;
        const hasAllRunsMean = result.all_runs_mean !== null && result.all_runs_mean !== undefined;
        $score.append($("<div>").addClass("score-comparison").append(
            $("<span>").append(
                $("<small>").text("This answer"),
                $("<b>").text(status === "completed" ? compactNumber(result.normalized_score) : readable(status))
            ),
            $("<span>").append(
                $("<small>").text("Completed tests"),
                $("<b>").text(hasAllRunsMean ? compactNumber(result.all_runs_mean) : "—"),
                $("<em>").text(allRunsCompleted ? "average · n=" + allRunsCompleted : "no completed scores")
            )
        ));
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
        const $section = $("<details>").addClass("human-review-section");
        const $heading = $("<summary>").addClass("human-review-heading").append(
            $("<span>").text("Human review · supporting evidence"),
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
        const responseContext = evaluationResponseContexts.get(currentEvaluationResponseId) || {};
        $evaluationResultDetail.empty().prop("hidden", false);
        const $header = $("<div>").addClass("response-detail-header");
        const $headerCopy = $("<div>");
        $headerCopy.append($("<span>").text(responseContext.label || "Saved answer"));
        $headerCopy.append($("<h3>").text(response.question_text));
        $header.append($headerCopy);
        $header.append($("<small>").text(responseContext.runName || response.run_name || "Saved test"));
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
        if (response.top_k !== null && response.top_k !== undefined) {
            $meta.append($("<span>").text("Top-k: " + response.top_k));
        }
        $evaluationResultDetail.append($meta);

        const $provenance = $("<details>").addClass("response-provenance");
        $provenance.append($("<summary>").text("Run settings and technical provenance"));
        const $technicalMeta = $("<div>").addClass("response-meta");
        $technicalMeta.append($("<span>").text("Internal response ID: " + response.response_id));
        $technicalMeta.append($("<span>").text("Internal run ID: " + response.run_id));
        $technicalMeta.append($("<span>").text(
            response.total_tokens === null
                ? "Generation usage not recorded"
                : response.total_tokens + " generation tokens"
        ));
        $technicalMeta.append($("<span>").text(
            response.answer_estimated_cost === null
                ? "Generation cost unavailable"
                : "Generation cost $" + compactNumber(response.answer_estimated_cost, 8)
        ));
        $technicalMeta.append($("<span>").text("Snapshot: " + readable(response.snapshot_provenance)));
        if (response.code_version) {
            $technicalMeta.append($("<span>").text("Code: " + response.code_version));
        }
        if (response.temperature !== null && response.temperature !== undefined) {
            $technicalMeta.append($("<span>").text("Temperature: " + response.temperature));
        }
        if (response.top_p !== null && response.top_p !== undefined) {
            $technicalMeta.append($("<span>").text("Top-p: " + response.top_p));
        }
        if (response.expected_source) {
            $technicalMeta.append($("<span>").text("Expected source: " + response.expected_source));
        }
        $provenance.append($technicalMeta);
        $evaluationResultDetail.append($provenance);

        const results = data.results || [];
        const resultAttempts = data.attempts || [];
        renderEvaluationMethodSummary(data);
        [
            {
                key: "local",
                label: "Local metrics",
                emptyTitle: "No local metric results were saved.",
                emptyText: "Run the local evaluation methods to compare this answer with the reviewed answer and expected source.",
            },
            {
                key: "judge",
                label: "LLM judge",
                emptyTitle: "The LLM judge has not evaluated this answer.",
                emptyText: "This is missing evidence, not a zero score. A guarded provider-backed evaluation can add the rubric result later.",
            },
            {
                key: "ragas",
                label: "RAGAS metrics",
                emptyTitle: "RAGAS has not evaluated this answer.",
                emptyText: "This is missing evidence, not a zero score. A guarded RAGAS run can add faithfulness, relevancy, context precision, and context recall.",
            },
        ].forEach(function (method) {
            const methodResults = results.filter(function (result) { return evaluatorMethodKey(result) === method.key; });
            const catalogMethods = evaluatorCatalog.filter(function (evaluator) { return evaluatorMethodKey(evaluator) === method.key; });
            const counts = methodStatusCounts(methodResults);
            const $section = $("<details>").addClass("score-layer-section");
            $section.append($("<summary>").addClass("score-layer-heading").append(
                $("<span>").text(method.label),
                $("<strong>").text(counts.completed + " of " + catalogMethods.length + " completed · " + counts.failed + " failed · " + counts.skipped + " skipped")
            ));
            if (methodResults.length) {
                const $scores = $("<div>").addClass("evaluation-score-list");
                methodResults.forEach(function (result) {
                    const attempts = resultAttempts.filter(function (attempt) {
                        return attempt.evaluator_key === result.evaluator_key;
                    });
                    $scores.append(renderScoreCard(result, attempts));
                });
                $section.append($scores);
            } else {
                $section.append($("<div>").addClass("layer-empty-state").append(
                    $("<strong>").text(method.emptyTitle),
                    $("<p>").text(method.emptyText)
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

        const $contexts = $("<details>").addClass("retrieved-evidence");
        $contexts.append($("<summary>").text("Retrieved evidence (" + (data.contexts || []).length + ")"));
        (data.contexts || []).forEach(function (context) {
            const $context = $("<article>").toggleClass("expected-evidence", Boolean(context.is_expected_source));
            $context.append($("<strong>").text(
                "Rank " + context.rank_position + ": " + (context.source_path || "unknown source") +
                (context.is_expected_source ? " · expected source" : "")
            ));
            $context.append($("<p>").text(context.context_excerpt));
            const scoreParts = [];
            if (context.semantic_distance !== null) {
                scoreParts.push("semantic distance " + compactNumber(context.semantic_distance, 6));
            }
            if (context.lexical_score !== null) {
                scoreParts.push("lexical " + compactNumber(context.lexical_score, 3));
            }
            if (context.retrieval_score !== null) {
                scoreParts.push("final score " + compactNumber(context.retrieval_score, 6));
            }
            const retrievalVersion = context.retrieval_metadata_json?.version;
            if (retrievalVersion) {
                scoreParts.push("algorithm " + retrievalVersion);
            }
            $context.append($("<small>").text(scoreParts.length ? scoreParts.join(" · ") : "Retrieval score provenance unavailable"));
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
                    $evaluationResultDetail[0].scrollIntoView({ behavior: preferredScrollBehavior(), block: "start" });
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
        const $button = $(this);
        $button.closest(".evaluation-run").find(".run-evaluation-target-select").val($button.data("responseId"));
        loadEvaluationResponse($button, true);
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
