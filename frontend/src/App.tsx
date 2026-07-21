import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { TabBar } from "./components/TabBar";
import { useNotificationScheduler } from "./hooks/useNotificationScheduler";
import Login from "./pages/Login";
import Progress from "./pages/Progress";
import Settings from "./pages/Settings";
import Today from "./pages/Today";
import Workout from "./pages/Workout";

export default function App() {
  const { user, loading } = useAuth();

  // La alarma antisedentarismo solo se programa con sesión iniciada
  // (el service worker necesita el token para registrar las pausas).
  useNotificationScheduler(user !== null);

  if (loading) {
    return <div className="login-screen" />;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<Today />} />
        <Route path="/entreno" element={<Workout />} />
        <Route path="/progreso" element={<Progress />} />
        <Route path="/ajustes" element={<Settings />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
      </Routes>
      <TabBar />
    </>
  );
}
