import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoggerProvider } from "@/context/LoggerContext";
import { Dashboard } from "@/pages/Dashboard";
import { ArxivSearch } from "@/pages/ArxivSearch";
import { DepotSemantic } from "@/pages/DepotSemantic";
import { Depot } from "@/pages/Depot";
import { Favorites } from "@/pages/Favorites";
import { LabBlogPage } from "@/pages/AnthropicPage";
import { ToolsPage } from "@/pages/ToolsPage";
import { AppsPage } from "@/pages/AppsPage";
import { HelpPage } from "@/pages/HelpPage";
import { SettingsPage } from "@/pages/SettingsPage";

export default function App() {
  return (
    <LoggerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="search" element={<ArxivSearch />} />
            <Route path="semantic" element={<DepotSemantic />} />
            <Route path="depot" element={<Depot />} />
            <Route path="favorites" element={<Favorites />} />
            <Route path="tools" element={<ToolsPage />} />
            <Route path="anthropic" element={<LabBlogPage />} />
            <Route path="apps" element={<AppsPage />} />
            <Route path="help" element={<HelpPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LoggerProvider>
  );
}
