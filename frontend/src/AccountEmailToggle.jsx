import { useState } from 'react'
import './PublicationInteractions.css'

export default function AccountEmailToggle({ email }) {
  const [shown, setShown] = useState(false)
  const at = email.indexOf('@')
  const masked = email ? `${email[0]}••••••••${at >= 0 ? email.slice(at) : ''}` : 'Not provided'
  return <span className="account-email-toggle"><span>{shown ? email : masked}</span>{email && <button type="button" onClick={() => setShown(!shown)} aria-label={shown ? 'Hide email address' : 'Show email address'} aria-pressed={shown}>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{shown && <path d="m3 3 18 18"/>}</svg>
  </button>}</span>
}
