import MapView from "@/components/MapView";

export const metadata = { title: "Maps · Flock ALPR × Demographics" };

export default function MapsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-ink">Maps</h1>
        <p className="max-w-3xl leading-7 text-slate-600">
          Census tracts shaded by Hispanic/Latino share or by camera density,
          with Flock camera locations, retailers and day-labor candidates as
          toggleable layers. Switch counties with the buttons.
        </p>
      </header>
      <MapView />
    </div>
  );
}
