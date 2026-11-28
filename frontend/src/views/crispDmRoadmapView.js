/**
 * Metodología: fases, hitos y avance.
 */

export function renderCrispDmRoadmapView(store) {
  const { roadmap } = store;
  const avance = roadmap.length
    ? Math.round(roadmap.reduce((sum, stage) => sum + stage.progress, 0) / roadmap.length)
    : 0;

  return `
    <div class="tabs-bar"><span class="chip chip-emerald">${roadmap.length} fases · ${avance}% de avance</span></div>

    <section class="grid-2">
      ${roadmap
        .map(
          stage => `
        <article class="card">
          <div class="card-header">
            <div class="card-title-group">
              <h3><span class="chip chip-blue mono">${stage.week}</span> ${stage.phase}</h3>
            </div>
            <span class="chip ${stage.progress === 100 ? 'chip-emerald' : 'chip-amber'}">${stage.progress}%</span>
          </div>

          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width:${stage.progress}%;"></div>
          </div>

          <ul style="padding-left:1.15rem; display:flex; flex-direction:column; gap:0.45rem; font-size:0.82rem; color:var(--text-secondary);">
            ${stage.deliverables.map(d => `<li>${d}</li>`).join('')}
          </ul>
        </article>
      `
        )
        .join('')}
    </section>
  `;
}
