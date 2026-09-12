export default function FeatureCard({
  sprite,
  title,
  children,
}: {
  sprite: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={sprite}
        alt=""
        width={48}
        height={48}
        className="pixelated mb-4"
      />
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}
