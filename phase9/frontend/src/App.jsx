import { useEffect, useState } from "react";
import { getRegions } from "./api";
import MapView from "./views/MapView";

const REGION_LABELS = {
  us_tx: "Texas (TX)",
  us_la: "Louisiana (LA)",
  us_ok: "Oklahoma (OK)",
};

export default function App() {
  const [regions, setRegions]   = useState([]);
  const [selected, setSelected] = useState("us_tx");
  const [error, setError]       = useState("");

  useEffect(() => {
    getRegions()
      .then((data) => setRegions(data.regions || []))
      .catch((e) => setError(String(e)));
  }, []);

  const regionLabel = (slug) =>
    REGION_LABELS[slug] || slug.toUpperCase().replace("US_", "");

  return (
    <div style={{ padding: 20, fontFamily: "system-ui, Arial", width: "100%", boxSizing: "border-box" }}>

      <h1 style={{ margin: "0 0 4px 0", fontSize: "1.4em", fontWeight: 600 }}>
        Pipeline Corridor Risk Visualisation
      </h1>
      <p style={{ margin: "0 0 16px 0", fontSize: 13, color: "#aaa" }}>
        Statistically validated corridor-scale risk scoring across U.S. natural gas transmission infrastructure
      </p>

      <div style={{ marginBottom: 12 }}>
        <label>Region: </label>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          style={{ padding: 6, marginLeft: 8 }}
        >
          {regions.map((r) => (
            <option key={r.slug} value={r.slug}>
              {regionLabel(r.slug)}
            </option>
          ))}
        </select>
      </div>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      <MapView region={selected} />

    </div>
  );
}
