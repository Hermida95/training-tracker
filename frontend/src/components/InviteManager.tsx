import { useEffect, useState } from "react";
import { invitesApi } from "../api/auth";
import type { InviteCode } from "../types";

export function InviteManager() {
  const [invites, setInvites] = useState<InviteCode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const load = () => invitesApi.list().then(setInvites);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setError(null);
    try {
      await invitesApi.create();
      await load();
    } catch (e) {
      const raw = e instanceof Error ? e.message : "";
      setError(
        raw.includes("409")
          ? "Ya tienes 5 invitaciones sin usar. Comparte esas primero."
          : "No se pudo generar la invitación."
      );
    }
  };

  const copy = async (invite: InviteCode) => {
    await navigator.clipboard.writeText(invite.code);
    setCopiedId(invite.id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="card">
      <h2>Invitaciones</h2>
      <p style={{ fontSize: "0.82rem" }}>
        El registro está cerrado: solo entra quien tenga un código. Genera uno y compárteselo a
        quien quieras invitar (un solo uso por código).
      </p>

      {invites.map((invite) => (
        <div className="invite-row" key={invite.id}>
          <code className={`invite-code ${invite.used_at ? "used" : ""}`}>{invite.code}</code>
          {invite.used_at ? (
            <span className="streak">usada</span>
          ) : (
            <button
              style={{ minHeight: 40, padding: "6px 14px" }}
              onClick={() => copy(invite)}
            >
              {copiedId === invite.id ? "Copiada ✓" : "Copiar"}
            </button>
          )}
        </div>
      ))}

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

      <button className="primary" style={{ width: "100%", marginTop: 12 }} onClick={create}>
        Generar invitación
      </button>
    </div>
  );
}
