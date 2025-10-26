declare module '@met4citizen/talkinghead' {
  type TalkHeadCommonOptions = Record<string, unknown>

  export type TalkingHeadOptions = TalkHeadCommonOptions & {
    cameraView?: 'full' | 'mid' | 'upper' | 'head'
    cameraRotateEnable?: boolean
    cameraPanEnable?: boolean
    cameraZoomEnable?: boolean
    modelPixelRatio?: number
    lightAmbientIntensity?: number
    lightDirectIntensity?: number
    lightSpotIntensity?: number
  }

  export type TalkingHeadShowAvatarOptions = TalkHeadCommonOptions & {
    url: string
    body?: 'M' | 'F' | string
    avatarMood?: string
    cameraView?: 'full' | 'mid' | 'upper' | 'head'
    lipsyncLang?: string
  }

  export class TalkingHead {
    constructor(container: HTMLElement, options?: TalkingHeadOptions)
    showAvatar(options: TalkingHeadShowAvatarOptions): Promise<void>
    stop(): void
    stopSpeaking(): void
    streamStop(): void
    dispose(): void
  }
}
