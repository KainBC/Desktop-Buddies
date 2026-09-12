import { GITHUB_URL } from "@/lib/links";

export default function Footer() {
  return (
    <footer className="border-t border-border py-8 text-sm text-muted">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6">
        <span>Desktop Buddies — an open-source desktop pet for friends.</span>
        <a href={GITHUB_URL} className="underline hover:text-foreground">
          GitHub
        </a>
      </div>
    </footer>
  );
}
