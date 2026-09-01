import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom doesn't implement scrollIntoView at all — components that call it
// (e.g. DirectConversationThread, scrolling to the latest message) would
// otherwise throw in every test that renders them, even though it works
// fine in a real browser.
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {})

// jsdom doesn't implement matchMedia either — ThemeProvider (used by any
// page rendered inside the real Shell/VolunteerShell) reads it on mount
// to resolve a system-preference default. A minimal "light, no listeners
// ever fire" stub is enough for tests; nothing here exercises live
// theme-change behavior.
window.matchMedia = window.matchMedia || (query => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

// Vitest's `globals: true` mode isn't enabled (test files import
// describe/it/expect explicitly), so React Testing Library's own
// auto-cleanup — which hooks into a global `afterEach` — needs wiring up
// here instead; without it, a component rendered in one test is still in
// the DOM when the next test's render runs.
afterEach(() => { cleanup() })
