import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { Working } from "../components/Spinner";

export default function StartPage() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const stored = await api.extractProfile(url.trim());
      navigate(`/b/${stored.business_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  }

  return (
    <section className="hero">
      <h1>Did AI spot your business?</h1>
      <p className="lede">
        Enter your website. We'll read it, show you what we found, and check whether search engines and AI
        assistants can reach it.
      </p>
      <form onSubmit={submit} className="url-form">
        <label htmlFor="url" className="visually-hidden">
          Your website
        </label>
        <input
          id="url"
          type="text"
          inputMode="url"
          autoComplete="url"
          placeholder="yourbusiness.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={busy}
          required
        />
        <button type="submit" className="primary" disabled={busy || !url.trim()}>
          {busy ? "Reading…" : "Check my business"}
        </button>
      </form>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {busy && (
        <Working
          steps={[
            "Opening your website",
            "Reading your homepage and key pages",
            "Finding your services, locations and contact details",
            "Preparing your profile for you to check",
          ]}
        />
      )}
    </section>
  );
}
