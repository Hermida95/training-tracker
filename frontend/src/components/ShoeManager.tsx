import { useEffect, useState } from "react";
import { workoutsApi } from "../api/workouts";
import type { Shoe } from "../types";

export function ShoeManager() {
  const [shoes, setShoes] = useState<Shoe[]>([]);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => workoutsApi.shoes().then(setShoes);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await workoutsApi.createShoe(name.trim());
      setName("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al añadir las zapatillas");
    } finally {
      setSaving(false);
    }
  };

  const toggleRetired = async (shoe: Shoe) => {
    await workoutsApi.updateShoe(shoe.id, { retired: !shoe.retired });
    await load();
  };

  const remove = async (shoe: Shoe) => {
    if (!window.confirm(`¿Borrar "${shoe.name}"? Los rodajes ya registrados con ellas no cambian.`))
      return;
    await workoutsApi.deleteShoe(shoe.id);
    await load();
  };

  return (
    <div className="card">
      <h2>Mis zapatillas</h2>
      <p style={{ fontSize: "0.82rem" }}>
        Añade tus pares de running para poder elegir con cuáles corres cada rodaje.
      </p>

      {shoes.map((shoe) => (
        <div className="habit-manage-row" key={shoe.id}>
          <div className="habit-manage-head">
            <div className="info">
              <span>{shoe.name}</span>
              {shoe.retired && <span className="streak">retiradas</span>}
            </div>
            <div className="btn-row" style={{ gap: 6 }}>
              <button
                style={{ minHeight: 40, padding: "6px 12px" }}
                onClick={() => toggleRetired(shoe)}
              >
                {shoe.retired ? "Reactivar" : "Retirar"}
              </button>
              <button
                className="danger"
                style={{ minHeight: 40, padding: "6px 12px" }}
                onClick={() => remove(shoe)}
                aria-label={`Borrar ${shoe.name}`}
              >
                Borrar
              </button>
            </div>
          </div>
        </div>
      ))}

      <div className="habit-create-form">
        <h2 style={{ marginTop: 16 }}>Nuevas zapatillas</h2>
        <label>Nombre</label>
        <input
          type="text"
          placeholder="Salomon Ultra Glide"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        <button
          className="primary big"
          style={{ marginTop: 12 }}
          onClick={create}
          disabled={saving || !name.trim()}
        >
          {saving ? "Añadiendo…" : "Añadir zapatillas"}
        </button>
      </div>
    </div>
  );
}
