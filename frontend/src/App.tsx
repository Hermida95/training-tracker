import { Route, Routes } from "react-router-dom";
import { TabBar } from "./components/TabBar";
import { useNotificationScheduler } from "./hooks/useNotificationScheduler";
import Progress from "./pages/Progress";
import Settings from "./pages/Settings";
import Today from "./pages/Today";
import Workout from "./pages/Workout";

export default function App() {
  useNotificationScheduler(true);

  return (
    <>
      <Routes>
        <Route path="/" element={<Today />} />
        <Route path="/entreno" element={<Workout />} />
        <Route path="/progreso" element={<Progress />} />
        <Route path="/ajustes" element={<Settings />} />
      </Routes>
      <TabBar />
    </>
  );
}
