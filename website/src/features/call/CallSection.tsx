import { ConversationProvider } from '@elevenlabs/react';

import { CallBox } from '@/features/call/CallBox';

/** Loaded lazily: the ElevenLabs SDK is most of the site's JavaScript. */
export default function CallSection() {
  return (
    <ConversationProvider>
      <CallBox />
    </ConversationProvider>
  );
}
