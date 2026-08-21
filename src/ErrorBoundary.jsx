import React from 'react'

export default class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24, fontFamily: 'Inter, Arial, sans-serif' }}>
        <div style={{ maxWidth: 720, width: '100%', border: '1px solid #e5e7eb', borderRadius: 16, padding: 24 }}>
          <h1 style={{ marginTop: 0, color: '#114b3a' }}>KDCCE could not load</h1>
          <p style={{ color: '#66706b', lineHeight: 1.6 }}>
            Open the browser console for the exact error. Most setup issues are fixed with the install commands in the README.
          </p>
          <pre style={{ whiteSpace: 'pre-wrap', background: '#f8fafc', padding: 16, borderRadius: 12, overflow: 'auto' }}>
            {this.state.error?.message || 'Unknown error'}
          </pre>
        </div>
      </div>
    )
  }
}
