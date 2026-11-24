/** The call-to-action. Kept apart from the ElevenLabs SDK so the page can show it before the SDK loads. */
export function TalkButton({ onClick }: { onClick: () => void }) {
  return (
    <>
      <button
        type="button"
        onClick={onClick}
        className="flex items-center gap-3 rounded-full bg-azulejo-600 px-7 py-3.5 font-display text-lg text-white transition hover:bg-azulejo-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-azulejo-600"
      >
        <MicIcon />
        Talk to Tasca
      </button>
      <p className="text-sm text-azulejo-600 italic">
        “I’d like to book a table for tomorrow at 8pm”
      </p>
    </>
  );
}

function MicIcon() {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0M12 17v4M8 21h8" />
    </svg>
  );
}
