import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { bodyMetricsApi } from "../api/bodyMetrics";
import { statsApi } from "../api/stats";
import { Stepper } from "../components/Stepper";
import type { MonthlyStats, WeeklyAveragePoint } from "../types";
import { todayIsoMadrid as todayIso } from "../utils/date";

export default function Progress() {
  const [weeks, setWeeks] = useState<WeeklyAveragePoint[]>([]);
  const [stats, setStats] = useState<MonthlyStats | null>(null);
  const [weight, setWeight] = useState<number | null>(null);
  const [waist, setWaist] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);

  const load = () => {
    bodyMetricsApi.weeklyAverage().then(setWeeks);
    const now = new Date();
    statsApi.monthly(now.getFullYear(), now.getMonth() + 1).then(setStats);
  };

  useEffect(load, []);

  const saveMetric = async () => {
    if (weight === null && waist === null) return;
    await bodyMetricsApi.upsert(todayIso(), weight, waist);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
    load();
  };

  const now = new Date();
  const chartData = weeks.map((w) => ({
    week: w.week_start.slice(5),
    peso: w.avg_weight_kg,
    cintura: w.avg_waist_cm,
  }));

  return (
    <div>
      <div className="top-bar">
        <h1>Progreso</h1>
      </div>
      <main>
        <div className="card">
          <h2>Registro rápido de hoy</h2>
          <div className="btn-row">
            <div style={{ flex: 1 }}>
              <label>Peso (kg)</label>
              <Stepper value={weight} step={0.1} suffix="kg" onChange={setWeight} />
            </div>
            <div style={{ flex: 1 }}>
              <label>Cintura (cm)</label>
              <Stepper value={waist} step={0.5} suffix="cm" onChange={setWaist} />
            </div>
          </div>
          <button className="primary big" style={{ marginTop: 12 }} onClick={saveMetric}>
            {saved ? "Guardado ✅" : "Guardar medición"}
          </button>
        </div>

        <div className="card">
          <h2>Media semanal</h2>
          {chartData.length === 0 ? (
            <p className="empty-state">Aún no hay mediciones suficientes.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="week" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                  }}
                />
                <Line type="monotone" dataKey="peso" stroke="#4ade80" strokeWidth={2} dot={false} />
                <Line
                  type="monotone"
                  dataKey="cintura"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {stats && (
          <div className="card">
            <h2>Resumen de {String(now.getMonth() + 1).padStart(2, "0")}/{now.getFullYear()}</h2>
            <p>Sesiones completadas: {stats.sessions_completed}</p>
            <p>Media de pasos: {stats.avg_steps ?? "sin datos"}</p>
            <p>
              Tendencia de peso:{" "}
              {stats.weight_trend_kg !== null ? `${stats.weight_trend_kg > 0 ? "+" : ""}${stats.weight_trend_kg}kg` : "sin datos"}
            </p>
            <p>
              Pausas activas: {stats.breaks_done}/{stats.breaks_total}
            </p>
            <p>Cumplimiento de hábitos: {Math.round(stats.habit_completion_rate * 100)}%</p>
            <p>
              Puntos del mes: <strong>{stats.points_total}</strong> · {stats.perfect_days}{" "}
              {stats.perfect_days === 1 ? "día perfecto" : "días perfectos"} ⭐
            </p>

            <div className="btn-row" style={{ marginTop: 12 }}>
              <a
                href={statsApi.exportTextUrl(now.getFullYear(), now.getMonth() + 1)}
                target="_blank"
                rel="noreferrer"
              >
                <button style={{ width: "100%" }}>Exportar (texto)</button>
              </a>
              <a
                href={statsApi.exportJsonUrl(now.getFullYear(), now.getMonth() + 1)}
                target="_blank"
                rel="noreferrer"
              >
                <button style={{ width: "100%" }}>Exportar (JSON)</button>
              </a>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
