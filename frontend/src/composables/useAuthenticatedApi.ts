import { useAuth } from '@clerk/vue'

import { createAuthenticatedApiClient } from '../api/client'

export function useAuthenticatedApi() {
  const { getToken } = useAuth()

  return createAuthenticatedApiClient({
    getToken: () => getToken.value(),
  })
}
