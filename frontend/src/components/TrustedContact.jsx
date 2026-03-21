import React, { useState } from 'react'

/**
 * Post-call trusted contact notification.
 * Allows users to set up family members to be notified after flagged calls.
 */
export default function TrustedContact({ riskLevel = 'low' }) {
  const [contacts, setContacts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [notified, setNotified] = useState(false)

  const addContact = () => {
    if (name && phone) {
      setContacts((prev) => [...prev, { name, phone }])
      setName('')
      setPhone('')
      setShowForm(false)
    }
  }

  const notifyContacts = () => {
    // In real mode, this would send SMS via backend
    setNotified(true)
    setTimeout(() => setNotified(false), 3000)
  }

  return (
    <div className="bg-surface-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-4">Trusted Contacts</h3>

      {contacts.length === 0 && !showForm ? (
        <div className="text-center py-4">
          <p className="text-gray-400 text-sm mb-3">
            Add a family member to notify after suspicious calls.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl
                       font-semibold min-h-[64px] transition-colors"
          >
            Add Trusted Contact
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
            className="w-full bg-surface-700 border border-gray-600 rounded-lg px-4 py-3
                       text-base text-white placeholder-gray-400 focus:border-blue-500"
          />
          <input
            type="tel"
            placeholder="Phone number"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full bg-surface-700 border border-gray-600 rounded-lg px-4 py-3
                       text-base text-white placeholder-gray-400 focus:border-blue-500"
          />
          <div className="flex gap-2">
            <button
              onClick={addContact}
              className="bg-green-600 hover:bg-green-500 text-white px-4 py-2
                         rounded-lg font-medium transition-colors"
            >
              Save
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="bg-surface-700 hover:bg-surface-900 text-gray-300 px-4 py-2
                         rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {contacts.length > 0 && (
        <>
          <ul className="space-y-2 mb-4">
            {contacts.map((c, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span>{c.name}</span>
                <span className="text-gray-400">{c.phone}</span>
              </li>
            ))}
          </ul>

          {riskLevel === 'high' && (
            <button
              onClick={notifyContacts}
              disabled={notified}
              className="w-full bg-red-600 hover:bg-red-500 text-white px-4 py-3
                         rounded-xl font-semibold min-h-[64px] transition-colors
                         disabled:opacity-50"
            >
              {notified ? 'Contacts notified!' : 'Notify trusted contacts'}
            </button>
          )}

          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="mt-2 text-sm text-blue-400 hover:text-blue-300"
            >
              + Add another contact
            </button>
          )}
        </>
      )}
    </div>
  )
}
