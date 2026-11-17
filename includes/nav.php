<header class="app-sidebar" aria-label="Application navigation">
    <a class="app-brand" href="index.php" aria-label="RAG Evaluation home">
        <span class="brand-mark" aria-hidden="true">R</span>
        <span>
            <strong>RAG Observatory</strong>
            <small>Metro State · ICS 499</small>
        </span>
    </a>

    <nav class="side-nav" id="mainNavigation" aria-label="Workspace sections">
        <a class="active" href="#overview" data-view="overview">Overview</a>
        <a href="#ask" data-view="ask">Chat</a>
        <a href="#documents" data-view="documents">Documents</a>
        <a href="#evaluation" data-view="evaluation">Gold Standard</a>
        <a href="#results" data-view="results">Evaluation</a>
    </nav>

    <div class="header-account" aria-label="Current account">
        <span class="header-account-name">
            <span class="header-account-icon" aria-hidden="true">&#9679;</span>
            <strong id="accountDisplayNameLabel"></strong>
        </span>
        <button class="btn btn-sm header-signout"
                id="signOutButton" type="button">Sign out</button>
    </div>
</header>
