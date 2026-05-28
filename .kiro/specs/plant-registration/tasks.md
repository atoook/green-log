# Implementation Plan

- [x] 1. Foundation: runtime, routing, and database setup
- [x] 1.1 Backend runtime configuration and database engine setup
  - Add runtime configuration for local SQLite, Turso database URL, and Turso auth token.
  - Add SQLAlchemy engine creation that supports both `sqlite:///...` and `sqlite+libsql://...` connection modes.
  - Add session dependency plumbing that can be reused by API handlers, Alembic, and smoke verification.
  - Add `sqlalchemy-libsql` to backend dependencies without changing the public Plant API contract.
  - Done when a local SQLite engine and a Turso-targeted libSQL engine can be constructed from environment configuration.
  - _Requirements: 6.1, 6.2_
  - _Boundary: Runtime Config, Database Engine_

- [x] 1.2 Alembic migration environment and Plant table migration
  - Add Alembic configuration that uses the same database URL resolution as runtime.
  - Create the initial Plant table migration with required columns, constraints, timestamps, and name index.
  - Keep the migration manually reviewable for SQLite and Turso compatibility instead of relying only on autogenerate output.
  - Done when `alembic upgrade head` creates the `plants` table against local SQLite.
  - _Depends: 1.1_
  - _Requirements: 1.3, 2.1, 2.3, 2.4, 2.5, 2.6, 6.1, 6.2, 6.5, 6.6_
  - _Boundary: Alembic Migration, Plant Model_

- [x] 1.3 Frontend dependency and routing foundation
  - Add Vue Router and Tailwind CSS tooling needed by the Plant Registration UI.
  - Configure explicit routes for `/`, `/plants`, and `/plants/:plantId`.
  - Register the router in the Vue app and replace the starter shell with a router-view based app shell.
  - Keep Pinia out of the dependency set and avoid introducing a global store.
  - Done when the Vite app can navigate between the Plant list route and Plant detail route shell.
  - _Requirements: 3.5, 4.1, 4.4, 5.3, 7.4_
  - _Boundary: Vue Router, App Shell_

- [x] 2. Backend Plant domain and API
- [x] 2.1 Plant model and schema contracts
  - Define Plant as a user-owned pot or individual plant record, not a species catalog entry.
  - Define create and read schemas with camelCase API fields and typed date, text, image URL, watering cycle, and timestamp values.
  - Enforce required name and positive watering cycle constraints at the schema or domain boundary.
  - Exclude watering history, next watering date, photo history, species master, and upload storage fields.
  - Done when Plant create and read payloads serialize consistently between Python domain names and API JSON field names.
  - _Depends: 1.2_
  - _Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - _Boundary: Plant Model, Plant Schemas_

- [x] 2.2 Plant persistence repository
  - Add persistence operations for creating, listing, and fetching Plant records by ID.
  - Ensure create commits and refreshes the persisted record so generated identifiers and timestamps are observable.
  - Return missing records as absence from the persistence boundary rather than HTTP errors.
  - Do not add update, delete, watering, photo, or species lookup persistence operations.
  - Done when repository operations pass against a migrated local SQLite database.
  - _Depends: 2.1_
  - _Requirements: 1.2, 1.3, 3.1, 4.1, 4.4, 6.1_
  - _Boundary: PlantRepository_

- [x] 2.3 Plant service behavior and validation
  - Add create, list, and detail use cases over the repository.
  - Reject blank plant names and watering cycles below one day with domain-level validation.
  - Convert missing detail records into a not-found domain outcome for the router.
  - Keep the service free of watering schedule calculations, image upload behavior, and species recommendations.
  - Done when service-level tests or checks show valid plants are created and invalid names or cycles are rejected.
  - _Depends: 2.2_
  - _Requirements: 1.2, 1.4, 2.2, 2.7, 4.4, 6.3, 6.4, 6.5, 6.6_
  - _Boundary: PlantService_

- [x] 2.4 Plant REST endpoints and app registration
  - Add endpoints for creating plants, listing plants, and fetching a plant detail.
  - Map validation failures and not-found outcomes to user-observable HTTP responses.
  - Register the Plant routes in the FastAPI app and preserve the generated OpenAPI contract.
  - Ensure no watering, photo, species, authentication, update, or delete endpoints are introduced.
  - Done when `POST /plants`, `GET /plants`, and `GET /plants/{plant_id}` work through the service boundary.
  - _Depends: 2.3_
  - _Requirements: 1.2, 3.1, 4.1, 4.4, 5.2, 5.3, 5.4, 6.3, 6.4, 6.5, 6.6_
  - _Boundary: PlantsRouter, FastAPI App_

- [x] 3. Frontend Plant pages and state
- [x] 3.1 (P) Typed Plant API client
  - Add a typed client for create, list, and detail requests.
  - Map validation, not found, network, and server failures into typed error results for UI consumption.
  - Keep API data in camelCase and avoid `any` in request, response, and error types.
  - Done when the client exposes typed functions for all Plant API operations and failure categories.
  - _Depends: 2.4_
  - _Requirements: 1.2, 3.1, 4.1, 5.2, 5.3, 5.4_
  - _Boundary: PlantsApiClient_

- [x] 3.2 (P) Plant form component
  - Build the create form for name, acquired date, memo, image URL, and watering cycle.
  - Show immediate user-facing errors for empty name and non-numeric or below-one watering cycle values.
  - Preserve user input when submission fails.
  - Use wording aligned with the product tone: record and care language rather than administrative task language.
  - Done when the form emits a valid create payload and displays field errors without requiring backend submission.
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 5.4, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: PlantForm_

- [x] 3.3 (P) Plant list component
  - Build the list presentation for registered plants with names and optional image previews.
  - Provide a readable fallback when an image URL is absent or unusable.
  - Show an empty state that makes plant registration the obvious next action.
  - Expose selection and retry events without owning route or API state.
  - Done when a non-empty list, no-image list item, empty state, and list error state render correctly.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: PlantList_

- [x] 3.4 (P) Plant detail component
  - Build the detail presentation for plant name, acquired date, memo, image URL, and watering cycle.
  - Keep layout stable when optional fields are absent.
  - Display not-found and load-failure states with a clear path back to the list.
  - Use mobile-first spacing and readable text without introducing upload, watering history, or species guidance UI.
  - Done when detail, optional-field, not-found, and load-failure states are visually distinguishable.
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.3, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: PlantDetail_

- [x] 3.5 Frontend composables for list, create, and detail
  - Add list and create state for the `/plants` page.
  - Add detail fetch state that treats the route plant ID as the source of truth.
  - Convert invalid route parameters into a user-observable not-found state.
  - Keep state local to pages and do not introduce Pinia or another global store.
  - Done when list/create state and route-based detail state can be exercised independently with the typed API client.
  - _Depends: 3.1_
  - _Requirements: 1.2, 3.1, 4.1, 4.4, 5.1, 5.2, 5.3, 5.4_
  - _Boundary: usePlants, usePlantDetail_

- [x] 3.6 Plant pages and route integration
  - Compose the `/plants` page from the form, list, and list/create composable.
  - Compose the `/plants/:plantId` page from the detail component and route-based detail composable.
  - Navigate to the created plant detail after successful registration.
  - Navigate from a list item to its detail route and support direct detail route loading.
  - Done when `/plants` and `/plants/:plantId` provide the complete registration, list, and detail user flow.
  - _Depends: 3.2, 3.3, 3.4, 3.5_
  - _Requirements: 1.1, 1.2, 3.1, 3.5, 4.1, 4.4, 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: PlantsPage, PlantDetailPage, Vue Router_

- [x] 4. Cross-boundary verification and hardening
- [x] 4.1 Backend local integration tests
  - Add tests for valid plant creation, listing, and detail retrieval through the HTTP API.
  - Add tests for empty name, invalid watering cycle, and missing plant detail responses.
  - Verify response payloads include stable identifiers, saved fields, and no next watering or watering history fields.
  - Done when backend integration tests pass against a migrated local SQLite database.
  - _Depends: 2.4_
  - _Requirements: 1.2, 1.3, 2.2, 2.7, 3.1, 3.2, 4.1, 4.4, 6.1, 6.2, 6.3, 6.4_
  - _Boundary: Backend Integration Tests_

- [x] 4.2 Turso migration and CRUD smoke verification
  - Add a smoke verification command for Turso/libSQL connection, migration target, Plant create/list/detail, and type round trip checks.
  - Verify UUID text, UTC datetime, and boolean storage behavior against local SQLite and Turso.
  - Fail fast when Turso credentials are missing for Turso mode and print a clear verification summary.
  - Done when the smoke command can prove migration and minimal Plant CRUD work against a Turso development database, or prints a blocking incompatibility that requires design review.
  - _Depends: 1.2, 2.4_
  - _Requirements: 1.2, 1.3, 3.1, 4.1, 6.1, 6.2_
  - _Boundary: TursoVerificationScript, Database Engine, Alembic Migration_
  - _Verified: Turso mode smoke passed against the configured development database with Alembic migration, Plant CRUD, UUID text, UTC datetime text, and boolean round-trip checks._

- [x] 4.3 Frontend route and UI validation
  - Add validation coverage for `/`, `/plants`, and `/plants/:plantId` navigation.
  - Verify the create flow navigates to detail, direct detail route loading fetches the plant, and invalid detail IDs show the not-found state.
  - Verify empty list, no-image plant, create failure, list failure, and detail failure states.
  - Check a mobile viewport for readable registration, list, and detail layouts without overlapping text.
  - Done when the frontend build and route/UI validation pass without Pinia or global state.
  - _Depends: 3.6_
  - _Requirements: 1.1, 1.2, 3.1, 3.4, 3.5, 4.1, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4_
  - _Boundary: Frontend Route and UI Validation_

- [x] 4.4 End-to-end local MVP flow validation
  - Run the backend and frontend together against local SQLite.
  - Create a plant from the UI and verify it appears in the list and detail route.
  - Verify the API and UI do not expose out-of-scope watering, photo upload, species master, authentication, update, or delete behavior.
  - Done when the local app demonstrates the complete Plant Registration MVP flow from UI to database and back.
  - _Depends: 4.1, 4.3_
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.5, 4.1, 4.2, 4.3, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4_

## Implementation Notes
- Turso remote smoke passed using `backend/.env` credentials. The smoke command verified Alembic migration, minimal Plant CRUD, UUID text, UTC datetime text, and boolean round-trip behavior against the configured development database.
