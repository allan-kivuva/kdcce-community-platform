import React from 'react'

export default class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="grid min-h-screen place-items-center bg-kBg p-6 font-sans text-kInk">
        <div className="w-full max-w-2xl rounded-2xl border border-kBorder bg-kSurface p-6">
          <h1 className="mt-0 font-display text-2xl font-bold text-kGreen">KDCCE could not load</h1>
          <p className="leading-relaxed text-kMuted">
            Open the browser console for the exact error. Most setup issues are fixed with the install commands in the README.
          </p>
          <pre className="overflow-auto whitespace-pre-wrap rounded-xl bg-kCream p-4 text-kInk">
            {this.state.error?.message || 'Unknown error'}
          </pre>
        </div>
      </div>
    )
  }
}
