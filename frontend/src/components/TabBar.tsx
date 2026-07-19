import { NavLink } from "react-router-dom";
import { BarbellIcon, SlidersIcon, SunIcon, TrendIcon } from "./icons";

const TABS = [
  { to: "/", label: "Hoy", icon: <SunIcon /> },
  { to: "/entreno", label: "Entreno", icon: <BarbellIcon /> },
  { to: "/progreso", label: "Progreso", icon: <TrendIcon /> },
  { to: "/ajustes", label: "Ajustes", icon: <SlidersIcon /> },
];

export function TabBar() {
  return (
    <nav className="tabbar">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === "/"}
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          <span className="icon">{tab.icon}</span>
          <span>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
