import "./App.css";

import { useMemo, useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:7071/api";

export default function App() {
  const [file, setFile] = useState(null);
  const [classId, setClassId] = useState(1);
  const [threshold, setThreshold] = useState(0.35);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [data, setData] = useState(null);

  const [localPreview, setLocalPreview] = useState("");

  const matched = useMemo(() => {
    const reco = data?.recognition;
    return (reco?.results || []).filter((r) => r.match);
  }, [data]);

  async function uploadImage(selectedFile) {
    const bytes = await selectedFile.arrayBuffer();
    const res = await axios.post(`${API_BASE}/UploadImage`, bytes, {
      headers: { "Content-Type": selectedFile.type || "image/jpeg" },
      timeout: 120000,
    });
    return res.data.image_url;
  }

  async function runPipeline(groupUrl) {
    const payload = {
      class_id: Number(classId),
      image_url: groupUrl,
      threshold: Number(threshold),
      request_id: `web-${Date.now()}`,
    };

    const res = await axios.post(`${API_BASE}/RunAttendancePipeline`, payload, {
      headers: { "Content-Type": "application/json" },
      timeout: 300000,
    });
    return res.data;
  }

  const onPickFile = (f) => {
    setFile(f);
    setData(null);
    setError("");
    setImageUrl("");
    if (localPreview) URL.revokeObjectURL(localPreview);
    if (f) setLocalPreview(URL.createObjectURL(f));
  };

  const onRun = async () => {
    setError("");
    setData(null);

    if (!file) {
      setError("Choisis une photo de groupe d’abord.");
      return;
    }

    try {
      setLoading(true);

      const url = await uploadImage(file);
      setImageUrl(url);

      const result = await runPipeline(url);
      setData(result);
    } catch (e) {
      setError(e?.response?.data?.error || e.message || "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const reco = data?.recognition;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">CA</div>
          <div>
            <h1>Cloud Attendance</h1>
            <p>Photo de groupe → reconnaissance → PDF → email (1 clic)</p>
          </div>
        </div>

        <div className="pill">
          <span className="dot" />
          <span>Local</span>
          <span className="muted">{API_BASE}</span>
        </div>
      </header>

      <main className="grid">
        {/* LEFT: Upload + Settings */}
        <section className="card">
          <h2>Nouvelle prise</h2>

          <div className="fieldRow">
            <div className="field">
              <label>Class ID</label>
              <input
                type="number"
                value={classId}
                onChange={(e) => setClassId(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Threshold</label>
              <input
                type="number"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
              />
            </div>
          </div>

          <div className="upload">
            <input
              id="file"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => onPickFile(e.target.files?.[0] || null)}
            />
            <label className="uploadBox" htmlFor="file">
              <div className="uploadIcon">📸</div>
              <div>
                <div className="uploadTitle">
                  {file ? file.name : "Choisir une photo de groupe"}
                </div>
                <div className="uploadSub">
                  JPG/PNG — caméra ou fichier
                </div>
              </div>
              <div className="uploadBtn">Parcourir</div>
            </label>

            {localPreview && (
              <div className="preview">
                <img src={localPreview} alt="Preview" />
              </div>
            )}
          </div>

          {error && <div className="alert error">⚠️ {error}</div>}

          <button className="primary" onClick={onRun} disabled={loading}>
            {loading ? "Traitement..." : "✅ Lancer la présence"}
          </button>

          <div className="links">
            {imageUrl && (
              <a href={imageUrl} target="_blank" rel="noreferrer">
                Ouvrir l’image Blob →
              </a>
            )}
          </div>
        </section>

        {/* RIGHT: Results */}
        <section className="card">
          <div className="cardHeader">
            <h2>Résultats</h2>
            {data?.email?.sendgrid_status && (
              <span className="badge">
                Email: {data.email.sendgrid_status}
              </span>
            )}
          </div>

          {!data ? (
            <div className="empty">
              <div className="emptyIcon">📊</div>
              <div>
                <div className="emptyTitle">Aucun résultat</div>
                <div className="muted">
                  Lance une prise pour générer présence + PDF + email.
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="kpis">
                <div className="kpi">
                  <div className="kpiLabel">Faces détectés</div>
                  <div className="kpiValue">{reco?.faces_detected ?? "-"}</div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Total</div>
                  <div className="kpiValue">{reco?.total_students ?? "-"}</div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Présents</div>
                  <div className="kpiValue">{reco?.present_count ?? "-"}</div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Taux</div>
                  <div className="kpiValue">{reco?.attendance_percentage ?? "-"}%</div>
                </div>
              </div>

              <div className="rowBetween">
                <h3>Étudiants présents</h3>
                {data.pdf_url && (
                  <a className="linkBtn" href={data.pdf_url} target="_blank" rel="noreferrer">
                    Ouvrir PDF →
                  </a>
                )}
              </div>

              {matched.length === 0 ? (
                <div className="alert">Aucun étudiant reconnu.</div>
              ) : (
                <ul className="list">
                  {matched.map((r, idx) => (
                    <li key={idx} className="listItem">
                      <div className="avatar">
                        {(r.student?.first_name?.[0] || "S").toUpperCase()}
                      </div>
                      <div className="who">
                        <div className="name">
                          {r.student?.first_name} {r.student?.last_name}
                        </div>
                        <div className="muted">{r.student?.matricule}</div>
                      </div>
                      <div className="dist">
                        dist: {Number(r.distance).toFixed(3)}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      </main>

      <footer className="footer muted">
        Cloud Attendance — Azure Functions • Blob Storage • Face Detect • MySQL • PDF • SendGrid
      </footer>
    </div>
  );
}
