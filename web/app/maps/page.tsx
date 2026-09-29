import MapView from "@/components/MapView";

export const metadata = { title: "Maps · Flock ALPR × Demographics" };

export default function MapsPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-rule pb-8">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Interactive</p>
        <h1 className="mt-4 font-serif text-4xl font-semibold leading-tight tracking-[-0.015em] text-ink">Maps</h1>
        <p className="mt-4 max-w-measure font-serif text-lg leading-8 text-slate-600">
          Census tracts shaded by Hispanic/Latino share or by camera density,
          with Flock camera locations, retailers and day-labor candidates as
          toggleable layers. Switch counties with the buttons.
        </p>
      </header>
      <MapView />
    </div>
  );
}
