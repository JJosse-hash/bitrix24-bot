"use client";

import { useEffect, useMemo, useState } from "react";
import { Eraser, MapPin, Mic, Pause, Search } from "lucide-react";
import { searchAddress } from "@/src/lib/api";
import type { SearchResponse } from "@/src/types/api";
import { StatusRow } from "@/src/components/StatusRow";
import { MiniMap } from "@/src/components/MiniMap";

const initialText = "universidad por san nicolas cerca del metro que tenga mecatronica";

export default function Home() {
  const [text, setText] = useState(initialText);
  const [listening, setListening] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const top = result?.candidates[0];

  useEffect(() => {
    const handle = window.setTimeout(async () => {
      if (!text.trim()) {
        setResult(null);
        return;
      }
      try {
        setError(null);
        setResult(await searchAddress(text));
      } catch {
        setError("La API no respondió. Puedes seguir escribiendo y reintentar.");
      }
    }, 260);
    return () => window.clearTimeout(handle);
  }, [text]);

  const confidence = useMemo(() => {
    if (!top) return "Sin candidato";
    return `${top.score.toFixed(1)}% · confianza ${top.confidence_label}`;
  }, [top]);

  return (
    <main className="min-h-screen bg-paper">
      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-5 lg:grid-cols-[1fr_28rem]">
        <div className="space-y-5">
          <header className="flex items-center justify-between border-b border-line pb-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">AddressAI México</h1>
              <p className="text-sm text-ink/60">Modo llamada para reconstruir ubicaciones con evidencia parcial.</p>
            </div>
            <button
              className={`inline-flex h-10 items-center gap-2 rounded border px-3 text-sm font-medium ${
                listening ? "border-caution text-caution" : "border-signal text-signal"
              }`}
              onClick={() => setListening(!listening)}
              title={listening ? "Pausar escucha" : "Activar modo llamada"}
            >
              {listening ? <Pause size={18} /> : <Mic size={18} />}
              {listening ? "Pausar" : "Hablar"}
            </button>
          </header>

          <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
            <section className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase text-ink/55">
                <Mic size={16} />
                {listening ? "Escuchando" : "Entrada manual"}
              </div>
              <textarea
                className="min-h-44 w-full resize-none rounded border border-line bg-white p-4 text-lg leading-8 outline-none focus:border-signal"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="¿Dónde está?"
              />
              <div className="flex gap-2">
                <button className="inline-flex items-center gap-2 rounded bg-signal px-3 py-2 text-sm font-medium text-white" onClick={() => void searchAddress(text).then(setResult)}>
                  <Search size={16} />
                  Buscar
                </button>
                <button className="inline-flex items-center gap-2 rounded border border-line px-3 py-2 text-sm" onClick={() => setText("")}>
                  <Eraser size={16} />
                  Limpiar
                </button>
              </div>
              {error && <p className="rounded border border-caution/30 bg-white p-3 text-sm text-caution">{error}</p>}
            </section>

            <section className="bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold uppercase text-ink/55">Interpretación en tiempo real</h2>
              <StatusRow label="Estado" evidence={result?.parsed.state} />
              <StatusRow label="Municipio" evidence={result?.parsed.municipality} />
              <StatusRow label="Colonia" evidence={result?.parsed.neighborhood} />
              <StatusRow label="Calle" evidence={result?.parsed.streets[0] ?? result?.parsed.intersections[0]} />
              <StatusRow label="Número" evidence={result?.parsed.house_number} />
              <StatusRow label="Manzana" evidence={result?.parsed.block} />
              <StatusRow label="Lote" evidence={result?.parsed.lot} />
              <StatusRow label="Referencia" evidence={result?.parsed.poi_categories[0]} />
            </section>
          </div>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase text-ink/55">Candidatos</h2>
            <div className="grid gap-3">
              {result?.candidates.map((item, index) => (
                <article key={item.candidate.id} className="grid gap-2 rounded border border-line bg-white p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-semibold">{index + 1}. {item.candidate.label}</h3>
                      <p className="text-sm text-ink/60">{item.candidate.normalized_address}</p>
                    </div>
                    <span className="rounded bg-signal/10 px-2 py-1 text-sm font-semibold text-signal">{item.score.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 rounded bg-line">
                    <div className="h-2 rounded bg-signal" style={{ width: `${item.score}%` }} />
                  </div>
                  <div className="grid gap-1 text-xs text-ink/65 md:grid-cols-2">
                    {item.breakdown.slice(0, 6).map((reason) => (
                      <span key={`${item.candidate.id}-${reason.signal}-${reason.reason}`}>+{reason.points} {reason.reason}</span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-5 lg:self-start">
          <section className="rounded border border-line bg-white p-4">
            <div className="mb-3 flex items-center gap-2">
              <MapPin size={18} className="text-signal" />
              <h2 className="font-semibold">Resultado</h2>
            </div>
            <p className="mb-3 text-3xl font-semibold">{confidence}</p>
            {top ? <MiniMap lat={top.candidate.point.lat} lon={top.candidate.point.lon} /> : <div className="h-64 rounded border border-line bg-paper" />}
          </section>

          <section className="rounded border border-line bg-white p-4">
            <h2 className="mb-2 font-semibold">Diagnóstico</h2>
            <p className="text-sm text-ink/70">{result?.recommended_question ?? "La evidencia actual no requiere otra pregunta prioritaria."}</p>
            {result?.warnings.map((warning) => (
              <p className="mt-2 text-sm text-caution" key={warning}>{warning}</p>
            ))}
          </section>

          <section className="rounded border border-line bg-white p-4">
            <h2 className="mb-2 font-semibold">Historial local</h2>
            <p className="text-sm text-ink/60">Este MVP no guarda conversaciones en servidor. La sesión vive en memoria del navegador.</p>
          </section>
        </aside>
      </section>
    </main>
  );
}
