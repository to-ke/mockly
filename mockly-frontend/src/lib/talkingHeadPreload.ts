import avatarModelUrl from '@/assets/avatar.glb?url'

let preloadPromise: Promise<void> | null = null

export const defaultTalkingHeadModelUrl = avatarModelUrl

export function preloadTalkingHeadModel(url: string = avatarModelUrl) {
  if (preloadPromise || typeof window === 'undefined') {
    return preloadPromise ?? Promise.resolve()
  }
  preloadPromise = fetch(url, { cache: 'force-cache' })
    .then((response) => {
      if (!response.ok) throw new Error(`Failed to preload avatar: ${response.statusText}`)
      return response.blob()
    })
    .then(() => undefined)
    .catch((error) => {
      preloadPromise = null
      throw error
    })
  return preloadPromise
}
