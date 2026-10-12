import { Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import AddRecordPage from "./pages/AddRecordPage";
import CratePage from "./pages/CratePage";
import LabelMakerPage from "./pages/LabelMakerPage";
import LabelPage from "./pages/LabelPage";
import LibraryPage from "./pages/LibraryPage";
import NotFoundPage from "./pages/NotFoundPage";
import RecordPage from "./pages/RecordPage";
import SearchPage from "./pages/SearchPage";
import SettingsPage from "./pages/SettingsPage";
import TagManagerPage from "./pages/TagManagerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<LibraryPage defaultStatus="owned" />} />
        <Route path="wantlist" element={<LibraryPage defaultStatus="wantlist" />} />
        <Route path="crate" element={<CratePage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="add" element={<AddRecordPage />} />
        <Route path="records/:id" element={<RecordPage />} />
        <Route path="records/:id/label" element={<LabelPage />} />
        <Route path="labels" element={<LabelMakerPage />} />
        <Route path="tags" element={<TagManagerPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
