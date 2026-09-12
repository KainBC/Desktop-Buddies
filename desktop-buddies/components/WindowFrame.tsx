/**
 * Faux desktop-window chrome.
 *
 * Desktop Buddies is a translucent, always-on-top window with sprites
 * pinned to its floor, so framing the page this way is a picture of the
 * product rather than ornament.
 */
export default function WindowFrame({
  title = "Desktop Buddies",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-lg">
      <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-4 py-3">
        <span aria-hidden className="flex gap-1.5">
          <span className="size-3 rounded-full bg-[#ff5f57]" />
          <span className="size-3 rounded-full bg-[#febc2e]" />
          <span className="size-3 rounded-full bg-[#28c840]" />
        </span>
        <span className="flex-1 text-center text-sm font-medium text-muted">
          {title}
        </span>
        {/* Balances the dots so the title sits centred. */}
        <span aria-hidden className="w-[52px]" />
      </div>
      {children}
    </div>
  );
}
