import "./App.css";
import { useMemo, useState } from "react";
import axios from "axios";

/**
 * Configuration présentation
 * (paramètres techniques masqués)
 */
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:7071/api";
const CLASS_ID = 1;
const CLASS_NAME = "L4 Cybersecurity";
const DEFAULT_THRESHOLD = 0.55;

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [data, setData] = useState(null);
  const [localPreview, setLocalPreview] = useState("");

  /**
   * Étudiants reconnus (sans valeurs techniques)
   */
  const presentStudents = useMemo(() => {
    const results = data?.recognition?.results || [];
    return results.filter((r) => r.match && r.student);
  }, [data]);

  /**
   * Upload image vers Blob
   */
  async function uploadImage(selectedFile) {
    const bytes = await selectedFile.arrayBuffer();
    const res = await axios.post(`${API_BASE}/UploadImage`, bytes, {
      headers: { "Content-Type": selectedFile.type || "image/jpeg" },
      timeout: 120000,
    });
    return res.data.image_url;
  }

  /**
   * Lancement pipeline Cloud
   */
  async function runPipeline(groupUrl) {
    const payload = {
      class_id: CLASS_ID,
      image_url: groupUrl,
      threshold: DEFAULT_THRESHOLD,
      request_id: `web-${Date.now()}`,
    };

    const res = await axios.post(`${API_BASE}/RunAttendancePipeline`, payload, {
      headers: { "Content-Type": "application/json" },
      timeout: 300000,
    });

    return res.data;
  }

  /**
   * Sélection image
   */
  const onPickFile = (f) => {
    setFile(f);
    setData(null);
    setError("");
    setImageUrl("");
    if (localPreview) URL.revokeObjectURL(localPreview);
    if (f) setLocalPreview(URL.createObjectURL(f));
  };

  /**
   * Action principale (1 clic)
   */
  const onRun = async () => {
    if (!file) {
      setError("Veuillez sélectionner une photo de groupe.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const url = await uploadImage(file);
      setImageUrl(url);

      const result = await runPipeline(url);
      setData(result);
    } catch (e) {
      setError(
        e?.response?.data?.error ||
          "Une erreur est survenue lors du traitement."
      );
    } finally {
      setLoading(false);
    }
  };

  const reco = data?.recognition;

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="brand">
          <div className="logo">CA</div>
          <div>
            <h1>Cloud Attendance</h1>
            <p>
              Prise de présence automatisée par reconnaissance faciale
            </p>
            <p className="muted">Classe : {CLASS_NAME}</p>
          </div>
        </div>

        <div className="pill">
          <span className="dot" />
          <span>Local</span>
          <span className="muted">{API_BASE}</span>
        </div>
      </header>

      <main className="grid">
        {/* Colonne gauche */}
        <section className="card">
          <h2>Nouvelle prise</h2>

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
                  JPG / PNG — caméra ou fichier
                </div>
              </div>
              <div className="uploadBtn">Parcourir</div>
            </label>

            {localPreview && (
              <div className="preview">
                <img src={localPreview} alt="Aperçu" />
              </div>
            )}
          </div>

          {error && <div className="alert error">⚠️ {error}</div>}

          <button
            className="primary"
            onClick={onRun}
            disabled={loading}
          >
            {loading ? "Traitement en cours..." : "📸 Prendre la présence"}
          </button>

          {imageUrl && (
            <div className="links">
              <a href={imageUrl} target="_blank" rel="noreferrer">
                Voir l’image originale →
              </a>
            </div>
          )}
        </section>

        {/* Colonne droite */}
        <section className="card">
          <div className="cardHeader">
            <h2>Résultats</h2>
            {data?.email?.sendgrid_status && (
              <span className="badge">
                Email envoyé
              </span>
            )}
          </div>

          {!data ? (
            <div className="empty">
              <div className="emptyIcon">📊</div>
              <div>
                <div className="emptyTitle">Aucun résultat</div>
                <div className="muted">
                  Lancez une prise pour générer la présence, le PDF et l’email.
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* KPIs */}
              <div className="kpis">
                <div className="kpi">
                  <div className="kpiLabel">Visages détectés</div>
                  <div className="kpiValue">
                    {reco?.faces_detected ?? "-"}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Total étudiants</div>
                  <div className="kpiValue">
                    {reco?.total_students ?? "-"}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Présents</div>
                  <div className="kpiValue">
                    {reco?.present_count ?? "-"}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel">Taux de présence</div>
                  <div className="kpiValue">
                    {reco?.attendance_percentage ?? "-"}%
                  </div>
                </div>
              </div>

              <div className="rowBetween">
                <h3>Étudiants présents</h3>
                {data?.pdf_url && (
                  <a
                    className="linkBtn"
                    href={data.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ouvrir le PDF →
                  </a>
                )}
              </div>

              {presentStudents.length === 0 ? (
                <div className="alert">
                  Aucun étudiant reconnu.
                </div>
              ) : (
                <ul className="list">
                  {presentStudents.map((r, idx) => (
                    <li key={idx} className="listItem">
                      <div className="avatar">
                        {(r.student.first_name?.[0] || "S").toUpperCase()}
                      </div>
                      <div className="who">
                        <div className="name">
                          {r.student.first_name} {r.student.last_name}
                        </div>
                        <div className="muted">
                          {r.student.matricule}
                        </div>
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
        Cloud Attendance — Azure Functions · Blob Storage · Face Detect · MySQL · PDF · SendGrid
      </footer>
    </div>
  );
}
