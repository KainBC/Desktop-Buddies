import Link from "next/link";
import BuddyStage from "@/components/BuddyStage";
import FeatureCard from "@/components/FeatureCard";
import Footer from "@/components/Footer";
import Steps from "@/components/Steps";
import WindowFrame from "@/components/WindowFrame";
import { framePath } from "@/lib/characters";
import { GITHUB_URL } from "@/lib/links";

export default function Home() {
  return (
    <>
      <main>
        <section className="mx-auto max-w-5xl px-6 pt-12 pb-16">
          <WindowFrame>
            <div className="px-6 pt-12 text-center sm:px-12">
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
                Your friends live on your desktop
              </h1>
              <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
                Share a room code and everyone&apos;s buddy walks around on
                everyone&apos;s screen.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Link
                  href="/download"
                  className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-contrast hover:opacity-90"
                >
                  Download
                </Link>
                <a
                  href={GITHUB_URL}
                  className="rounded-md border border-border px-5 py-2.5 font-medium hover:bg-surface-2"
                >
                  GitHub
                </a>
              </div>
              <p className="mt-10 text-sm text-muted">Click a buddy.</p>
            </div>
            <BuddyStage />
          </WindowFrame>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <h2 className="mb-4 text-2xl font-semibold">What it is</h2>
          <p className="max-w-2xl text-lg leading-relaxed text-muted">
            Desktop Buddies puts a small animated character on your desktop
            that wanders around while you work. Join a room with friends and
            their characters appear on your screen too, moving in real time.
          </p>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <h2 className="sr-only">Features</h2>
          <div className="grid gap-6 sm:grid-cols-3">
            <FeatureCard
              sprite={framePath("placeholder_blob", "walk", 0)}
              title="They wander"
            >
              Each buddy idles and walks along the bottom of the screen on its
              own, in a small frameless window that stays on top without
              covering your screen.
            </FeatureCard>
            <FeatureCard
              sprite={framePath("placeholder_cat", "idle", 0)}
              title="Chat bubbles"
            >
              Press the global hotkey or click your buddy to type; what you
              send appears as a bubble over your character on everyone&apos;s
              desktop.
            </FeatureCard>
            <FeatureCard
              sprite={framePath("placeholder_dog", "walk", 2)}
              title="Your own room"
            >
              Share a short code and your buddies appear on each other&apos;s
              desktops. No accounts and no sign-up — just a
              short code.
            </FeatureCard>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-16">
          <h2 className="mb-6 text-2xl font-semibold">How it works</h2>
          <Steps />
        </section>

        <section className="mx-auto max-w-5xl px-6 pb-20 text-center">
          <Link
            href="/download"
            className="inline-block rounded-md bg-accent px-6 py-3 font-medium text-accent-contrast hover:opacity-90"
          >
            Get Desktop Buddies
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
