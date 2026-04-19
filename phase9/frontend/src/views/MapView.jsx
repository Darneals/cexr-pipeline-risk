import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const DEFAULT_CENTER = [-98.5, 31.0];
const DEFAULT_ZOOM = 5;

const SOURCE_ID  = "risk_windows";
const BASE_ID    = "risk-windows-fill";
const OUTLINE_ID = "risk-windows-outline";
const EXTRUDE_ID = "risk-windows-extrude";
const LABELS_ID  = "corridor-labels";

const Z_MAX          = 6;
const HEIGHT_PER_Z   = 500;

const num         = (field, def) => ["coalesce", ["to-number", ["get", field]], def];
// FIX 4: use z_corridor (new field name from corridorfdr)
const zClamped        = ["min", Z_MAX, ["max", 0, num("z_corridor", 0)]];
const extrudeHeightExpr = ["*", zClamped, HEIGHT_PER_Z];

// FIX 4: updated field candidates to match corridorfdr schema
const SCORE_FIELD_CANDIDATES = ["risk_obs_max", "risk_score_fixed", "risk_score"];
const BAND_FIELD_CANDIDATES  = ["corridor_sig_band", "risk_band_story"];

const SCORE_STOPS = [
  0.0, "#2ECC71",
  0.5, "#F1C40F",
  0.75, "#E67E22",
  1.0, "#E74C3C",
];

// FIX 7: added "Not significant" entry for corridorfdr band values
const BAND_COLORS = [
  "Not significant", "#8E9AAF",
  "Very Low",        "#2ECC71",
  "Low",             "#27AE60",
  "Medium",          "#F1C40F",
  "High",            "#E67E22",
  "Very High",       "#E74C3C",
];

function resolveFieldsFromGeojson(geojson) {
  const f0   = geojson?.features?.[0];
  const p    = f0?.properties || {};
  const keys = Object.keys(p);

  const scoreField = SCORE_FIELD_CANDIDATES.find((k) => keys.includes(k)) || "risk_obs_max";
  const bandField  = BAND_FIELD_CANDIDATES.find((k) => keys.includes(k))  || "corridor_sig_band";

  return { scoreField, bandField };
}

function scoreColorExpr(scoreField) {
  return [
    "interpolate", ["linear"],
    ["coalesce", ["to-number", ["get", scoreField]], 0],
    ...SCORE_STOPS,
  ];
}

function bandColorExpr(bandField) {
  return ["match", ["get", bandField], ...BAND_COLORS, "#8E9AAF"];
}

function bboxFromGeoJSON(geojson) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

  const pushPair = (lng, lat) => {
    const x = Number(lng), y = Number(lat);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  };

  const walk = (node) => {
    if (!node) return;
    if (Array.isArray(node) && node.length >= 2 &&
        typeof node[0] !== "object" && typeof node[1] !== "object") {
      pushPair(node[0], node[1]); return;
    }
    if (Array.isArray(node)) { for (const child of node) walk(child); }
  };

  for (const f of (geojson?.features || [])) walk(f?.geometry?.coordinates);

  const ok = [minX, minY, maxX, maxY].every(Number.isFinite);
  return ok ? [minX, minY, maxX, maxY] : null;
}

// FIX 4+6: hotspot filters updated to corridorfdr field names
const STORY_HOTSPOT_FILTER = [
  "in",
  ["get", "corridor_sig_band"],
  ["literal", ["High", "Very High"]],
];

const VALIDATED_HOTSPOT_FILTER = [
  "any",
  ["==", ["get", "significant_fdr05"], true],
  ["==", ["get", "significant_fdr05"], "true"],
  ["==", ["get", "significant_fdr05"], "True"],
];

function applyHotspotFilter(map, showHotspots, hotspotMode) {
  const filter = showHotspots
    ? (hotspotMode === "validated" ? VALIDATED_HOTSPOT_FILTER : STORY_HOTSPOT_FILTER)
    : null;
  [BASE_ID, OUTLINE_ID, EXTRUDE_ID, LABELS_ID].forEach((id) => {
    if (map.getLayer(id)) map.setFilter(id, filter);
  });
}

// FIX 5+6: popup updated to corridorfdr field names
function makePopupHTML(region, props, scoreField, bandField) {
  const scoreRaw = props?.[scoreField];
  const scoreNum = Number(scoreRaw);
  const scoreText = Number.isFinite(scoreNum) ? scoreNum.toFixed(3) : (scoreRaw ?? "n/a");

  const band = props?.[bandField];

  // FIX 6: sig_gate uses significant_fdr05 (handles bool and string serialisation)
  const sigRaw  = props?.significant_fdr05;
  const sigGate = (sigRaw === true || sigRaw === "true" || sigRaw === "True")
    ? "PASS" : "FAIL";

  const fmtNum = (v, d = 3) => {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(d) : (v ?? "n/a");
  };

  return `
    <div style="font-family:system-ui, Arial; font-size:12px; line-height:1.35;">
      <div style="letter-spacing:0.14em;text-transform:uppercase;color:rgba(0,255,180,0.95);font-size:10px;margin-bottom:6px">
        Corridor Telemetry
      </div>
      <div><b>region</b>: ${region}</div>
      <div><b>win_id</b>: ${props?.win_id ?? "n/a"}</div>
      <div><b>corr_id</b>: ${props?.corr_id ?? "n/a"}</div>
      <div><b>win_len_m</b>: ${props?.win_len_m ?? "n/a"}</div>
      <div><b>start_m</b>: ${props?.start_m ?? "n/a"}</div>
      <div><b>end_m</b>: ${props?.end_m ?? "n/a"}</div>

      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.12);margin:8px 0" />

      <div><b>corridor band</b>: ${props?.corridor_sig_band ?? "n/a"}</div>
      <div><b>${scoreField}</b>: ${scoreText}</div>
      <div><b>${bandField}</b>: ${band ?? "n/a"}</div>

      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.12);margin:8px 0" />

      <div><b>sig_gate</b>: ${sigGate}</div>
      <div><b>significant_fdr05</b>: ${sigRaw ?? "n/a"}</div>
      <div><b>z_corridor</b>: ${fmtNum(props?.z_corridor)}</div>
      <div><b>q_fdr_bh</b>: ${fmtNum(props?.q_fdr_bh)}</div>
      <div><b>p_empirical</b>: ${fmtNum(props?.p_empirical)}</div>

      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.12);margin:8px 0" />

      <div><b>risk_obs_max</b>: ${fmtNum(props?.risk_obs_max)}</div>
      <div><b>incident_count</b>: ${props?.incident_count ?? "n/a"}</div>
      <div><b>exposure_count</b>: ${props?.exposure_count ?? "n/a"}</div>
    </div>
  `;
}

export default function MapView({ region }) {
  const hostRef = useRef(null);
  const mapRef  = useRef(null);
  const popupRef = useRef(null);

  const pulseTimerRef = useRef(null);
  const didFlyRef     = useRef(false);

  const [ui, setUi] = useState({
    res: "10km",
    story: true,
    showHotspots: false,
    hotspotMode: "story",
    outline: true,
    threeD: false,
  });

  const fieldsRef = useRef({
    scoreField: "risk_obs_max",
    bandField:  "corridor_sig_band",
  });

  const fittedKeyRef = useRef(null);
  const hoverIdRef   = useRef(null);

  const ensurePopup = () => {
    if (!popupRef.current) {
      popupRef.current = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        maxWidth: "360px",
      });
    }
    return popupRef.current;
  };

  const startPulseIfNeeded = () => {
    const map = mapRef.current;
    if (!map || pulseTimerRef.current) return;
    let t = 0;
    pulseTimerRef.current = window.setInterval(() => {
      if (!map.getLayer(EXTRUDE_ID)) return;
      t += 0.05;
      map.setPaintProperty(EXTRUDE_ID, "fill-extrusion-height", [
        "*", extrudeHeightExpr,
        ["+", 1, ["*", 0.25, ["sin", t]]],
      ]);
    }, 60);
  };

  const stopPulse = () => {
    if (pulseTimerRef.current) {
      clearInterval(pulseTimerRef.current);
      pulseTimerRef.current = null;
    }
  };

  const applyPaintAndFilters = () => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const { scoreField, bandField } = fieldsRef.current;
    const fillColor = ui.story ? bandColorExpr(bandField) : scoreColorExpr(scoreField);

    if (map.getLayer(BASE_ID)) {
      map.setPaintProperty(BASE_ID, "fill-color", fillColor);
      map.setLayoutProperty(BASE_ID, "visibility", ui.threeD ? "none" : "visible");
    }
    if (map.getLayer(EXTRUDE_ID)) {
      map.setLayoutProperty(EXTRUDE_ID, "visibility", ui.threeD ? "visible" : "none");
      map.setPaintProperty(EXTRUDE_ID, "fill-extrusion-color", fillColor);
      map.setPaintProperty(EXTRUDE_ID, "fill-extrusion-height", extrudeHeightExpr);
      if (ui.threeD) startPulseIfNeeded(); else stopPulse();
    }

    applyHotspotFilter(map, ui.showHotspots, ui.hotspotMode);

    if (map.getLayer(OUTLINE_ID))
      map.setLayoutProperty(OUTLINE_ID, "visibility", ui.outline ? "visible" : "none");
    if (map.getLayer(LABELS_ID))
      map.setLayoutProperty(LABELS_ID, "visibility", "none");
  };

  const fitToGeojson = (geojson) => {
    const map = mapRef.current;
    if (!map) return;
    const bb = bboxFromGeoJSON(geojson);
    if (!bb) return;
    map.fitBounds([[bb[0], bb[1]], [bb[2], bb[3]]], { padding: 30, maxZoom: 11 });
  };

  const loadGeojson = async (signal) => {
    const map = mapRef.current;
    if (!map) return;

    const suffix  = ui.res === "5km" ? "5km_ribbon" : "10km_ribbon";
    const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
    const url     = `${apiBase}/data/regions/${region}/results_corridor/risk_windows_${suffix}.geojson`;

    const res = await fetch(url, { signal, cache: "no-store" });
    if (!res.ok) throw new Error(`fetch failed ${res.status} for ${url}`);
    const geojson = await res.json();

    const { scoreField, bandField } = resolveFieldsFromGeojson(geojson);
    fieldsRef.current = { scoreField, bandField };

    const src = map.getSource(SOURCE_ID);
    if (src) src.setData(geojson);

    applyPaintAndFilters();

    const fitKey = `${region}:${ui.res}`;
    if (fittedKeyRef.current !== fitKey) {
      fittedKeyRef.current = fitKey;
      fitToGeojson(geojson);
      if (!didFlyRef.current) {
        didFlyRef.current = true;
        map.easeTo({ pitch: 70, bearing: -20, zoom: 12, duration: 1800 });
      }
    }
  };

  useEffect(() => {
    if (!hostRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: hostRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,preserveDrawingBuffer: true,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.dragRotate.enable();
    map.touchZoomRotate.enableRotation();
    map.keyboard.enable();
    map.doubleClickZoom.enable();
    map.setMaxPitch(85);

    mapRef.current = map;
    window._map = map;

    const attachHover = (layerId) => {
      const popup = ensurePopup();

      const clearHover = () => {
        if (hoverIdRef.current != null) {
          try { map.setFeatureState({ source: SOURCE_ID, id: hoverIdRef.current }, { hover: false }); } catch {}
        }
        hoverIdRef.current = null;
      };

      map.on("mousemove", layerId, (e) => {
        const f = e?.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const props = f.properties || {};
        const id    = props.win_id;
        if (hoverIdRef.current !== id) {
          clearHover();
          hoverIdRef.current = id;
          try { map.setFeatureState({ source: SOURCE_ID, id }, { hover: true }); } catch {}
        }
        const { scoreField, bandField } = fieldsRef.current;
        popup.setLngLat(e.lngLat)
             .setHTML(makePopupHTML(region, props, scoreField, bandField))
             .addTo(map);
      });

      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
        clearHover();
      });
    };

    const attachClickToFocus = (layerId) => {
      map.on("click", layerId, (e) => {
        const f = e?.features?.[0];
        if (!f) return;
        map.easeTo({
          center: e.lngLat,
          zoom: Math.max(map.getZoom(), 15),
          pitch: 70,
          bearing: map.getBearing() + 20,
          duration: 800,
        });
      });
    };

    map.on("load", () => {
      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
          promoteId: "win_id",
        });
        window._map = map;
      }

      window.exportMapPNG = async (scale = 4, name = "fig08A_metaverse_3d.png", timeoutMs = 15000) => {
        const map = window._map;
        if (!map) throw new Error("window._map not found.");
        const waitForIdleOrTimeout = () => new Promise((resolve) => {
          let done = false;
          const finish = () => { if (done) return; done = true; resolve(); };
          try { map.once("idle", finish); } catch {}
          try { map.triggerRepaint(); } catch {}
          setTimeout(finish, timeoutMs);
        });
        await waitForIdleOrTimeout();
        const canvas = map.getCanvas();
        if (!canvas) throw new Error("Map canvas not found.");
        const { width: w, height: h } = canvas;
        if (!w || !h) throw new Error(`Canvas invalid: ${w}x${h}`);
        const out = document.createElement("canvas");
        out.width  = Math.round(w * scale);
        out.height = Math.round(h * scale);
        const ctx = out.getContext("2d");
        if (!ctx) throw new Error("Could not get 2D context.");
        ctx.drawImage(canvas, 0, 0, out.width, out.height);
        const blob = await new Promise((resolve) => out.toBlob(resolve, "image/png"));
        if (!blob) throw new Error("toBlob() returned null.");
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = name;
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        return { base: { w, h }, out: { w: out.width, h: out.height }, scale };
      };

      if (!map.getLayer(BASE_ID)) {
        map.addLayer({
          id: BASE_ID, type: "fill", source: SOURCE_ID,
          paint: {
            "fill-color":   bandColorExpr(fieldsRef.current.bandField),
            "fill-opacity": 0.75,
          },
        });
      }

      if (!map.getLayer(EXTRUDE_ID)) {
        map.addLayer({
          id: EXTRUDE_ID, type: "fill-extrusion", source: SOURCE_ID,
          layout: { "visibility": "none" },
          paint: {
            "fill-extrusion-color":   bandColorExpr(fieldsRef.current.bandField),
            "fill-extrusion-height":  extrudeHeightExpr,
            "fill-extrusion-base":    0,
            "fill-extrusion-opacity": 0.85,
          },
        });
      }

      if (!map.getLayer(OUTLINE_ID)) {
        map.addLayer({
          id: OUTLINE_ID, type: "line", source: SOURCE_ID,
          layout: { "line-join": "round", "line-cap": "round" },
          paint: { "line-width": 1, "line-color": "#000", "line-opacity": 0.30 },
        });
      }

      if (!map.getLayer(LABELS_ID)) {
        map.addLayer({
          id: LABELS_ID, type: "symbol", source: SOURCE_ID,
          minzoom: 12,
          layout: {
            "visibility": "none",
            "text-field": ["get", "corr_id"],
            "text-size": 11,
            "text-allow-overlap": false,
          },
          paint: {
            "text-halo-color": "rgba(0,0,0,0.65)",
            "text-halo-width": 1,
          },
          filter: STORY_HOTSPOT_FILTER,
        });
      }

      applyPaintAndFilters();
      attachHover(BASE_ID);
      attachHover(EXTRUDE_ID);
      attachClickToFocus(BASE_ID);
      attachClickToFocus(EXTRUDE_ID);

      if (typeof map.setFog === "function") {
        map.setFog({
          range: [0.5, 10],
          color: "rgba(220,255,245,0.08)",
          "horizon-blend": 0.15,
        });
      }
    });

    return () => {
      try { stopPulse(); map.remove(); } catch {}
      mapRef.current    = null;
      window._map       = undefined;
      didFlyRef.current = false;
    };
  }, [region]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const controller = new AbortController();
    const run = async () => {
      try {
        if (!map.isStyleLoaded()) map.once("load", () => loadGeojson(controller.signal));
        else await loadGeojson(controller.signal);
      } catch (e) {
        if (e?.name !== "AbortError") console.error(e);
      }
    };
    run();
    return () => controller.abort();
  }, [region, ui.res]);

  useEffect(() => {
    applyPaintAndFilters();
  }, [ui.story, ui.showHotspots, ui.hotspotMode, ui.outline, ui.threeD]);

  const onReload = async () => {
    const map = mapRef.current;
    if (!map) return;
    const controller = new AbortController();
    try { await loadGeojson(controller.signal); }
    catch (e) { if (e?.name !== "AbortError") console.error(e); }
  };

  return (
    <div style={{ position: "relative" }}>
      <div
        ref={hostRef}
        style={{
          height: "600px", width: "100%",
          borderRadius: 12, overflow: "hidden",
          border: "1px solid rgba(0,255,180,0.15)",
          boxShadow: "0 0 18px rgba(0,255,180,0.06)",
        }}
      />

      <div style={{
        position: "absolute", top: 12, left: 12,
        padding: "10px 12px", borderRadius: 10,
        background: "rgba(0,0,0,0.55)",
        border: "1px solid rgba(0,255,180,0.25)",
        color: "rgba(220,255,245,0.95)",
        fontFamily: "system-ui, Arial", fontSize: 12,
        zIndex: 10, minWidth: 260,
      }}>
        <div style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 10, color: "rgba(0,255,180,0.9)" }}>
          Control Room
        </div>

        <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Resolution</span>
            <select value={ui.res} onChange={(e) => setUi((p) => ({ ...p, res: e.target.value }))}
              style={{ padding: "6px 8px", borderRadius: 6 }}>
              <option value="10km">10km</option>
              <option value="5km">5km</option>
            </select>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
            <input type="checkbox" checked={ui.threeD} onChange={(e) => {
              const checked = !!e.target.checked;
              setUi((p) => ({ ...p, threeD: checked }));
              const map = mapRef.current;
              if (map) map.easeTo({ pitch: checked ? 70 : 0, bearing: checked ? -20 : 0, zoom: checked ? 14 : 10, duration: 900 });
            }} />
            <span>3D</span>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
            <input type="checkbox" checked={ui.story}
              onChange={(e) => setUi((p) => ({ ...p, story: !!e.target.checked }))} />
            <span>Story mode</span>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
            <input type="checkbox" checked={ui.showHotspots}
              onChange={(e) => setUi((p) => ({ ...p, showHotspots: !!e.target.checked }))} />
            <span>Show Hotspots</span>
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span>Hotspot Mode</span>
            <select value={ui.hotspotMode}
              onChange={(e) => setUi((p) => ({ ...p, hotspotMode: e.target.value }))}
              style={{ padding: "6px 8px", borderRadius: 6 }}>
              <option value="story">Story Hotspots</option>
              <option value="validated">Validated (FDR)</option>
            </select>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
            <input type="checkbox" checked={ui.outline}
              onChange={(e) => setUi((p) => ({ ...p, outline: !!e.target.checked }))} />
            <span>Outline</span>
          </label>

          <button onClick={onReload} style={{
            marginTop: 6, padding: "8px 10px", borderRadius: 8,
            cursor: "pointer", border: "1px solid rgba(255,255,255,0.15)",
            background: "rgba(0,0,0,0.35)", color: "rgba(220,255,245,0.95)", fontWeight: 600,
          }}>
            Reload
          </button>
        </div>

        <div style={{ marginTop: 10, color: "rgba(220,255,245,0.85)" }}>
          Hover corridors for telemetry.
        </div>
      </div>
    </div>
  );
}
