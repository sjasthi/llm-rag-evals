# LLM RAG Evaluations Web Application

## 1. Project Overview

The goal of this project is to build a web-based application for evaluating Retrieval-Augmented Generation (RAG) approaches using Metrostate documents as the example knowledge base.

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
* Which evaluation method gives the most useful results for business users and developers?
* Which RAG configuration produces better responses?

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

* PDF
* TXT
* DOCX, if supported
* HTML or copied webpage text, if supported

The system shall store document metadata in MySQL, including:

* Document ID
* Document title
* File name
* Upload date
* Uploaded by
* Document type
* Status

The system shall allow admin users to view uploaded documents.

The system shall allow admin users to delete or replace uploaded documents.

The system shall prepare uploaded documents for RAG processing.

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

The project should include a set of sample Metrostate-related test questions.

The test set will be used to compare RAG performance across different settings and evaluation methods.

---

## 6.6 RAG Evaluation Methods

The system shall support multiple evaluation methods for comparing actual generated answers against expected answers and retrieved context.

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

* Which RAG approach performed best
* Which evaluation framework was most useful
* Which settings improved answer quality
* Which settings caused weaker results
* Common failure cases
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

The application should handle a reasonable number of Metrostate documents and test questions.

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
* The dashboard or report helps users understand which RAG approach performed better.
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

---

## 11. Project Scope

## 11.1 In Scope

The following items are in scope:

* Web-based application
* Metrostate document upload and management
* RAG question-answering system
* Approved LLM provider integration
* MySQL storage
* RAG response evaluation
* Evaluation dashboard
* Comparison of RAG approaches
* Reports for business users and developers

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
4. How many evaluation questions are required?
5. Which evaluation frameworks are required versus optional?
6. Should RAGAS or DeepEval be integrated directly, or should the project implement simplified versions of those metrics?
7. Should the application call LLM provider APIs directly from PHP, or should PHP call a separate helper script or service?
8. What is the minimum expected dashboard/report for the final submission?
9. Should the project focus more on business decision-making reports or developer implementation structure?
10. Are charts required, or are tables and written summaries enough?

---

## 13. Initial Minimum Viable Product

The initial MVP should include:

1. Upload Metrostate documents
2. Store document metadata in MySQL
3. Chunk document text
4. Generate embeddings using an API
5. Retrieve relevant chunks for a question
6. Generate an answer using an LLM API
7. Display answer and sources
8. Store question, answer, context, and settings
9. Run a small evaluation set
10. Display evaluation results in a simple table or dashboard

---

## 14. Future Enhancements

Possible future enhancements include:

* More advanced RAG evaluation frameworks
* More model providers
* Better document parsing
* Visual charts for evaluation results
* User feedback buttons
* Human evaluation workflow
* Exportable reports
* Admin authentication
* Side-by-side model comparison
* Automated recommendations for best RAG settings
