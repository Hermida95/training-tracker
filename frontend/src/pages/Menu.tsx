import { useEffect, useRef, useState } from "react";
import { menuApi } from "../api/menu";
import type { MenuDocument } from "../types";

const MAX_FILE_BYTES = 8 * 1024 * 1024;

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  return `${Math.max(1, Math.round(bytes / 1024))}KB`;
}

/** Imagen del menú cargada con fetch autenticado (un <img src> normal no
 *  puede mandar el token). El object URL se libera al desmontar. */
function MenuImage({ menuId, title }: { menuId: number; title: string }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked: string | null = null;
    menuApi.fetchFileUrl(menuId).then((u) => {
      revoked = u;
      setUrl(u);
    });
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [menuId]);

  if (!url) return <p className="empty-state">Cargando imagen…</p>;
  return <img className="menu-image" src={url} alt={title} />;
}

export default function Menu() {
  const [menus, setMenus] = useState<MenuDocument[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = () => menuApi.list().then(setMenus);
  useEffect(() => {
    load();
  }, []);

  const upload = async () => {
    if (!title.trim() || (!file && !text.trim())) return;
    if (file && file.size > MAX_FILE_BYTES) {
      setError("El fichero supera el máximo de 8MB.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await menuApi.upload(title.trim(), file, text.trim() || null);
      setTitle("");
      setFile(null);
      setText("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch {
      setError("No se pudo subir el menú. ¿Formato JPG/PNG/WebP/PDF y menos de 8MB?");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (menu: MenuDocument) => {
    if (!window.confirm(`¿Borrar "${menu.title}"?`)) return;
    await menuApi.remove(menu.id);
    if (expandedId === menu.id) setExpandedId(null);
    await load();
  };

  const openPdf = async (menu: MenuDocument) => {
    const url = await menuApi.fetchFileUrl(menu.id);
    window.open(url, "_blank", "noopener");
    // El navegador mantiene el blob mientras la pestaña nueva lo usa;
    // liberamos pasado un margen para no acumular memoria.
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  return (
    <div>
      <div className="top-bar">
        <h1>Menú</h1>
      </div>
      <main>
        <div className="card">
          <h2>Mis menús</h2>
          {menus.length === 0 && (
            <p className="empty-state">
              Sube aquí tu plan de comidas (foto, PDF o texto) y tenlo siempre a mano.
            </p>
          )}
          {menus.map((menu) => (
            <div className="menu-row" key={menu.id}>
              <div className="menu-row-head">
                <div className="info">
                  <span>{menu.title}</span>
                  <span className="streak">
                    {menu.created_at.slice(0, 10)}
                    {menu.content_type ? ` · ${formatSize(menu.file_size)}` : " · texto"}
                  </span>
                </div>
                <div className="btn-row" style={{ flexShrink: 0 }}>
                  {menu.content_type === "application/pdf" ? (
                    <button onClick={() => openPdf(menu)}>Abrir PDF</button>
                  ) : (
                    <button
                      onClick={() => setExpandedId(expandedId === menu.id ? null : menu.id)}
                    >
                      {expandedId === menu.id ? "Ocultar" : "Ver"}
                    </button>
                  )}
                  <button className="danger" onClick={() => remove(menu)}>
                    Borrar
                  </button>
                </div>
              </div>

              {expandedId === menu.id && (
                <div className="menu-detail">
                  {menu.content_type?.startsWith("image/") && (
                    <MenuImage menuId={menu.id} title={menu.title} />
                  )}
                  {menu.text_content && <pre className="menu-text">{menu.text_content}</pre>}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="card">
          <h2>Subir menú</h2>
          <label>Título</label>
          <input
            type="text"
            placeholder="Menú de agosto"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          <label style={{ marginTop: 10, display: "block" }}>Foto o PDF</label>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />

          <label style={{ marginTop: 10, display: "block" }}>O pégalo como texto</label>
          <textarea
            rows={4}
            placeholder={"Lunes: pollo con arroz\nMartes: salmón con verduras…"}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

          <button
            className="primary big"
            style={{ marginTop: 12 }}
            onClick={upload}
            disabled={saving || !title.trim() || (!file && !text.trim())}
          >
            {saving ? "Subiendo…" : "Guardar menú"}
          </button>
        </div>
      </main>
    </div>
  );
}
