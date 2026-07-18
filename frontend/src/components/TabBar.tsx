import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "Hoy", icon: "☀️" },
  { to: "/entreno", label: "Entreno", icon: "🏋️" },
  { to: "/progreso", label: "Progreso", icon: "📈" },
  { to: "/ajustes", label: "Ajustes", icon: "⚙️" },
];

export function TabBar() {
  return (
    <nav className="tabbar">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
          <span className="icon">{tab.icon}</span>
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
