/**
 * Marstek Venus E — Lovelace Card
 * Custom Web Component auto-enregistré par l'intégration Home Assistant.
 *
 * Usage dans un dashboard Lovelace :
 *   type: custom:marstek-venus-card
 *
 * Optionnel :
 *   type: custom:marstek-venus-card
 *   title: "Ma batterie"          # override du titre
 *   rated_capacity: 5120          # Wh nominal (auto-détecté depuis l'entité)
 */

// ── Logo Marstek SVG embarqué ────────────────────────────────────────────────
const MARSTEK_LOGO_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 48" fill="none">
  <defs>
    <linearGradient id="mg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#00e87a"/>
      <stop offset="100%" stop-color="#00916e"/>
    </linearGradient>
  </defs>
  <!-- Icône batterie stylisée -->
  <rect x="2" y="10" width="34" height="28" rx="5" stroke="url(#mg)" stroke-width="2.5" fill="none"/>
  <rect x="36" y="17" width="4" height="14" rx="2" fill="url(#mg)"/>
  <rect x="7" y="15" width="24" height="18" rx="3" fill="url(#mg)" opacity="0.85"/>
  <!-- Éclair -->
  <path d="M21 15 L16 24 L20 24 L19 33 L26 22 L22 22 Z"
        fill="#0b0f14" opacity="0.9"/>
  <!-- Texte MARSTEK -->
  <text x="46" y="22" font-family="'Rajdhani','Segoe UI',sans-serif"
        font-size="13" font-weight="800" fill="#e8f0ea" letter-spacing="1.5">MARSTEK</text>
  <!-- Texte VENUS E -->
  <text x="46" y="37" font-family="'Rajdhani','Segoe UI',sans-serif"
        font-size="11" font-weight="600" fill="#00d278" letter-spacing="2">VENUS E 3.0</text>
</svg>`;

// ── Utilitaires ──────────────────────────────────────────────────────────────
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const stateNum = (hass, eid, fallback = 0) =>
  parseFloat(hass?.states?.[eid]?.state ?? fallback) || fallback;
const stateStr = (hass, eid, fallback = "–") =>
  hass?.states?.[eid]?.state ?? fallback;

// ── Web Component ────────────────────────────────────────────────────────────
class MarstekVenusCard extends HTMLElement {

  // ── Propriétés Lovelace obligatoires ────────────────────────────────────

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() { return 7; }

  static getConfigElement() {
    return document.createElement("marstek-venus-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  // ── Rendu ────────────────────────────────────────────────────────────────

  _render() {
    const h = this._hass;
    if (!h) return;

    // ── Lecture des entités ──────────────────────────────────────────────
    const soc         = stateNum(h, "sensor.marstek_battery_soc");
    const batCap      = stateNum(h, "sensor.marstek_battery_capacity");
    const ratedCap    = stateNum(h, "sensor.marstek_battery_rated_capacity", 5120);
    const batTemp     = stateNum(h, "sensor.marstek_battery_temperature");
    const batPower    = stateNum(h, "sensor.marstek_battery_power");
    const pvPower     = stateNum(h, "sensor.marstek_pv_power");
    const gridPower   = stateNum(h, "sensor.marstek_grid_power");
    const offgrid     = stateNum(h, "sensor.marstek_offgrid_power");
    const totalPv     = stateNum(h, "sensor.marstek_total_pv_energy");
    const totalExp    = stateNum(h, "sensor.marstek_total_grid_export");
    const totalImp    = stateNum(h, "sensor.marstek_total_grid_import");
    const rssi        = stateNum(h, "sensor.marstek_wifi_signal", -80);
    const mode        = stateStr(h, "sensor.marstek_operating_mode", "–");
    const charging    = stateStr(h, "binary_sensor.marstek_charging") === "on";
    const discharging = stateStr(h, "binary_sensor.marstek_discharging") === "on";

    // ── Couleurs dynamiques ──────────────────────────────────────────────
    const socCol  = soc > 70 ? "#00d278" : soc > 30 ? "#ffaa00" : "#ff4455";
    const socGlow = soc > 70 ? "0,210,120" : soc > 30 ? "255,170,0" : "255,68,85";

    const modeMap = {
      Auto:    { icon: "⚡", color: "#00d278", glow: "0,210,120" },
      AI:      { icon: "🤖", color: "#9d7fff", glow: "157,127,255" },
      Manual:  { icon: "🕐", color: "#4da6ff", glow: "77,166,255" },
      Passive: { icon: "🎯", color: "#ff9900", glow: "255,153,0" },
    };
    const mc = modeMap[mode] ?? { icon: "●", color: "#888", glow: "128,128,128" };

    const gridCol   = gridPower > 0 ? "#ff4455" : gridPower < 0 ? "#00d278" : "#444";
    const gridGlow  = gridPower > 0 ? "255,68,85" : gridPower < 0 ? "0,210,120" : "60,60,60";
    const gridLabel = gridPower > 0 ? "↓ Import réseau" : gridPower < 0 ? "↑ Export réseau" : "Réseau";

    const batCol    = batPower > 0 ? "#ff9900" : batPower < 0 ? "#4da6ff" : "#444";
    const batLabel  = batPower < 0 ? "▼ Charge" : batPower > 0 ? "▲ Décharge" : "En veille";

    const wifiCol   = rssi > -60 ? "#00d278" : rssi > -75 ? "#ffaa00" : "#ff4455";

    const statusText = charging ? "▲ EN CHARGE" : discharging ? "▼ DÉCHARGE" : "■ VEILLE";
    const statusCol  = charging ? "#00d278"      : discharging ? "#ff9900"    : "#555";

    // ── Arc SVG SOC ──────────────────────────────────────────────────────
    const R = 54, CX = 70, CY = 72;
    const circ = 2 * Math.PI * R;
    const arc  = circ * 0.75;
    const dash = clamp(soc / 100, 0, 1) * arc;

    // ── Barre de puissance ───────────────────────────────────────────────
    const powerBar = (val, max, col, glow) => {
      const pct = clamp(Math.abs(val) / max * 100, 0, 100);
      return `<div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;margin-top:6px;">
        <div style="width:${pct}%;height:100%;background:${col};border-radius:2px;
          box-shadow:0 0 8px rgba(${glow},0.7);transition:width .8s ease;"></div>
      </div>`;
    };

    // ── Mode bouton ──────────────────────────────────────────────────────
    const modeBtn = (m) => {
      const cfg   = modeMap[m] ?? mc;
      const activ = m === mode;
      return `<button class="mode-btn ${activ ? "active" : ""}"
          data-mode="${m}"
          style="
            background:${activ ? `rgba(${cfg.glow},0.12)` : "rgba(255,255,255,0.03)"};
            border:1px solid ${activ ? `rgba(${cfg.glow},0.45)` : "rgba(255,255,255,0.08)"};
            box-shadow:${activ ? `0 0 14px rgba(${cfg.glow},0.2)` : "none"};
            color:${activ ? cfg.color : "rgba(200,220,210,0.38)"};
          ">
          <span class="mode-icon">${cfg.icon}</span>
          <span class="mode-label">${m.toUpperCase()}</span>
        </button>`;
    };

    // ── Template HTML ────────────────────────────────────────────────────
    const html = `
      <ha-card>
        <style>
          ha-card {
            background: #0b0f14;
            border: 1px solid rgba(0,210,120,0.18);
            border-radius: 24px;
            overflow: hidden;
            box-shadow:
              0 0 0 1px rgba(0,0,0,0.4),
              0 4px 6px rgba(0,0,0,0.3),
              0 20px 60px rgba(0,0,0,0.5),
              inset 0 1px 0 rgba(255,255,255,0.04);
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #e8f0ea;
          }

          /* ── Header ── */
          .mv-header {
            background: linear-gradient(135deg, #0f1a14, #0b1410);
            border-bottom: 1px solid rgba(0,210,120,0.1);
            padding: 14px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
          }
          .mv-logo { flex-shrink: 0; width: 110px; height: 44px; }
          .mv-title-block { flex: 1; }
          .mv-title {
            font-size: 15px; font-weight: 700;
            letter-spacing: 1.5px; text-transform: uppercase;
          }
          .mv-subtitle {
            font-size: 9px; color: rgba(200,220,210,0.35);
            letter-spacing: 2px; margin-top: 1px;
          }
          .mv-status-block { text-align: right; }
          .mv-mode-badge {
            font-size: 12px; font-weight: 700;
            letter-spacing: 1px; color: ${mc.color};
          }
          .mv-action {
            font-size: 10px; letter-spacing: 1.5px;
            color: ${statusCol}; margin-top: 2px;
          }

          /* ── SOC ── */
          .mv-soc-section {
            padding: 16px 18px 12px;
            display: flex;
            align-items: center;
            gap: 18px;
          }
          .mv-arc-wrap { position: relative; flex-shrink: 0; }
          .mv-arc-label {
            position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -48%);
            text-align: center;
          }
          .mv-soc-pct {
            font-size: 33px; font-weight: 900;
            color: ${socCol};
            text-shadow: 0 0 18px rgba(${socGlow},0.55);
            line-height: 1;
          }
          .mv-soc-unit { font-size: 15px; }
          .mv-soc-tag {
            font-size: 9px; color: rgba(200,220,210,0.4);
            letter-spacing: 1px; margin-top: 2px;
          }
          .mv-info-right { flex: 1; display: flex; flex-direction: column; gap: 10px; }
          .mv-cap-label {
            font-size: 10px; color: rgba(200,220,210,0.4);
            letter-spacing: 1px; margin-bottom: 2px;
          }
          .mv-cap-val { font-size: 21px; font-weight: 800; }
          .mv-cap-unit { font-size: 11px; color: rgba(200,220,210,0.4); }
          .mv-cap-sub { font-size: 10px; color: rgba(200,220,210,0.3); margin-top: 1px; }
          .mv-cap-bar {
            height: 3px; background: rgba(255,255,255,0.07);
            border-radius: 2px; margin-top: 5px; overflow: hidden;
          }
          .mv-cap-bar-fill {
            height: 100%; background: ${socCol}; border-radius: 2px;
            width: ${soc}%;
            box-shadow: 0 0 6px rgba(${socGlow},0.8);
            transition: width 1s ease;
          }
          .mv-mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
          .mv-mini-box {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 8px; padding: 6px 10px;
          }
          .mv-mini-label {
            font-size: 9px; color: rgba(200,220,210,0.35); letter-spacing: 1px;
          }
          .mv-mini-val { font-size: 14px; font-weight: 700; margin-top: 1px; }

          /* ── Flux ── */
          .mv-flows {
            padding: 4px 18px 14px;
            border-top: 1px solid rgba(0,210,120,0.08);
            display: flex; flex-direction: column; gap: 7px;
          }
          .mv-section-label {
            font-size: 9px; font-weight: 700; letter-spacing: 2.5px;
            color: rgba(200,220,210,0.22); padding: 10px 0 4px;
          }
          .mv-flow-row {
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 11px; padding: 10px 13px;
          }
          .mv-flow-head {
            display: flex; justify-content: space-between; align-items: center;
          }
          .mv-flow-left { display: flex; align-items: center; gap: 7px; }
          .mv-flow-icon { font-size: 16px; }
          .mv-flow-name { font-size: 11px; color: rgba(200,220,210,0.45); }
          .mv-flow-val { font-size: 15px; font-weight: 800; }

          /* ── Modes ── */
          .mv-modes {
            padding: 0 18px 12px;
            border-top: 1px solid rgba(255,255,255,0.05);
          }
          .mv-modes-grid {
            display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 7px;
          }
          .mode-btn {
            border-radius: 12px; padding: 10px 4px; cursor: pointer;
            display: flex; flex-direction: column; align-items: center; gap: 4px;
            transition: all 0.2s; outline: none;
          }
          .mode-btn:hover { filter: brightness(1.2); transform: translateY(-1px); }
          .mode-btn:active { transform: scale(0.96); }
          .mode-icon { font-size: 20px; }
          .mode-label { font-size: 9px; font-weight: 700; letter-spacing: 1px; }

          /* ── Stats ── */
          .mv-stats {
            padding: 14px 18px 16px;
            border-top: 1px solid rgba(255,255,255,0.05);
          }
          .mv-stats-grid { display: flex; gap: 7px; margin-bottom: 10px; }
          .mv-stat-box {
            flex: 1; background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 11px; padding: 10px 8px; text-align: center;
          }
          .mv-stat-icon { font-size: 18px; margin-bottom: 4px; }
          .mv-stat-val { font-size: 15px; font-weight: 800; }
          .mv-stat-unit { font-size: 10px; color: rgba(200,220,210,0.4); }
          .mv-stat-label {
            font-size: 9px; color: rgba(200,220,210,0.35);
            letter-spacing: 0.8px; margin-top: 3px;
          }
          .mv-wifi-row {
            display: flex; align-items: center; justify-content: flex-end; gap: 6px;
            padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05);
          }
          .mv-wifi-label { font-size: 10px; color: rgba(200,220,210,0.25); }
          .mv-wifi-val { font-size: 11px; font-weight: 700; color: ${wifiCol}; }
        </style>

        <!-- ══ HEADER ══ -->
        <div class="mv-header">
          <div class="mv-logo">${MARSTEK_LOGO_SVG}</div>
          <div class="mv-status-block" style="margin-left:auto">
            <div class="mv-mode-badge">${mc.icon} ${mode.toUpperCase()}</div>
            <div class="mv-action">${statusText}</div>
          </div>
        </div>

        <!-- ══ SOC ══ -->
        <div class="mv-soc-section">
          <div class="mv-arc-wrap">
            <svg width="140" height="128" viewBox="0 0 140 128">
              <defs>
                <filter id="mv-glow">
                  <feGaussianBlur stdDeviation="3" result="b"/>
                  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
              </defs>
              <circle cx="${CX}" cy="${CY}" r="${R}" fill="none"
                stroke="rgba(255,255,255,0.06)" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="${arc} ${circ - arc}"
                transform="rotate(-225 ${CX} ${CY})"/>
              <circle cx="${CX}" cy="${CY}" r="${R}" fill="none"
                stroke="${socCol}" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="${dash} ${circ - dash}"
                transform="rotate(-225 ${CX} ${CY})"
                filter="url(#mv-glow)"
                style="transition:stroke-dasharray 1s ease"/>
              <circle cx="${CX}" cy="${CY}" r="40" fill="rgba(0,0,0,0.3)"
                stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            </svg>
            <div class="mv-arc-label">
              <div class="mv-soc-pct">${soc}<span class="mv-soc-unit">%</span></div>
              <div class="mv-soc-tag">SOC</div>
            </div>
          </div>
          <div class="mv-info-right">
            <div>
              <div class="mv-cap-label">ÉNERGIE RESTANTE</div>
              <div class="mv-cap-val">${batCap.toFixed(0)} <span class="mv-cap-unit">Wh</span></div>
              <div class="mv-cap-sub">sur ${ratedCap.toFixed(0)} Wh nominal</div>
              <div class="mv-cap-bar"><div class="mv-cap-bar-fill"></div></div>
            </div>
            <div class="mv-mini-grid">
              <div class="mv-mini-box">
                <div class="mv-mini-label">TEMP.</div>
                <div class="mv-mini-val" style="color:#4da6ff">${batTemp.toFixed(1)} °C</div>
              </div>
              <div class="mv-mini-box">
                <div class="mv-mini-label">BATTERIE</div>
                <div class="mv-mini-val" style="color:${batCol}">
                  ${batLabel} ${Math.abs(batPower)} W
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ FLUX D'ÉNERGIE ══ -->
        <div class="mv-flows">
          <div class="mv-section-label">⚡ &nbsp;FLUX D'ÉNERGIE</div>
          <div class="mv-flow-row">
            <div class="mv-flow-head">
              <div class="mv-flow-left">
                <span class="mv-flow-icon">☀</span>
                <span class="mv-flow-name">Puissance solaire PV</span>
              </div>
              <span class="mv-flow-val" style="color:#ffaa00;text-shadow:0 0 10px rgba(255,170,0,0.5)">
                ${pvPower} W
              </span>
            </div>
            ${powerBar(pvPower, 3000, "#ffaa00", "255,170,0")}
          </div>
          <div class="mv-flow-row">
            <div class="mv-flow-head">
              <div class="mv-flow-left">
                <span class="mv-flow-icon">⚡</span>
                <span class="mv-flow-name">${gridLabel}</span>
              </div>
              <span class="mv-flow-val" style="color:${gridCol};text-shadow:0 0 10px rgba(${gridGlow},0.5)">
                ${Math.abs(gridPower)} W
              </span>
            </div>
            ${powerBar(gridPower, 3000, gridCol, gridGlow)}
          </div>
          ${offgrid !== 0 ? `
          <div class="mv-flow-row">
            <div class="mv-flow-head">
              <div class="mv-flow-left">
                <span class="mv-flow-icon">🏠</span>
                <span class="mv-flow-name">Hors-réseau (offgrid)</span>
              </div>
              <span class="mv-flow-val" style="color:#9d7fff;text-shadow:0 0 10px rgba(157,127,255,0.5)">
                ${Math.abs(offgrid)} W
              </span>
            </div>
            ${powerBar(offgrid, 3000, "#9d7fff", "157,127,255")}
          </div>` : ""}
        </div>

        <!-- ══ CONTRÔLE DE MODE ══ -->
        <div class="mv-modes">
          <div class="mv-section-label">⚙ &nbsp;CONTRÔLE DU MODE</div>
          <div class="mv-modes-grid">
            ${["Auto", "AI", "Manual", "Passive"].map(modeBtn).join("")}
          </div>
        </div>

        <!-- ══ STATISTIQUES ══ -->
        <div class="mv-stats">
          <div class="mv-section-label">📊 &nbsp;STATISTIQUES TOTALES</div>
          <div class="mv-stats-grid">
            <div class="mv-stat-box">
              <div class="mv-stat-icon">☀</div>
              <div class="mv-stat-val" style="color:#ffaa00;text-shadow:0 0 10px rgba(255,170,0,0.4)">
                ${totalPv.toFixed(1)}<span class="mv-stat-unit"> kWh</span>
              </div>
              <div class="mv-stat-label">Total solaire</div>
            </div>
            <div class="mv-stat-box">
              <div class="mv-stat-icon">↑</div>
              <div class="mv-stat-val" style="color:#00d278;text-shadow:0 0 10px rgba(0,210,120,0.4)">
                ${totalExp.toFixed(1)}<span class="mv-stat-unit"> kWh</span>
              </div>
              <div class="mv-stat-label">Export réseau</div>
            </div>
            <div class="mv-stat-box">
              <div class="mv-stat-icon">↓</div>
              <div class="mv-stat-val" style="color:#ff4455;text-shadow:0 0 10px rgba(255,68,85,0.4)">
                ${totalImp.toFixed(1)}<span class="mv-stat-unit"> kWh</span>
              </div>
              <div class="mv-stat-label">Import réseau</div>
            </div>
          </div>
          <div class="mv-wifi-row">
            <span class="mv-wifi-label">WiFi</span>
            <span class="mv-wifi-val">${rssi} dBm</span>
            <span>${rssi > -60 ? "📶" : rssi > -75 ? "📶" : "⚠"}</span>
          </div>
        </div>
      </ha-card>`;

    // Injecter le HTML (ou initialiser)
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.shadowRoot.innerHTML = html;

    // ── Attacher les handlers de mode ────────────────────────────────────
    this.shadowRoot.querySelectorAll(".mode-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const newMode = btn.dataset.mode;
        this._hass.callService("select", "select_option", {
          entity_id: "select.marstek_operating_mode",
          option: newMode,
        });
      });
    });
  }
}

// ── Enregistrement du custom element ────────────────────────────────────────
if (!customElements.get("marstek-venus-card")) {
  customElements.define("marstek-venus-card", MarstekVenusCard);
  console.info(
    "%c MARSTEK VENUS CARD %c v1.2.0 ",
    "background:#00d278;color:#0b0f14;font-weight:800;border-radius:4px 0 0 4px;padding:2px 6px",
    "background:#0b0f14;color:#00d278;font-weight:600;border-radius:0 4px 4px 0;padding:2px 6px"
  );
}

// ── Déclaration pour l'éditeur de cartes HA ─────────────────────────────────
window.customCards = window.customCards || [];
window.customCards.push({
  type: "marstek-venus-card",
  name: "Marstek Venus E",
  description: "Tableau de bord complet pour la batterie Marstek Venus E 3.0",
  preview: false,
  documentationURL: "https://github.com/Jhamende/marstek-ha",
});
