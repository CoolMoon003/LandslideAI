// frontend/src/pages/ModelInsights.jsx

import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function ModelInsights() {
  const [metrics, setMetrics] = useState([]);
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [metricData, featureData] = await Promise.all([
          api.metrics(),
          api.features(),
        ]);

        setMetrics(Array.isArray(metricData) ? metricData : []);
        setFeatures(Array.isArray(featureData) ? featureData : []);
      } catch (error) {
        console.error("Model insights error:", error);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const formatPercent = (value) => {
    const num = Number(value);
    if (Number.isNaN(num)) return "—";
    return `${(num * 100).toFixed(1)}%`;
  };

  const getModelName = (model) => {
    const name =
      model.model ||
      model.Model ||
      model.model_name ||
      model.ModelName ||
      "";

    if (name.toLowerCase().includes("logistic")) {
      return "Logistic Regression";
    }

    if (name.toLowerCase().includes("random")) {
      return "Random Forest";
    }

    if (name.toLowerCase().includes("gradient")) {
      return "Gradient Boosting";
    }

    return name || "Model";
  };

  const selectedModel =
    metrics.find(
      (m) =>
        m.selected === true ||
        m.selected === "True" ||
        m.Selected === true ||
        m.Selected === "True"
    ) || metrics.find((m) => getModelName(m) === "Random Forest");

  const maxFeatureImportance =
    features.length > 0
      ? Math.max(...features.map((f) => Number(f.importance || f.value || 0)))
      : 1;

  if (loading) {
    return (
      <div className="page">
        <div className="card">
          <p>Loading model insights...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>Model Insights</h1>
          <p>
            Compare machine-learning models and understand the factors driving
            landslide susceptibility.
          </p>
        </div>

        {selectedModel && (
          <div className="risk-badge">
            <span>Selected Model</span>
            <strong>{getModelName(selectedModel)}</strong>
          </div>
        )}
      </div>

      {/* Model Comparison */}
      <section className="card">
        <div className="section-header">
          <div>
            <h2>Model Comparison</h2>
            <p>
              Models are evaluated using the same spatial train-test split and
              feature set.
            </p>
          </div>
        </div>

        <div className="model-table-wrapper">
          <table className="model-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Accuracy</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
              </tr>
            </thead>

            <tbody>
              {metrics.map((metric, index) => {
                const modelName = getModelName(metric);

                const isSelected =
                  metric.selected === true ||
                  metric.selected === "True" ||
                  metric.Selected === true ||
                  metric.Selected === "True" ||
                  modelName === "Random Forest";

                return (
                  <tr
                    key={`${modelName}-${index}`}
                    className={isSelected ? "selected-model-row" : ""}
                  >
                    <td>
                      <div className="model-name-cell">
                        <strong>{modelName}</strong>
                        {isSelected && (
                          <span className="selected-pill">BEST</span>
                        )}
                      </div>
                    </td>

                    <td>
                      {formatPercent(metric.accuracy ?? metric.Accuracy)}
                    </td>

                    <td>
                      {formatPercent(metric.precision ?? metric.Precision)}
                    </td>

                    <td>
                      {formatPercent(metric.recall ?? metric.Recall)}
                    </td>

                    <td className="strong-metric">
                      {formatPercent(metric.f1 ?? metric.F1 ?? metric.f1_score)}
                    </td>

                    <td>
                      {formatPercent(metric.roc_auc ?? metric["ROC-AUC"])}
                    </td>

                    <td className="strong-metric">
                      {formatPercent(metric.pr_auc ?? metric["PR-AUC"])}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Visual Comparison */}
      <section className="card">
        <div className="section-header">
          <div>
            <h2>Performance Comparison</h2>
            <p>Higher values indicate stronger model performance.</p>
          </div>
        </div>

        <div className="comparison-grid">
          {metrics.map((metric, index) => {
            const modelName = getModelName(metric);

            const f1 = Number(
              metric.f1 ?? metric.F1 ?? metric.f1_score ?? 0
            );

            const recall = Number(metric.recall ?? metric.Recall ?? 0);

            const prAuc = Number(
              metric.pr_auc ?? metric["PR-AUC"] ?? 0
            );

            const isSelected =
              modelName === "Random Forest" ||
              metric.selected === true ||
              metric.selected === "True";

            return (
              <div
                className={`model-performance-card ${
                  isSelected ? "best-performance" : ""
                }`}
                key={`${modelName}-chart-${index}`}
              >
                <div className="performance-card-header">
                  <strong>{modelName}</strong>
                  {isSelected && <span>★ BEST</span>}
                </div>

                <div className="metric-bar-item">
                  <div className="metric-bar-label">
                    <span>F1 Score</span>
                    <strong>{formatPercent(f1)}</strong>
                  </div>

                  <div className="metric-bar">
                    <div
                      className="metric-bar-fill"
                      style={{ width: `${f1 * 100}%` }}
                    />
                  </div>
                </div>

                <div className="metric-bar-item">
                  <div className="metric-bar-label">
                    <span>Recall</span>
                    <strong>{formatPercent(recall)}</strong>
                  </div>

                  <div className="metric-bar">
                    <div
                      className="metric-bar-fill"
                      style={{ width: `${recall * 100}%` }}
                    />
                  </div>
                </div>

                <div className="metric-bar-item">
                  <div className="metric-bar-label">
                    <span>PR-AUC</span>
                    <strong>{formatPercent(prAuc)}</strong>
                  </div>

                  <div className="metric-bar">
                    <div
                      className="metric-bar-fill"
                      style={{ width: `${prAuc * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Why Random Forest */}
      {selectedModel && (
        <section className="insight-highlight">
          <div className="insight-icon">★</div>

          <div>
            <h2>Why Random Forest?</h2>
            <p>
              Random Forest achieved the strongest overall balance for
              landslide-risk detection, with higher F1 Score, Recall and
              PR-AUC than the other tested models.
            </p>

            <div className="insight-stats">
              <div>
                <span>F1 Score</span>
                <strong>
                  {formatPercent(
                    selectedModel.f1 ??
                      selectedModel.F1 ??
                      selectedModel.f1_score
                  )}
                </strong>
              </div>

              <div>
                <span>Recall</span>
                <strong>
                  {formatPercent(
                    selectedModel.recall ?? selectedModel.Recall
                  )}
                </strong>
              </div>

              <div>
                <span>PR-AUC</span>
                <strong>
                  {formatPercent(
                    selectedModel.pr_auc ?? selectedModel["PR-AUC"]
                  )}
                </strong>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Feature Importance */}
      <section className="card">
        <div className="section-header">
          <div>
            <h2>Feature Importance</h2>
            <p>
              Relative contribution of terrain and land-cover features in the
              selected Random Forest model.
            </p>
          </div>
        </div>

        {features.length > 0 ? (
          <div className="feature-list">
            {features
              .sort(
                (a, b) =>
                  Number(b.importance ?? b.value ?? 0) -
                  Number(a.importance ?? a.value ?? 0)
              )
              .map((feature, index) => {
                const importance = Number(
                  feature.importance ?? feature.value ?? 0
                );

                const name =
                  feature.feature ||
                  feature.name ||
                  feature.Feature ||
                  `Feature ${index + 1}`;

                return (
                  <div className="feature-item" key={name}>
                    <div className="feature-header">
                      <span>{name}</span>
                      <strong>{formatPercent(importance)}</strong>
                    </div>

                    <div className="feature-track">
                      <div
                        className="feature-fill"
                        style={{
                          width: `${
                            maxFeatureImportance > 0
                              ? (importance / maxFeatureImportance) * 100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        ) : (
          <p className="empty-state">
            Feature importance data is currently unavailable.
          </p>
        )}
      </section>
    </div>
  );
}