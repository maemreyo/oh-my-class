/**
 * Google Forms API — OAuth 2.0 setup (one-time flow).
 *
 * Required scopes:
 *   - https://www.googleapis.com/auth/forms.body
 *   - https://www.googleapis.com/auth/drive.file
 *
 * Setup steps:
 *   1. Create OAuth 2.0 credentials in Google Cloud Console
 *   2. Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET in .env
 *   3. Call getAuthUrl() to get the consent URL
 *   4. User visits the URL and approves
 *   5. Exchange the code from the callback for tokens via exchangeCode()
 *   6. Store the refresh token securely (GOOGLE_REFRESH_TOKEN in .env)
 */

export interface GoogleOAuthConfig {
  clientId:     string
  clientSecret: string
  redirectUri:  string
}

export interface GoogleTokens {
  accessToken:  string
  refreshToken?: string
  expiresAt:    number   // Unix ms
}

const SCOPES = [
  'https://www.googleapis.com/auth/forms.body',
  'https://www.googleapis.com/auth/drive.file',
]

export function getAuthUrl(config: GoogleOAuthConfig): string {
  const params = new URLSearchParams({
    client_id:     config.clientId,
    redirect_uri:  config.redirectUri,
    response_type: 'code',
    scope:         SCOPES.join(' '),
    access_type:   'offline',
    prompt:        'consent',
  })
  return `https://accounts.google.com/o/oauth2/v2/auth?${params}`
}

export async function exchangeCode(
  config: GoogleOAuthConfig,
  code: string,
): Promise<GoogleTokens> {
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id:     config.clientId,
      client_secret: config.clientSecret,
      redirect_uri:  config.redirectUri,
      grant_type:    'authorization_code',
    }),
  })
  const data = await res.json() as { access_token: string; refresh_token?: string; expires_in: number }
  return {
    accessToken:  data.access_token,
    refreshToken: data.refresh_token,
    expiresAt:    Date.now() + data.expires_in * 1000,
  }
}

export async function refreshAccessToken(
  config: GoogleOAuthConfig,
  refreshToken: string,
): Promise<GoogleTokens> {
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      refresh_token: refreshToken,
      client_id:     config.clientId,
      client_secret: config.clientSecret,
      grant_type:    'refresh_token',
    }),
  })
  const data = await res.json() as { access_token: string; expires_in: number }
  return {
    accessToken: data.access_token,
    refreshToken,
    expiresAt:   Date.now() + data.expires_in * 1000,
  }
}
