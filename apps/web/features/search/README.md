# Search experience

`app/search/page.tsx` and the components in `features/search/` are implemented.

Users can submit a natural-language query, optionally filter by document type, read a
ranked patient-level result list where each entry shows the source document title, type,
date, and the matching passage, and navigate to the existing patient-detail route. Idle,
loading, results, no-results, validation, and dependency-failure states are all handled.
The form submits through a Server Action (`actions.ts`); the browser never calls the API
directly and server-only configuration stays out of browser code.
