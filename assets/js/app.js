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
});
