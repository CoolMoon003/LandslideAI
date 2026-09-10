import React from "react";
import { Mountain, Layers, CloudRain, Activity, Building2, ArrowRight } from "lucide-react";

const STAGES = [
  {
    icon: Mountain,
    title: "Terrain",
    desc: "Elevation, slope, aspect and curvature describe the physical landscape.",
  },
  {
    icon: Layers,
    title: "Susceptibility",
    desc: "Terrain features create a static susceptibility surface via the Random Forest model.",
  },
  {
    icon: CloudRain,
    title: "Rainfall Trigger",
    desc: "IMD rainfall accumulation changes the scenario's trigger intensity.",
  },
  {
    icon: Activity,
    title: "Dynamic Risk",
    desc: "Susceptibility combined with the rainfall trigger for the selected date.",
  },
  {
    icon: Building2,
    title: "Impact",
    desc: "Infrastructure overlay identifies potentially exposed roads and settlements.",
  },
];

export default function RiskEngine() {
  return (
    <section className="card engine-card">
      <div className="card-head">
        <div>
          <span className="card-kicker">RISK ENGINE</span>
          <h3>How a scenario is built</h3>
        </div>
      </div>

      <div className="engine-pipeline">
        {STAGES.map((s, i) => (
          <React.Fragment key={s.title}>
            <div className="engine-stage">
              <div className="engine-number">{String(i + 1).padStart(2, "0")}</div>
              <b>{s.title}</b>
              <span>{s.desc}</span>
            </div>
            {i < STAGES.length - 1 && (
              <div className="engine-arrow">
                <ArrowRight size={16} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}
