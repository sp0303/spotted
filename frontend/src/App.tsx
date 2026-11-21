import { Link, Route, Routes } from "react-router-dom";
import StartPage from "./pages/StartPage";
import ProfilePage from "./pages/ProfilePage";
import ChecksPage from "./pages/ChecksPage";

export default function App() {
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand" aria-label="Spotted home">
          <span className="brand-dot" aria-hidden="true" />
          Spotted
        </Link>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<StartPage />} />
          <Route path="/b/:id" element={<ProfilePage />} />
          <Route path="/b/:id/checks" element={<ChecksPage />} />
          <Route path="*" element={<p>Page not found. <Link to="/">Start again</Link></p>} />
        </Routes>
      </main>
    </>
  );
}
