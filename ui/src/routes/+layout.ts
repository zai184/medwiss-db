// Prerender every route to static HTML (adapter-static). The VPS static
// server (medwiss-serve.ts) has no working SPA fallback, so deep links like
// /rechner or /search must exist as real files in build/.
export const prerender = true;
