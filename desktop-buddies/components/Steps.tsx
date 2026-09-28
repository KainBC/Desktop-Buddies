const STEPS = [
  {
    title: "Install it",
    body: "Download it for macOS, Windows or Linux.",
  },
  {
    title: "Share a room code",
    body: "One person creates a room and sends the short code to friends.",
  },
  {
    title: "They show up",
    body: "Everyone's buddy appears and wanders on everyone else's screen.",
  },
];

export default function Steps() {
  return (
    <ol className="grid gap-6 sm:grid-cols-3">
      {STEPS.map((step, i) => (
        <li key={step.title}>
          <span className="mb-3 flex size-8 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-contrast">
            {i + 1}
          </span>
          <h3 className="mb-1 font-semibold">{step.title}</h3>
          <p className="text-sm leading-relaxed text-muted">{step.body}</p>
        </li>
      ))}
    </ol>
  );
}
