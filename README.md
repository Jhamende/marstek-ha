# Marstek Venus E 3.0 — Home Assistant Integration

Intégration locale pour les batteries **Marstek Venus E 3.0** (et séries C/D compatibles).  
Communication 100 % locale via l'**Open API UDP JSON-RPC** officielle de Marstek — aucun cloud requis.

---

## Prérequis

### 1. Activer l'Open API sur la batterie

Dans l'app **Marstek Venus Monitor** (Windows / Android / iOS) :

```
Paramètres → Open API → Activer
Port : 30000 (défaut, recommandé)
```

> ⚠️ Firmware minimum recommandé : **V153+**  
> Sur V147, `ES.GetStatus` peut timeout sur certains appareils — l'intégration fait un fallback automatique sur `ES.GetMode`.

### 2. IP statique recommandée

Réservez un bail DHCP fixe pour la batterie sur votre routeur (MikroTik, UniFi…).

---

## Installation

### Via HACS (recommandé)

1. HACS → Intégrations → ⋮ → **Dépôts personnalisés**
2. Ajouter l'URL de ce dépôt, type : **Intégration**
3. Installer → Redémarrer Home Assistant

### Manuellement

```bash
# Copier le dossier dans votre config HA
cp -r custom_components/marstek_venus_e  /config/custom_components/
```

Redémarrer Home Assistant.

---

## Configuration

**Paramètres → Appareils & Services → + Ajouter une intégration → "Marstek Venus E"**

L'assistant détecte automatiquement les batteries sur le réseau local (broadcast UDP).  
Si la découverte échoue : choisir "Entrer l'IP manuellement".

---

## Entités créées

### Capteurs (`sensor`)

| Entité | Description | Unité |
|--------|-------------|-------|
| `battery_soc` | Niveau de charge | % |
| `battery_capacity` | Capacité restante | Wh |
| `battery_rated_capacity` | Capacité nominale | Wh |
| `battery_temperature` | Température batterie | °C |
| `pv_power` | Puissance solaire | W |
| `grid_power` | Puissance réseau (+ = export) | W |
| `offgrid_power` | Puissance hors-réseau | W |
| `battery_power` | Puissance batterie | W |
| `phase_a/b/c_power` | Puissance par phase CT | W |
| `total_ct_power` | Puissance CT totale | W |
| `total_pv_energy` | Énergie solaire totale | kWh |
| `total_grid_export` | Export réseau total | kWh |
| `total_grid_import` | Import réseau total | kWh |
| `total_load_energy` | Consommation totale | kWh |
| `wifi_signal` | Signal WiFi | dBm |
| `operating_mode` | Mode de fonctionnement | texte |

### Capteurs binaires (`binary_sensor`)

| Entité | Description |
|--------|-------------|
| `charging` | Batterie en charge |
| `discharging` | Batterie en décharge |
| `ct_connected` | Compteur CT connecté |

### Contrôles

| Type | Entité | Description |
|------|--------|-------------|
| `select` | `operating_mode` | Choisir Auto / AI / Manual / Passive |
| `number` | `passive_power_target` | Puissance passive (W) |
| `number` | `passive_duration` | Durée mode passif (s) |
| `button` | `mode_auto` | Basculer en mode Auto |
| `button` | `mode_ai` | Basculer en mode AI |
| `button` | `force_refresh` | Actualiser maintenant |

---

## Services

### `marstek_venus_e.set_passive_mode`

Passer en mode passif avec une puissance cible.

```yaml
service: marstek_venus_e.set_passive_mode
data:
  power: -2000      # négatif = charge à 2000 W depuis le réseau
  cd_time: 14400    # durée en secondes (0 = indéfini)
```

### `marstek_venus_e.set_manual_schedule`

Configurer un slot de planification (mode Manuel).

```yaml
service: marstek_venus_e.set_manual_schedule
data:
  time_num: 0          # slot 0 à 9
  start_time: "08:00"
  end_time: "16:00"
  week_set: 31         # 31 = lundi-vendredi (bitmask)
  power: -1500         # charge à 1500 W
  enable: true
```

**Bitmask `week_set`** : bit0=Lun, bit1=Mar, bit2=Mer, bit3=Jeu, bit4=Ven, bit5=Sam, bit6=Dim  
→ 127 = tous les jours, 31 = semaine, 96 = week-end

### `marstek_venus_e.clear_schedules`

Désactiver tous les 10 slots de planification.

### `marstek_venus_e.force_refresh`

Forcer une actualisation immédiate hors intervalle normal.

---

## Exemples d'automatisations

### Charger la nuit (heures creuses)

```yaml
automation:
  - alias: "Marstek — Charge heures creuses"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: marstek_venus_e.set_passive_mode
        data:
          power: -2500     # charge à 2500 W
          cd_time: 28800   # pendant 8 heures
```

### Décharger pendant les heures de pointe

```yaml
automation:
  - alias: "Marstek — Décharge heures de pointe"
    trigger:
      - platform: time
        at: "17:00:00"
    action:
      - service: marstek_venus_e.set_passive_mode
        data:
          power: 2000    # injecte 2000 W au réseau
          cd_time: 7200  # pendant 2 heures
```

### Revenir en mode Auto après

```yaml
automation:
  - alias: "Marstek — Retour Auto après heures de pointe"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.marstek_operating_mode
        data:
          option: "Auto"
```

---

## Carte Lovelace suggérée

```yaml
type: entities
title: Marstek Venus E 3.0
entities:
  - entity: sensor.marstek_battery_soc
    name: Niveau batterie
  - entity: sensor.marstek_pv_power
    name: Production solaire
  - entity: sensor.marstek_grid_power
    name: Réseau
  - entity: sensor.marstek_battery_power
    name: Puissance batterie
  - entity: sensor.marstek_operating_mode
    name: Mode
  - entity: select.marstek_operating_mode
    name: Changer de mode
  - entity: number.marstek_passive_power_target
    name: Puissance passive
  - entity: binary_sensor.marstek_charging
    name: En charge
  - entity: binary_sensor.marstek_discharging
    name: En décharge
```

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Pas de réponse UDP | Vérifier que l'Open API est activée dans l'app Marstek |
| `ES.GetStatus` timeout | Normal sur V147 — l'intégration bascule automatiquement sur `ES.GetMode` |
| Port 30000 déjà utilisé | L'intégration tente `reuse_port` puis bascule sur un port éphémère |
| Perte de connexion après mise à jour firmware | Réactiver l'Open API dans l'app |
| Valeurs à None | Attendre le prochain cycle de polling (intervalle par défaut : 60 s) |

Pour activer les logs détaillés :
```yaml
# configuration.yaml
logger:
  logs:
    custom_components.marstek_venus_e: debug
```

---

## Protocole (référence)

- **Transport** : UDP uniquement (TCP refusé par le firmware)
- **Port** : 30000 par défaut (source = destination — exigence Marstek)
- **Format** : JSON-RPC 2.0
- **Découverte** : broadcast `Marstek.GetDevice` → `255.255.255.255:30000`
- **Intervalle poll minimum** : 60 s (en dessous, le device peut devenir instable)

---

*Projet non affilié à Marstek. Utilisation à vos risques conformément à la licence API Marstek.*
