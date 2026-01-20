```markdown
## Preliminary Repository Guidance
- If an `AGENTS.md` file exists in the repo root, inspect it first and align with any procedures it specifies before implementing the endpoint. (Assume either none exists or that it confirms the standard practices outlined below.)
- Identify the service or module handling finance endpoints—look for directories like `services/finance`, `api/finance`, `controllers/finance`, or similar within the backend portion of the repo.

## Key Files/Areas to Inspect
1. **Existing Finance Endpoints**
   - Locate current router/controller definitions for `/finance/*`. Look for files such as `financeRouter.ts`, `financeController.ts`, or similar under `src/api`, `src/routes`, or `src/controllers`.
2. **CSV Statement Ingestion Logic**
   - Search for existing services/utilities dealing with CSV parsing (e.g., `csvParser.ts`), statement ingestion (e.g., `statementService.ts`), or data transformation utilities; these may live under `src/services`, `src/lib`, or `src/utils`.
3. **Orchestrator Patterns**
   - Identify any orchestrators for other endpoints; e.g., `ingestOrchestrator.ts`, `transactionOrchestrator.ts`. Follow the structure/pattern for consistent implementation if such files exist.
4. **Data Models and Validation**
   - Inspect models or DTO definitions for finance statements (e.g., `StatementDTO`, `TransactionModel`). These may be in `src/models` or `src/types`.
5. **Tests**
   - Check for finance-related tests under `tests/finance`, `__tests__/finance`, or similar to understand coverage expectations.

## Implementation Steps
1. **Define the /finance/ingest Route**
   - Update the finance router to register a new POST endpoint at `/finance/ingest`.
   - Ensure the route points to a handler function such as `financeIngestOrchestrator`.
   - Document the expected request payload schema in code comments or validation middleware (CSV file reference, metadata, etc.).

2. **Create Orchestrator Module**
   - If not already present, create `src/services/finance/ingestOrchestrator.ts` (or similar) to encapsulate the orchestration logic for ingestion.
   - The orchestrator should:
     - Parse the CSV payload using existing CSV utilities or a new parser if needed.
     - Validate parsed records against the expected schema (dates, amounts, identifiers).
     - Call downstream services (e.g., `statementService.processStatement(record)`).
     - Collect and return status/result metadata (success count, failures, errors).

3. **Leverage Existing CSV Parsing/Validation**
   - Reuse any shared CSV parser or validation helpers. If none exist:
     - Introduce a CSV parsing utility using a library available in the repo (e.g., `papaparse`, `csv-parse`).
     - Ensure parser handles headers, type conversions (dates/numbers), and error aggregation.
   - Implement schema validation using existing DTOs or `zod`/`io-ts` schemas if used elsewhere (align with repo style).

4. **Integrate with Statement Processing Services**
   - Identify the service responsible for persisting/order statements (likely `statementService.processCsvOrRecords` or similar).
   - Have the orchestrator map parsed rows to the required input format and call the service.
   - Handle service responses: track successes/failures, log relevant messages, and assemble a final response.

5. **Response Format**
   - Return a JSON response that includes:
     - Total records received
     - Number successfully ingested
     - Number/array of records with errors and associated messages
     - Any metadata (ingestId, timestamp) if required
   - Set appropriate HTTP status codes (e.g., `200` for partial success, `400` for validation failures).

6. **Error Handling**
   - Ensure top-level error handling is consistent with other endpoints (use `try/catch`, `next(error)` if Express).
   - Wrap parsing/processing errors with contextual information for debugging.

7. **Tests**
   - Add unit tests for the orchestrator:
     - Mock CSV parsing and downstream service to assert orchestrator behavior on success/failure.
     - Validate error aggregation and response structure.
   - Add integration/api tests hitting `/finance/ingest`:
     - Simulate CSV request payloads (success, partial errors).
     - Assert response structure and status codes.

8. **Register the Endpoint**
   - If router registration requires updates (e.g., `routes/index.ts`), make sure `/finance/ingest` is included.
   - Update any API documentation (e.g., Swagger/OpenAPI definitions) if present.

## Validation/Tests to Run
1. **Unit Tests**
   - Run targeted unit tests for the new orchestrator or parser (e.g., `npm run test -- ingestOrchestrator` or equivalent).
2. **Integration/API Tests**
   - Execute integration suites that include finance endpoints (e.g., `npm run test:integration -- finance`).
3. **Linting and Type Checks**
   - Run `npm run lint`/`npm run typecheck` to ensure code style and typing consistency.
4. **Smoke Testing (if automated)**
   - Send a POST request to `/finance/ingest` in a controlled test environment to confirm end-to-end processing.

##