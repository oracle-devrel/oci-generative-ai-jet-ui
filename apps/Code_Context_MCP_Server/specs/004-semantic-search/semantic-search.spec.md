# Feature Specification: Semantic Code Search

**Feature Branch**: `004-semantic-search`
**Created**: 2026-10-10
**Status**: Draft
**Input**: Load an embedding model into the database, have the database embed every indexed symbol as it is stored, index the embeddings for fast nearest-neighbour search, and add a search command that answers a plain-English question with the 10 closest symbols, dropping anything below a cosine similarity of 0.3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The database can turn text into vectors on its own (Priority: P1)

A developer runs one setup command. It loads the published `all_MiniLM_L12_v2` model into the database under the name `ALL_MINILM_L12_V2`. From then on the database embeds text itself: no API key, no network call, and no source code leaves the database to be indexed.

**Why this priority**: everything else in this step depends on the model being in the database. Keeping code inside the database is what makes the tool acceptable to many teams.

**Independent Test**: run the setup command, then `SELECT model_name FROM user_mining_models;` and `SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v;`.

**Acceptance Scenarios**:

1. **Given** a database without the model, **When** the developer runs the model setup command, **Then** `SELECT model_name FROM user_mining_models;` lists `ALL_MINILM_L12_V2`.
2. **Given** the model is loaded, **When** the developer runs `SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v;`, **Then** it returns a vector of 384 elements.
3. **Given** the model is already loaded, **When** the setup command runs again, **Then** it reports the model as present and changes nothing.
4. **Given** the published model file cannot be downloaded, **When** the setup command runs, **Then** it fails with a message naming the file and where it was fetched from, and the database is unchanged.

---

### User Story 2 - Every indexed symbol gets an embedding (Priority: P1)

When a repository is ingested, the database computes each symbol's embedding from the symbol's text as the row is stored, and keeps it with the symbol. A nearest-neighbour index over the embeddings keeps searches fast as the index grows.

**Why this priority**: without embeddings there is nothing to search by meaning.

**Independent Test**: re-ingest flask and gin, then count symbols without an embedding (expect zero), and check that the vector index exists.

**Acceptance Scenarios**:

1. **Given** the model is loaded, **When** a repository is ingested, **Then** every stored symbol has a 384-dimension embedding computed by the database.
2. **Given** symbols indexed before this step, **When** the repository is re-ingested, **Then** all of its symbols have embeddings.
3. **Given** the model is not loaded, **When** a repository is ingested, **Then** ingest fails before changing anything and says to run the model setup command.
4. **Given** the schema is set up, **When** the developer inspects the database, **Then** a cosine-distance nearest-neighbour index exists on the embeddings.

---

### User Story 3 - Ask a question in plain English (Priority: P1)

A developer types `ccctx search "how are incoming requests routed to handlers"`. They get up to 10 symbols ranked by how close their meaning is to the question, each with its similarity score, repository, file and line range. The results include routing and dispatch code from both repositories, even though none of it contains the words typed.

**Why this priority**: this is what the step is for. It finds code that text search cannot.

**Independent Test**: after ingesting both repositories, run the routing question and the sourdough question and compare the results.

**Acceptance Scenarios**:

1. **Given** flask and gin are ingested with embeddings, **When** the developer searches "how are incoming requests routed to handlers", **Then** at most 10 results come back, ordered from most to least similar, and they include routing or dispatch code from both flask and gin.
2. **Given** any search, **When** results are shown, **Then** none has a cosine similarity below 0.3, and each shows its score.
3. **Given** a question unrelated to the indexed code, such as "recipe for sourdough bread", **When** the developer searches, **Then** few results or none come back. With none, the command says no symbol was similar enough rather than printing an empty table.
4. **Given** `--repo gin`, **When** the developer searches, **Then** only gin symbols are returned.
5. **Given** an empty question, **When** the developer searches, **Then** the command refuses with a message and exits non-zero.

---

### User Story 4 - Agents can search too (Priority: P2)

An MCP client calls a search tool with a question and gets the same ranked results the command line shows, as structured data with source locations.

**Why this priority**: the constitution requires search to be available over MCP, and agents are the main consumer of these results. The command line comes first because it is how the step is checked.

**Independent Test**: call the search tool from the MCP Inspector with the routing question and compare it with `ccctx search`.

**Acceptance Scenarios**:

1. **Given** both repositories are ingested, **When** a client calls the search tool with a question, **Then** it returns the same symbols, order and scores as `ccctx search` for that question.
2. **Given** the database is down or the model is missing, **When** a client calls the tool, **Then** it returns a clear "unavailable" result with a reason, not a crash.

### Edge Cases

- **Long symbols**: a class or file window longer than the model's input limit is embedded from its leading text. This is the model's own truncation, and it is not an error.
- **Fallback chunks**: windows of documentation and config are embedded and searchable like any other symbol, and are shown with kind `chunk`.
- **Fewer than 10 above the floor**: only the ones at or above 0.3 are shown. The floor is never relaxed to fill the list.
- **Nothing ingested yet**: search says there is nothing indexed.
- **Unknown `--repo`**: search refuses and names the repository.
- **Model replaced or changed**: the model name and its dimension are recorded. Embeddings from a different model are never mixed in one index.
- **Database down**: search fails within a few seconds with no password in the output.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A setup command MUST load the published ONNX `all_MiniLM_L12_v2` model into the database with `DBMS_VECTOR.LOAD_ONNX_MODEL` under the name `ALL_MINILM_L12_V2`. It MUST do nothing when the model is already loaded.
- **FR-002**: The model file MUST be obtained once from Oracle's published location. No source code or symbol text is ever sent outside the database.
- **FR-003**: Each symbol MUST have an embedding stored in a `VECTOR(384, FLOAT32)` column.
- **FR-004**: The database MUST compute each embedding with `VECTOR_EMBEDDING` as the symbol row is inserted. Embeddings MUST NOT be computed in the application and sent to the database.
- **FR-005**: The embedded text for a symbol MUST include its name, its kind, its file path and its source.
- **FR-006**: An HNSW vector index MUST exist on the embedding column, created with `ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95`.
- **FR-007**: The model name and the embedding dimension MUST be recorded alongside the index, so that a change of model can be detected.
- **FR-008**: Ingest MUST refuse to run, changing nothing, when the model is not loaded, and MUST name the setup command in its message.
- **FR-009**: `ccctx search "<question>"` MUST embed the question with the same in-database model and return the 10 symbols closest by cosine distance.
- **FR-010**: Search MUST drop every result with a cosine similarity below 0.3, where similarity is 1 minus cosine distance.
- **FR-011**: Each search result MUST show its rank, similarity, repository, kind, name, file path and line range, ordered from most to least similar.
- **FR-012**: When no result reaches the floor, search MUST say so and exit successfully.
- **FR-013**: `ccctx search` MUST accept `--repo <name>` to search one repository, and MUST refuse an unknown name.
- **FR-014**: Search MUST refuse an empty question, an unreachable database and a missing model with a non-zero exit, a clear message and no secret in its output.
- **FR-015**: An MCP search tool MUST return the same results as `ccctx search`, as structured data including repository, path, line range, kind, name and similarity, using the same core code.

### Key Entities

- **Embedding model**: the `ALL_MINILM_L12_V2` model stored in the database. It turns text into 384-number vectors.
- **Symbol embedding**: a 384-dimension vector stored with each symbol, computed by the database from the symbol's name, kind, path and source.
- **Vector index**: a cosine-distance nearest-neighbour index over the symbol embeddings, with the model name and dimension recorded alongside it.
- **Search result**: one symbol returned for a question. Its rank, similarity, repository, kind, name, path and line range.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After setup, the model check lists `ALL_MINILM_L12_V2`, and embedding 'hello world' returns exactly 384 elements.
- **SC-002**: After re-ingesting both repositories, 100% of their symbols have an embedding.
- **SC-003**: For "how are incoming requests routed to handlers", the top 10 results include at least one routing or dispatch symbol from flask and at least one from gin.
- **SC-004**: For "recipe for sourdough bread", 3 or fewer results come back.
- **SC-005**: 100% of results shown by any search have similarity of at least 0.3, in descending order.
- **SC-006**: A search over both repositories answers in under 2 seconds once the model is loaded.
- **SC-007**: Ingesting flask, and ingesting gin, each finishes in under 5 minutes with embeddings.
- **SC-008**: The MCP search tool and the command line return identical results for the same question.

## Assumptions

- **The model file is downloaded once, then loaded by the database.** The setup command is `ccctx model load`. It fetches Oracle's published augmented ONNX file for `all_MiniLM_L12_v2`, places it where the database can read it, and loads it. Downloading the model sends nothing of the code anywhere.
- **The database is configured for in-memory vector indexes.** The vector memory pool is enabled as part of the container setup, since the HNSW index lives in memory.
- **Every stored symbol is searchable, fallback chunks included**, so documentation can answer a question too. Kind is shown, so a reader can tell a window from a definition.
- **Similarity is 1 minus cosine distance.** The floor of 0.3 and the limit of 10 are fixed for this step.
- **Search is semantic only in this step.** The constitution's default fused keyword and semantic ranking is a later step. Each result already reports its semantic score, so the later fusion can expose component scores alongside it.
- **Search is approximate.** It uses the index's target accuracy of 95%, so on rare occasions it may miss a result an exhaustive scan would return.
- **Existing symbols get embeddings by re-ingesting.** No separate backfill command is added.

## Verbatim Constraints

- Model: `all_MiniLM_L12_v2`, loaded with `DBMS_VECTOR.LOAD_ONNX_MODEL` as `ALL_MINILM_L12_V2`
- Column type: `VECTOR(384, FLOAT32)`, populated with `VECTOR_EMBEDDING`
- Index: `ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95`
- Search: `ccctx search "how are incoming requests routed to handlers"`, `ccctx search "recipe for sourdough bread"`
- Result count `10`, cosine similarity floor `0.3`
- Checks: `SELECT model_name FROM user_mining_models;` and `SELECT VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING 'hello world' as data) AS v;`
