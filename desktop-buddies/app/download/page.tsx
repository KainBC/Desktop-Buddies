import type { Metadata } from "next";
import Link from "next/link";
import DownloadButton from "@/components/DownloadButton";
import Footer from "@/components/Footer";
import WindowFrame from "@/components/WindowFrame";
import { BUILDS, CHECKSUMS_URL, buildName, primaryBuild } from "@/lib/downloads";
import { GITHUB_URL } from "@/lib/links";

export const metadata: Metadata = {
  title: "Download — Desktop Buddies",
  description:
    "Download Desktop Buddies for macOS, Windows or Linux.",
};

const SETUP = `git clone ${GITHUB_URL}.git
cd Desktop-Buddies
./run.sh setup
./run.sh client`;

export default function Download() {
  return (
    <>
      <main className="mx-auto max-w-5xl px-6 pt-12 pb-16">
        <WindowFrame title="Download">
          <div className="px-6 py-12 text-center sm:px-12">
            <h1 className="mb-8 text-3xl font-bold tracking-tight">
              Get Desktop Buddies
            </h1>
            <DownloadButton />
          </div>
        </WindowFrame>

        <section id="all-platforms" className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">All platforms</h2>
          <ul className="divide-y divide-border rounded-lg border border-border">
            {BUILDS.map((build) => (
              <li
                key={buildName(build)}
                className="flex items-center justify-between gap-4 px-5 py-4"
              >
                <span>
                  <span className="font-medium">{buildName(build)}</span>{" "}
                  <span className="text-sm text-muted">{build.file}</span>
                </span>
                {build.url ? (
                  <a
                    href={build.url}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-contrast hover:opacity-90"
                  >
                    Download
                  </a>
                ) : (
                  <span className="text-sm text-muted">Coming soon</span>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section id="first-launch" className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">First launch</h2>
          <p className="mb-6 text-muted">
            The apps aren&apos;t code-signed yet — signing certificates cost
            money, and the source is public on GitHub — so your OS asks you to
            confirm the first time. After that it opens like any other app.
          </p>
          <div className="grid gap-6 sm:grid-cols-3">
            {(["macos", "windows", "linux"] as const).map((platform) => {
              const build = primaryBuild(platform)!;
              return (
                <div key={platform}>
                  <h3 className="mb-2 font-semibold">{build.label}</h3>
                  <ol className="list-decimal space-y-1 pl-5 text-sm text-muted">
                    {build.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              );
            })}
          </div>
          <p className="mt-6 text-sm text-muted">
            Want to verify your download?{" "}
            <a href={CHECKSUMS_URL} className="underline hover:text-foreground">
              SHA-256 checksums
            </a>
            .
          </p>
        </section>

        <section className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">Run from source</h2>
          <p className="mb-4 text-muted">
            Prefer to run the Python directly? You need Python 3.11 or newer.
          </p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-surface p-5 font-mono text-sm">
            <code>{SETUP}</code>
          </pre>
          <p className="mt-4 text-muted">
            It connects to the hosted relay by default. To self-host, start a
            relay with{" "}
            <code className="font-mono text-sm">./run.sh relay</code> and point
            clients at it with{" "}
            <code className="font-mono text-sm">BUDDIES_URL</code>, for example{" "}
            <code className="font-mono text-sm">
              BUDDIES_URL=ws://localhost:8765 ./run.sh client
            </code>
            .
          </p>
        </section>

        <section className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">Notes</h2>
          <ul className="list-disc space-y-2 pl-5 text-muted">
            <li>
              The global hotkey is ⌘⇧B on macOS and Ctrl+Shift+B elsewhere. It
              opens the chat input for your buddy; clicking your own buddy does
              the same.
            </li>
            <li>
              Set <code className="font-mono text-sm">BUDDIES_NO_HOTKEY=1</code>{" "}
              to opt out of the global hotkey.
            </li>
            <li>
              Source and issues live on{" "}
              <a href={GITHUB_URL} className="underline hover:text-foreground">
                GitHub
              </a>
              .
            </li>
          </ul>
        </section>

        <p className="pt-12">
          <Link href="/" className="text-muted underline hover:text-foreground">
            ← Back to the landing page
          </Link>
        </p>
      </main>
      <Footer />
    </>
  );
}
