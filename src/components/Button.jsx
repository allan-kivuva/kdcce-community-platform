import React from 'react'
import { Link } from 'react-router-dom'

export function PrimaryButton({ children, to, onClick, type = 'button', className = '' }) {
  const classes = `btn-orange ${className}`
  if (to) return <Link to={to} className={classes}>{children}</Link>
  return <button type={type} onClick={onClick} className={classes}>{children}</button>
}

export function OutlineButton({ children, to, onClick, type = 'button', className = '' }) {
  const classes = `btn-outline ${className}`
  if (to) return <Link to={to} className={classes}>{children}</Link>
  return <button type={type} onClick={onClick} className={classes}>{children}</button>
}

export function GreenButton({ children, to, onClick, type = 'button', className = '' }) {
  const classes = `btn-green ${className}`
  if (to) return <Link to={to} className={classes}>{children}</Link>
  return <button type={type} onClick={onClick} className={classes}>{children}</button>
}
