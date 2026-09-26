# 22Sep2026 Meeting TODOs

-   Discuss V1.0, understanding the current pipeline and version
    shortcomings
-   Talk about suggested deliverables/new features for V2.0
-   Discuss timeline for project

## Version 2.0 Deliverables

-   **Multimodal RAG:** Extend PDF ingestion so the RAG system can use
    information contained in images/diagrams, tables, and charts, in
    addition to ordinary PDF text.
-   **Conversation Memory:** Extend Chat so that conversation context is
    maintained across turns, allowing follow-up questions to depend on
    earlier questions and answers.

 ## Project Timeline

| Week | Main Focus | Work to Complete | End-of-Week Goal |
|---|---|---|---|
| **1** | **Understand V1** | Run and study existing application; trace PDF ingestion → chunking → Chroma → retrieval → Gemini; trace Chat request flow; understand DB schema; run baseline evaluations; document V1 limitations. | Both team members can explain V1 architecture and have a working baseline. |
| **2** | **Design Version 2** | Design multimodal ingestion architecture; decide how images/diagrams, tables, and charts will be extracted/represented; design conversation/session and message storage; define V2 database changes; create test PDFs and conversational test cases. | Written V2 architecture and implementation plan before coding. |
| **3** | **Multimodal PDF Extraction** | Modify PDF processing to detect/extract visual content; extract images/diagrams; extract table information; identify charts; preserve page/source metadata; experiment with vision/OCR/table tools. | Given a test PDF, system can extract text and useful visual/table/chart information. |
| **4** | **Multimodal Indexing & Retrieval** | Convert extracted multimodal information into RAG-ready representations; chunk/index it; store modality/page metadata; add it to Chroma; retrieve visual/table/chart-derived information from natural-language questions. | Multimodal content is searchable through the RAG pipeline. |
| **5** | **Multimodal End-to-End RAG** | Connect multimodal retrieval to answer generation; display multimodal provenance/evidence; handle PDFs containing mixed text + visuals; test diagrams, tables, and charts; fix ingestion/retrieval issues. | User can upload a PDF and successfully ask questions whose answers require visual/table/chart content. |
| **6** | **Conversation Memory** | Add conversation/session data model; save user and assistant messages; load relevant history; use previous turns when interpreting follow-up questions; preserve source retrieval; add New Conversation/reset behavior. | Chat correctly handles contextual follow-up questions. |
| **7** | **Integrate Both Features** | Make conversation memory work with multimodal retrieval; test follow-up questions about charts/tables/images; handle context switching; prevent old context from incorrectly affecting unrelated questions; regression-test V1 functionality. | Both Version 2 features work together as one system. |
| **8** | **Evaluation & Comparison** | Extend Gold Standard with multimodal questions and multi-turn conversations; establish V1 vs V2 experiments; evaluate retrieval and answer quality; investigate failures; performance/error testing; fix highest-priority defects. | Measurable evidence showing where V2 improves or fails relative to V1. |
| **9** | **Finalization & Presentation** | Feature freeze; final regression testing; clean code; update README/setup docs; architecture diagrams; document limitations; summarize evaluation results; prepare demo and presentation. | Stable, documented Version 2 ready to submit and demonstrate. |