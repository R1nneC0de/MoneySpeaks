import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

/**
 * Auth context with Auth0 real mode / mock bypass.
 *
 * When AUTH0_DOMAIN and AUTH0_CLIENT_ID are set in env, uses @auth0/auth0-react.
 * Otherwise, provides a mock user that's always "logged in".
 */

const AUTH0_DOMAIN = import.meta.env.VITE_AUTH0_DOMAIN || ''
const AUTH0_CLIENT_ID = import.meta.env.VITE_AUTH0_CLIENT_ID || ''
const MOCK_MODE = !AUTH0_DOMAIN || !AUTH0_CLIENT_ID

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

// Mock user for development
const MOCK_USER = {
  sub: 'mock|12345',
  email: 'user@moneyspeaks.demo',
  name: 'Demo User',
  picture: '',
}

function MockAuthProvider({ children }) {
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    // Fetch profile from backend (which also runs in mock mode)
    fetch('/api/me')
      .then((r) => r.json())
      .then(setProfile)
      .catch(() => setProfile(MOCK_USER))
  }, [])

  const updateProfile = useCallback(async (updates) => {
    const res = await fetch('/api/me', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, ...data }))
    return data
  }, [])

  const addTrustedContact = useCallback(async (name, phone) => {
    const res = await fetch('/api/me/trusted-contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone }),
    })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, trusted_contacts: data.contacts }))
    return data
  }, [])

  const removeTrustedContact = useCallback(async (index) => {
    const res = await fetch(`/api/me/trusted-contacts/${index}`, { method: 'DELETE' })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, trusted_contacts: data.contacts }))
    return data
  }, [])

  const notifyContacts = useCallback(async (riskLevel) => {
    const res = await fetch('/api/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ risk_level: riskLevel }),
    })
    return res.json()
  }, [])

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: true,
        isLoading: false,
        user: profile || MOCK_USER,
        profile,
        mockMode: true,
        login: () => {},
        logout: () => {},
        updateProfile,
        addTrustedContact,
        removeTrustedContact,
        notifyContacts,
        getToken: async () => 'mock-token',
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

function RealAuthProvider({ children }) {
  // Dynamic import to avoid bundling auth0-react when not needed
  const [Auth0Module, setAuth0Module] = useState(null)

  useEffect(() => {
    import('@auth0/auth0-react').then(setAuth0Module)
  }, [])

  if (!Auth0Module) {
    return <div className="min-h-screen bg-surface-900 flex items-center justify-center text-white">Loading auth...</div>
  }

  const { Auth0Provider } = Auth0Module
  return (
    <Auth0Provider
      domain={AUTH0_DOMAIN}
      clientId={AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: `https://${AUTH0_DOMAIN}/api/v2/`,
      }}
    >
      <Auth0Inner>{children}</Auth0Inner>
    </Auth0Provider>
  )
}

function Auth0Inner({ children }) {
  const [auth0, setAuth0] = useState(null)
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    import('@auth0/auth0-react').then((mod) => setAuth0(mod))
  }, [])

  const auth0Hook = auth0 ? auth0.useAuth0() : null

  useEffect(() => {
    if (auth0Hook?.isAuthenticated) {
      fetchProfile(auth0Hook.getAccessTokenSilently)
    }
  }, [auth0Hook?.isAuthenticated])

  async function fetchProfile(getToken) {
    try {
      const token = await getToken()
      const res = await fetch('/api/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setProfile(await res.json())
    } catch (e) {
      console.error('Failed to fetch profile:', e)
    }
  }

  const makeAuthFetch = useCallback(async (url, options = {}) => {
    if (!auth0Hook) return
    const token = await auth0Hook.getAccessTokenSilently()
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
  }, [auth0Hook])

  const updateProfile = useCallback(async (updates) => {
    const res = await makeAuthFetch('/api/me', {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, ...data }))
    return data
  }, [makeAuthFetch])

  const addTrustedContact = useCallback(async (name, phone) => {
    const res = await makeAuthFetch('/api/me/trusted-contacts', {
      method: 'POST',
      body: JSON.stringify({ name, phone }),
    })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, trusted_contacts: data.contacts }))
    return data
  }, [makeAuthFetch])

  const removeTrustedContact = useCallback(async (index) => {
    const res = await makeAuthFetch(`/api/me/trusted-contacts/${index}`, {
      method: 'DELETE',
    })
    const data = await res.json()
    setProfile((prev) => ({ ...prev, trusted_contacts: data.contacts }))
    return data
  }, [makeAuthFetch])

  const notifyContacts = useCallback(async (riskLevel) => {
    const res = await makeAuthFetch('/api/notify', {
      method: 'POST',
      body: JSON.stringify({ risk_level: riskLevel }),
    })
    return res.json()
  }, [makeAuthFetch])

  if (!auth0Hook) return null

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: auth0Hook.isAuthenticated,
        isLoading: auth0Hook.isLoading,
        user: auth0Hook.user,
        profile,
        mockMode: false,
        login: () => auth0Hook.loginWithRedirect(),
        logout: () => auth0Hook.logout({ logoutParams: { returnTo: window.location.origin } }),
        updateProfile,
        addTrustedContact,
        removeTrustedContact,
        notifyContacts,
        getToken: () => auth0Hook.getAccessTokenSilently(),
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export default function AuthProvider({ children }) {
  if (MOCK_MODE) return <MockAuthProvider>{children}</MockAuthProvider>
  return <RealAuthProvider>{children}</RealAuthProvider>
}
