import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoggerProvider } from "@/context/LoggerContext";
import { LabBlogPage } from "@/pages/AnthropicPage";
import { ApiDocsPage } from "@/pages/ApiDocsPage";
import { AppsPage } from "@/pages/AppsPage";
import ArxivSearch from "@/pages/ArxivSearch";
import { ChatPage } from "@/pages/ChatPage";
import { Dashboard } from "@/pages/Dashboard";
import { Depot } from "@/pages/Depot";
import { DepotSemantic } from "@/pages/DepotSemantic";
import { Favorites } from "@/pages/Favorites";
import { HelpPage } from "@/pages/HelpPage";
import { LogsPage } from "@/pages/LogsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SkillsPage } from "@/pages/SkillsPage";
import SweepsPage from "@/pages/SweepsPage";
import { ToolsPage } from "@/pages/ToolsPage";

export default function App() {
  return (
    <LoggerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="search" element={<ArxivSearch />} />
            <Route path="sweeps" element={<SweepsPage />} />
            <Route path="semantic" element={<DepotSemantic />} />
            <Route path="depot" element={<Depot />} />
            <Route path="favorites" element={<Favorites />} />
            <Route path="tools" element={<ToolsPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="skills" element={<SkillsPage />} />
            <Route path="swagger" element={<ApiDocsPage />} />
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
