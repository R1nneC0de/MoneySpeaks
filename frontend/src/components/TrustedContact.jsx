import React, { useState } from 'react'

/**
 * Trusted contact management — retro window panel style.
 */
export default function TrustedContact({
  riskLevel = 'low',
  contacts = [],
  onAddContact,
  onRemoveContact,
  onNotify,
}) {
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [notified, setNotified] = useState(false)
  const [saving, setSaving] = useState(false)

  const addContact = async () => {
    if (name && phone && onAddContact) {
      setSaving(true)
      try {
        await onAddContact(name, phone)
        setName('')
        setPhone('')
        setShowForm(false)
      } catch (e) {
        console.error('Failed to add contact:', e)
      } finally {
        setSaving(false)
      }
    }
  }

  const handleNotify = async () => {
    if (onNotify) {
      setNotified(true)
      try {
        await onNotify()
      } catch (e) {
        console.error('Failed to notify:', e)
      }
      setTimeout(() => setNotified(false), 3000)
    }
  }

  return (
    <div className="window-panel">
      <div className="window-titlebar">
        <span>[ TRUSTED CONTACTS ]</span>
        <span>■</span>
      </div>
      <div className="p-4">
        {contacts.length === 0 && !showForm ? (
          <div className="text-center py-4">
            <p className="font-mono text-sm text-crt-green-dim mb-3">
              &gt; Add a family member to notify after suspicious calls.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="btn-retro bg-crt-green/10 text-crt-green px-6 py-3
                         min-h-[48px]"
            >
              [+ ADD CONTACT]
            </button>
          </div>
        ) : null}

        {showForm && (
          <div className="space-y-3 mb-4">
            <input
              type="text"
              placeholder="Contact name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-retro w-full"
            />
            <input
              type="tel"
              placeholder="Phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="input-retro w-full"
            />
            <div className="flex gap-2">
              <button
                onClick={addContact}
                disabled={saving}
                className="btn-retro bg-crt-green/10 text-crt-green px-4 py-2"
              >
                {saving ? 'SAVING...' : '[SAVE]'}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="btn-retro bg-crt-panel text-crt-green-dim px-4 py-2"
              >
                [CANCEL]
              </button>
            </div>
          </div>
        )}

        {contacts.length > 0 && (
          <>
            <ul className="space-y-2 mb-4 font-mono text-sm">
              {contacts.map((c, i) => (
                <li key={i} className="flex items-center justify-between text-crt-green">
                  <span>{c.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-crt-green-dim">{c.phone}</span>
                    <button
                      onClick={() => onRemoveContact && onRemoveContact(i)}
                      className="text-crt-red hover:text-crt-red text-xs"
                    >
                      [DEL]
                    </button>
                  </div>
                </li>
              ))}
            </ul>

            {riskLevel === 'high' && (
              <button
                onClick={handleNotify}
                disabled={notified}
                className="btn-retro w-full bg-crt-red/10 text-crt-red px-4 py-3
                           min-h-[48px] disabled:opacity-40"
              >
                {notified ? '>> CONTACTS NOTIFIED <<' : '[! NOTIFY TRUSTED CONTACTS]'}
              </button>
            )}

            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="mt-2 font-mono text-sm text-crt-green-dim hover:text-crt-green"
              >
                [+ Add another]
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
