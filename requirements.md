# LLM RAG Evaluations Web Application

## 1. Project Overview

The goal of this project is to build a web-based research application for evaluating Retrieval-Augmented Generation (RAG) approaches using Metrostate documents as the example knowledge base. The application is the experimental instrument; the final contribution includes what the experiments teach about metric usefulness, failure modes, and the effects of document-collection size and composition.

The system will allow users to upload or manage Metrostate-related documents, ask questions against those documents, generate AI-assisted responses using approved LLM providers such as OpenAI/ChatGPT, Gemini, or Claude, and compare different RAG evaluation approaches. The project is intended to help business users, managers, and developers understand which RAG approach or evaluation framework is most useful for informed decision making.

This project will use the following reference repositories:

* Reference Repo 1: https://github.com/sjasthi/ragworks
* Reference Repo 2: https://github.com/sjasthi/student-compass
* Main Project Repo: https://github.com/sjasthi/llm-rag-evals

The project will port or adapt useful ideas from the reference repositories into the required course technology stack.

---

## 2. Technology Stack

The application must use the following technology stack:

### Front End

* HTML
* CSS
* JavaScript
* jQuery
* Bootstrap

### Server

* PHP

### Backend / Database

* MySQL
* ChromaDB for vector storage and retrieval

### AI / LLM Integration

* Approved LLM providers such as OpenAI/ChatGPT, Gemini, or Claude
* Embedding model for document search
* LLM model for answer generation
* Optional LLM-based evaluation for response scoring

---

## 3. Target Users

### 3.1 Business Users / Managers

Business users and managers will use the application to compare different RAG evaluation approaches and make informed decisions about which approach is most useful.

They should be able to:

* View evaluation results
* Compare RAG performance across different settings
* Understand trade-offs between evaluation frameworks
* Review which approach gives better accuracy, relevance, and faithfulness
* Use reports or dashboard results to support decision making

### 3.2 Developers

Developers will use the application as a starting point for building and testing RAG systems in the required technology stack.

They should be able to:

* Understand the application structure
* Review how documents are processed
* See how questions and responses are stored
* Review how evaluation scores are calculated
* Extend the system with additional evaluation methods or model providers

### 3.3 Admin Users

Admin users will manage the document knowledge base and evaluation test data.

They should be able to:

* Upload Metrostate documents
* View uploaded documents
* Delete or replace documents
* Manage test questions
* Manage expected answers
* Run evaluation tests
* View evaluation history

### 3.4 General Users

General users will ask questions against the Metrostate document knowledge base.

They should be able to:

* Enter a question
* Receive an AI-generated answer
* View retrieved source documents or source chunks
* See basic evaluation feedback when available

---

## 4. Main Project Goal

The main goal is to prove and compare different RAG evaluation frameworks using Metrostate documents.

The application should answer questions such as:

* Did the RAG system retrieve the correct Metrostate document sections?
* Did the generated answer correctly answer the user’s question?
* Was the answer faithful to the retrieved context?
* Did the answer include unsupported or hallucinated information?
* Which evaluation method gives the most useful results for a specific business, development, or research purpose?
* Where do evaluation metrics agree or disagree on the same response?
* Which retrieval or generation failures does each metric detect or miss?
* How does document-collection size or composition affect retrieval and evaluation results?
* Which RAG configuration produces better responses?

The project shall not assume that one evaluation metric or configuration is universally best. Conclusions shall identify the corpus, questions, settings, metrics, and limitations behind each finding.

---

## 5. Metrostate Document Requirement

The project must use Metrostate documents as the RAG example dataset.

Examples of possible Metrostate documents include:

* Course syllabi
* Program requirements
* Academic policies
* Student handbook pages
* Registration information
* Graduation requirements
* Financial aid information
* Advising documents
* Department documents
* Public Metrostate web pages or PDFs

The application should process these documents so users can ask questions and receive answers grounded in the document content.

---

## 6. Functional Requirements

## 6.1 Document Management

The system shall allow admin users to upload Metrostate documents.

The system shall support common document formats such as:

* TXT
* Text-based PDF
* DOCX
* HTML or copied webpage text, if supported

The system shall store document metadata in MySQL, including:

* Document ID
* Document title
* File name
* Upload date
* Uploaded by
* Document type
* Status

The system shall store the original display filename separately from the
server-controlled runtime storage path.

The system shall allow admin users to view uploaded documents.

The system shall allow admin users to delete or replace uploaded documents.

FP6 implements live document/category counts plus replacement and confirmed
deletion for browser-managed uploads. Deletion removes the stored file, MySQL
document/chunks, and matching ChromaDB vectors. The bundled Metro State source
documents are intentionally protected from browser replacement or deletion.

The system shall prepare uploaded documents for RAG processing.

The browser upload workflow shall validate extension, MIME type, file size, upload status, and parser output. Uploaded filenames shall not be trusted as server storage names. The system shall reject encrypted, unreadable, empty, or unsupported files with a clear error and record ingestion failures for diagnosis.

TXT, PDF, and DOCX inputs shall be converted into normalized text and then use the same chunking, metadata, MySQL, and ChromaDB ingestion path. Scanned-image PDF OCR is optional unless separately required.

---

## 6.2 Document Chunking

The system shall split uploaded documents into smaller text chunks.

Each chunk shall be associated with its original document.

Each chunk shall store useful metadata, such as:

* Chunk ID
* Document ID
* Chunk text
* Chunk order
* Page number or section, if available
* Created date

The system should support configurable chunking settings, such as:

* Chunk size
* Chunk overlap

---

## 6.3 Embeddings and Retrieval

The system shall generate embeddings for document chunks using an approved embedding provider.

The system shall store chunk information and retrieval metadata.

The system shall retrieve relevant chunks based on the user’s question.

The system should support configurable retrieval settings, such as:

* Top-k value
* Similarity threshold
* Embedding model
* Retrieval method

The system shall return the most relevant document chunks to the answer generation step.

---

## 6.4 Question Answering

The system shall provide a user interface where users can ask questions about Metrostate documents.

The system shall send the user question and retrieved context to an LLM provider.

The system shall generate an answer based on the retrieved Metrostate document context.

The system shall display the answer to the user.

The system shall display the source documents or source chunks used to generate the answer.

The system should avoid answering questions that are not supported by the retrieved Metrostate documents.

---

## 6.5 Evaluation Test Set

The system shall allow admin users to create and manage evaluation test questions.

Each test question should include:

* Question ID
* Question text
* Expected answer
* Related source document, if known
* Category or topic
* Difficulty level, if needed

The project shall begin with at least 25 manually reviewed Metrostate-related test questions. Twenty-five is a starting target, not a fixed ratio between questions and documents. Additional questions shall be added when they improve category, document, difficulty, answerability, or failure-mode coverage.

The initial test set shall:

* Cover all current document categories
* Include answerable and deliberately unanswerable questions
* Include factual dates, amounts, requirements, and policy questions
* Store a verified expected answer and expected source for answerable questions
* Store answerability, category, and difficulty metadata
* Avoid redundant questions unless repetition supports a documented experiment

The test set will be used to compare RAG performance across different settings and evaluation methods.

---

## 6.6 RAG Evaluation Methods

The system shall support multiple evaluation methods for comparing actual generated answers against expected answers and retrieved context.

The same stored responses should be scored by multiple methods so metric results can be compared directly. The system shall preserve per-question scores and should identify cases where metrics disagree. Metric documentation shall explain what each method measures, its intended use, and its limitations.

Possible evaluation methods include:

### Exact Match / String Match

Compares the generated answer directly with the expected answer.

### Token Overlap Metrics

Compares word or phrase overlap between the generated answer and the expected answer.

Examples:

* BLEU
* ROUGE
* METEOR

### Semantic Similarity

Compares the generated answer and expected answer using embeddings or semantic similarity.

### LLM-as-Judge

Uses an LLM to score the generated answer based on criteria such as accuracy, completeness, relevance, and faithfulness.

### RAGAS-style Metrics

Uses RAG evaluation metrics such as:

* Faithfulness
* Answer relevancy
* Context precision
* Context recall
* Answer correctness

### Human Evaluation

Allows manual review or scoring of generated answers.

---

## 6.7 Evaluation Criteria

The system should evaluate RAG responses using criteria such as:

### Answer Accuracy

Measures whether the generated answer is factually correct.

### Answer Relevance

Measures whether the generated answer directly responds to the user’s question.

### Faithfulness

Measures whether the answer is supported by the retrieved document chunks.

### Context Precision

Measures whether the retrieved chunks are relevant to the question.

### Context Recall

Measures whether the retrieved chunks contain the information needed to answer the question.

### Source Accuracy

Measures whether the answer cites or uses the correct Metrostate source document.

### Hallucination Detection

Measures whether the generated answer includes information not supported by the retrieved context.

---

## 6.8 Evaluation Dashboard

The system shall include a dashboard for viewing evaluation results.

The dashboard should show:

* Total number of test questions
* Average accuracy score
* Average relevance score
* Average faithfulness score
* Average context precision score
* Average context recall score
* Pass/fail results
* Evaluation method used
* Model used
* Retrieval settings used

The dashboard should allow comparison between different RAG configurations.

Example comparison settings include:

* Different chunk sizes
* Different chunk overlap values
* Different top-k retrieval values
* Different LLM models
* Different embedding models
* Different evaluation frameworks

---

## 6.9 Reports

The system should generate summary reports for business users and managers.

Reports should explain:

* Which RAG approach performed better for the tested corpus and settings
* Which evaluation framework was useful for each specific purpose
* Where evaluation metrics agreed or disagreed
* Which problems each metric detected or missed
* Which settings improved answer quality
* Which settings caused weaker results
* Common failure cases
* What was learned from document-collection size or composition experiments
* Which conclusions cannot be generalized to enterprise-scale collections
* Recommendations for future development

Reports may include tables, charts, or summary text.

---

## 6.10 User Interface Requirements

The front end shall be built using HTML, CSS, JavaScript, jQuery, and Bootstrap.

The application should include the following pages:

* Home page
* Document upload page
* Document list page
* Chat / question page
* Evaluation test set page
* Evaluation results page
* Dashboard page
* Report page
* About / project information page

The interface should be simple, clean, and easy to use.

Bootstrap should be used for layout, forms, buttons, tables, cards, and responsive design.

---

## 7. Database Requirements

The MySQL database should store the main application data.

ChromaDB should store RAG vector data, including document chunks, embeddings,
source metadata, and retrieval collections.

Possible tables include:

### users

Stores user account information if login is implemented.

### documents

Stores uploaded document metadata.

### document_chunks

Stores chunked document text and metadata.

### questions

Stores user questions and evaluation test questions.

### expected_answers

Stores expected answers for test questions.

### rag_responses

Stores generated answers from the RAG system.

### retrieved_contexts

Stores retrieved chunks used for each question.

### evaluation_runs

Stores each evaluation run.

### evaluation_scores

Stores scores from different evaluation methods.

### model_settings

Stores model, embedding, chunking, and retrieval settings.

---

## 8. Non-Functional Requirements

## 8.1 Usability

The application should be easy for business users, managers, developers, and students to understand.

## 8.2 Maintainability

The code should be organized so future developers can extend the project.

## 8.3 Modularity

The RAG pipeline should be separated into clear steps:

* Document upload
* Chunking
* Embedding
* Retrieval
* Answer generation
* Evaluation
* Reporting

## 8.4 Security

API keys should not be hardcoded in public files.

Sensitive configuration values should be stored in a separate configuration file or environment file.

User input should be validated before being stored or processed.

Database queries should use prepared statements to reduce SQL injection risk.

## 8.5 Performance

The application should handle a reasonable number of Metrostate documents and test questions on a local development machine.

The research shall recognize that organizations may search hundreds to millions of documents. The local project is not required to reproduce enterprise scale, but it shall support a controlled comparison between document subsets or differently composed collections and report how retrieval quality, answer quality, latency, and metric behavior change.

The system should avoid unnecessary repeated API calls when possible.

The system should store results so previous evaluations can be reviewed without rerunning every test.

## 8.6 Cost Awareness

The system should track or estimate API usage when using paid model providers.

The system should allow smaller test runs to reduce unnecessary API cost.

---

## 9. Success Criteria

The project will be considered successful if:

* The application runs using the required technology stack.
* Metrostate documents can be used as the RAG knowledge base.
* Users can ask questions and receive generated answers.
* Retrieved sources or chunks are shown with the answer.
* The system can run evaluation tests against expected answers.
* The system compares at least two RAG evaluation methods.
* The system stores evaluation results in MySQL.
* At least 25 reviewed questions cover the current categories and answerability cases.
* TXT, text-based PDF, and DOCX documents can enter the common ingestion pipeline through the browser workflow.
* The dashboard or report explains metric usefulness, metric disagreement, failure cases, and configuration results.
* A controlled collection-size or collection-composition experiment is reproducible and its limits are documented.
* The application provides a useful starting point for future developers.

---

## 10. Possible Evaluation Experiments

The project may compare RAG performance using experiments such as:

### Experiment 1: Different Top-K Values

Compare response quality when retrieving different numbers of chunks.

Example:

* Top-k = 3
* Top-k = 5
* Top-k = 8

### Experiment 2: Different Chunk Sizes

Compare response quality using different chunk sizes.

Example:

* Small chunks
* Medium chunks
* Large chunks

### Experiment 3: Different Evaluation Methods

Compare how different evaluation frameworks score the same responses.

Example:

* Exact match
* Semantic similarity
* LLM-as-judge
* RAGAS-style metrics

### Experiment 4: Different Models

Compare results using different LLM providers or models.

Example:

* OpenAI/ChatGPT model
* Gemini model
* Claude model
* Other supported model provider
* Local model, if supported

### Experiment 5: Document Collection Size and Composition

Run the same applicable questions against reproducible document collections, such as a focused subset and the full current collection. If additional approved documents are available, include a larger collection or add similar distractor documents.

Compare:

* Expected-source hit rate and rank
* Irrelevant-context rate
* Answer correctness and faithfulness
* Refusal correctness
* Latency
* Agreement and disagreement between evaluation metrics

The results shall be presented as evidence from the tested collections, not as proof of behavior at millions-of-documents scale.

---

## 11. Project Scope

## 11.1 In Scope

The following items are in scope:

* Web-based application
* Metrostate document upload and management
* TXT, text-based PDF, and DOCX parsing
* RAG question-answering system
* Approved LLM provider integration
* MySQL storage
* RAG response evaluation
* Evaluation dashboard
* Comparison of RAG approaches
* Reports for business users and developers
* At least 25 reviewed evaluation questions
* Metric-usefulness and metric-disagreement analysis
* Controlled document-collection size or composition experiments

## 11.2 Out of Scope

The following items are out of scope for the initial version:

* Training a custom large language model
* Building a production-level enterprise chatbot
* Supporting every possible document type
* Real-time multi-user collaboration
* Full authentication system, unless required
* Production deployment at enterprise scale
* Guaranteeing perfect answer accuracy

---

## 12. Open Questions

The following questions should be clarified with the professor:

1. Should the project port more from RagWorks or Student Compass?
2. Should the final app require user login, or can it be a simple admin/user interface without authentication?
3. Which Metrostate documents should be used first?
4. Which evaluation frameworks beyond the initial baseline metrics are required versus optional?
5. Should RAGAS or DeepEval be integrated directly, or should the project implement selected comparable metrics?
6. What is the minimum expected dashboard/report for the final submission?
7. Are charts required, or are tables and written summaries enough?
8. Is scanned-PDF OCR required, or are text-based PDFs sufficient?

---

## 13. Initial Minimum Viable Product

The initial MVP should include:

1. Upload TXT, text-based PDF, and DOCX Metrostate documents
2. Store document metadata in MySQL
3. Chunk document text
4. Generate embeddings using the configured local or provider model
5. Retrieve relevant chunks for a question
6. Generate an answer using an LLM API
7. Display answer and sources
8. Store question, answer, context, and settings
9. Run the reviewed evaluation set with multiple metrics
10. Display per-question and aggregate results in a table or dashboard

---

## 14. Future Enhancements

Possible future enhancements include:

* More advanced RAG evaluation frameworks
* More model providers
* OCR for scanned PDFs and additional document formats
* Visual charts for evaluation results
* User feedback buttons
* Human evaluation workflow
* Exportable reports
* Admin authentication
* Side-by-side model comparison
* Automated, purpose-specific recommendations with documented evidence
