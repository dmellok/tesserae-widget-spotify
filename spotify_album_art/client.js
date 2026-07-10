// spotify_album_art, Spectra full-bleed image. Just the current
// album art at full size; a tiny bottom-overlay surfaces the track
// + artist when something is playing, fades to a "Not playing"
// placeholder when idle.

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const opts = ctx?.cell?.options || {};
  const dimWhenPaused = opts.dim_when_paused !== false; // default true
  const showInfo = opts.show_track_info !== false;      // default true
  // ``scale`` flips the img between object-fit:cover (default, fills
  // the cell, crops to aspect) and contain (letterbox, keeps the
  // album art square). Anything else falls back to cover.
  const fit = opts.scale === "contain" ? "contain" : "cover";
  const css = `<link rel="stylesheet" href="/static/style/spectra-widgets.css">`;

  if (data.error) {
    shadow.innerHTML = `
      ${css}
      <div class="w" data-widget="spotify_album_art">
        <div class="w-title"><i class="ph-bold ph-warning-circle"></i><h3>Spotify</h3></div>
        <div class="w-body"><p class="u-muted">${escapeHtml(data.error)}</p></div>
      </div>`;
    return;
  }

  if (data.idle || !data.album_art) {
    shadow.innerHTML = `
      ${css}
      <div class="w is-bleed" data-widget="spotify_album_art">
        <div class="bleed-empty">Not playing.</div>
      </div>`;
    return;
  }

  const subBits = [data.track, data.artist].filter(Boolean);
  const dimmed = dimWhenPaused && data.is_playing === false;
  const imgStyle = [
    `object-fit:${fit}`,
    fit === "contain" ? "background:var(--surface-sunken)" : "",
    dimmed ? "opacity:0.5" : "",
  ].filter(Boolean).join(";");

  // Fragments (issue #60): the Panels canvas can place just one part of the
  // widget. ``ctx.fragment`` selects which; "full" (default) is the whole
  // card. "art" is the bleed image alone; "info" is the track + artist text.
  const frag = ctx?.fragment || "full";
  if (frag === "art") {
    shadow.innerHTML = `
      ${css}
      <div class="w is-bleed" data-widget="spotify_album_art">
        <img src="${escapeHtml(data.album_art)}" alt="${escapeHtml(data.track || "")}" style="${imgStyle}">
      </div>`;
    return;
  }
  if (frag === "info") {
    shadow.innerHTML = `
      ${css}
      <style>
        .saa-info { display: flex; flex-direction: column; justify-content: center; height: 100%; gap: var(--space-1); padding: var(--space-3); }
        .saa-info .t { font-size: clamp(1em, 9cqmin, 2.4em); font-weight: var(--fw-black); line-height: var(--lh-tight); overflow: hidden; text-overflow: ellipsis; }
        .saa-info .a { font-size: clamp(.8em, 6cqmin, 1.4em); color: var(--text-secondary); font-weight: var(--fw-semi); overflow: hidden; text-overflow: ellipsis; }
      </style>
      <div class="w" data-widget="spotify_album_art"><div class="w-body saa-info">
        ${data.track ? `<span class="t">${escapeHtml(data.track)}</span>` : ""}
        ${data.artist ? `<span class="a">${escapeHtml(data.artist)}</span>` : ""}
      </div></div>`;
    return;
  }

  shadow.innerHTML = `
    ${css}
    <div class="w is-bleed" data-widget="spotify_album_art">
      <img src="${escapeHtml(data.album_art)}" alt="${escapeHtml(data.track || "")}" style="${imgStyle}">
      ${showInfo && subBits.length
        ? `<div class="img-overlay">
            ${data.track ? `<span class="title">${escapeHtml(data.track)}</span>` : ""}
            ${data.artist ? `<span class="sub">${escapeHtml(data.artist)}</span>` : ""}
          </div>`
        : ""}
    </div>`;
}
