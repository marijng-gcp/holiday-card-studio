(() => {
  const state = {
    vibe: "Cozy",
    style: "cozy_gourmet",
    emoji: "🎅",
    selfieImage: null,
    sessionId: null,
    invocationId: null,
  };

  const $ = (id) => document.getElementById(id);

  async function initConfig() {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const data = await res.json();
        if (data.event_title) $("event-title").textContent = data.event_title;
      }
    } catch (_) {}
  }

  document.querySelectorAll(".vibe-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.vibe = btn.dataset.vibe;
      document.querySelectorAll(".vibe-btn").forEach((b) => {
        b.className = "vibe-btn rounded-xl border border-white/20 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-200";
      });
      btn.className = "vibe-btn rounded-xl border border-amber-400 bg-amber-400/20 px-3 py-2 text-xs font-semibold text-amber-100";
    });
  });

  document.querySelectorAll(".style-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.style = btn.dataset.style;
      document.querySelectorAll(".style-btn").forEach((b) => {
        b.className = "style-btn rounded-xl border border-white/20 bg-slate-900/60 px-2 py-2 text-xs font-semibold text-slate-200";
      });
      btn.className = "style-btn rounded-xl border border-amber-400 bg-amber-400/20 px-2 py-2 text-xs font-semibold text-amber-100";
    });
  });

  document.querySelectorAll(".emoji-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.emoji = btn.dataset.emoji;
      state.selfieImage = null;
      $("selfie-status").textContent = `Using ${state.emoji}`;
      document.querySelectorAll(".emoji-btn").forEach((b) => {
        b.className = "emoji-btn rounded-lg bg-white/10 px-2.5 py-1.5 text-lg";
      });
      btn.className = "emoji-btn rounded-lg bg-amber-400/25 px-2.5 py-1.5 text-lg";
    });
  });

  $("selfie-input").addEventListener("change", (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        state.selfieImage = img;
        $("selfie-status").textContent = "Selfie ready (local only)";
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });

  function showSection(name) {
    ["form-section", "loading-section", "confirm-section", "result-section"].forEach((id) => {
      $(id).classList.toggle("hidden", id !== name);
    });
  }

  function showError(msg) {
    const el = $("error-banner");
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = (text || "").split(/\s+/);
    let line = "";
    let curY = y;
    for (const word of words) {
      const testLine = line ? `${line} ${word}` : word;
      if (ctx.measureText(testLine).width > maxWidth && line) {
        ctx.fillText(line, x, curY);
        line = word;
        curY += lineHeight;
      } else {
        line = testLine;
      }
    }
    if (line) ctx.fillText(line, x, curY);
  }

  async function renderCard(payload) {
    const canvas = $("card-canvas");
    const ctx = canvas.getContext("2d");
    const W = 1080;
    const H = 1440;

    ctx.clearRect(0, 0, W, H);
    const bgImg = new Image();
    await new Promise((resolve) => {
      bgImg.onload = resolve;
      bgImg.onerror = resolve;
      bgImg.src = `data:${payload.background_mime_type};base64,${payload.background_image_base64}`;
    });
    ctx.drawImage(bgImg, 0, 0, W, H);

    // Subtle dark gradient at bottom for crisp typography
    const grad = ctx.createLinearGradient(0, 620, 0, H);
    grad.addColorStop(0, "rgba(15, 23, 42, 0.15)");
    grad.addColorStop(0.5, "rgba(15, 23, 42, 0.78)");
    grad.addColorStop(1, "rgba(15, 23, 42, 0.94)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 620, W, H - 620);

    // Gold trading card border
    ctx.strokeStyle = "#F6C453";
    ctx.lineWidth = 14;
    ctx.strokeRect(28, 28, W - 56, H - 56);

    // Circular ornament frame for local selfie or emoji
    const cx = W / 2;
    const cy = 360;
    const radius = 190;
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();

    if (state.selfieImage) {
      const img = state.selfieImage;
      const scale = Math.max((radius * 2) / img.width, (radius * 2) / img.height);
      const dw = img.width * scale;
      const dh = img.height * scale;
      ctx.drawImage(img, cx - dw / 2, cy - dh / 2, dw, dh);
    } else {
      ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
      ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);
      ctx.font = "180px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(state.emoji, cx, cy + 12);
    }
    ctx.restore();

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = 12;
    ctx.strokeStyle = "#F6C453";
    ctx.stroke();

    const copy = payload.card_copy || {
      holiday_title: "Festive Legend",
      superpower_2027: "2027 Superpower: Joy +99",
      greeting_text: "Wishing you a joyful holiday season and a bright 2027!",
    };

    ctx.textAlign = "center";
    ctx.fillStyle = "#FDE68A";
    ctx.font = "bold 56px sans-serif";
    ctx.fillText(copy.holiday_title, cx, 710);

    ctx.fillStyle = "#34D399";
    ctx.font = "bold 36px sans-serif";
    ctx.fillText(copy.superpower_2027, cx, 790);

    ctx.fillStyle = "#F8FAFC";
    ctx.font = "38px sans-serif";
    wrapText(ctx, copy.greeting_text, cx, 900, 880, 56);

    ctx.fillStyle = "#CBD5E1";
    ctx.font = "bold 28px sans-serif";
    ctx.fillText(payload.event_footer || "Season's Greetings!", cx, 1340);

    showSection("result-section");
  }

  async function handleResponse(data) {
    state.sessionId = data.session_id;
    if (data.status === "awaiting_confirmation") {
      state.invocationId = data.invocation_id;
      $("confirm-reason").textContent = data.confirmation_reason || "Review your copy before rendering.";
      $("preview-title").textContent = data.card_copy ? data.card_copy.holiday_title : "";
      $("preview-power").textContent = data.card_copy ? data.card_copy.superpower_2027 : "";
      $("edited-greeting").value = data.card_copy ? data.card_copy.greeting_text : "";
      showSection("confirm-section");
      return;
    }
    await renderCard(data);
  }

  $("generate-btn").addEventListener("click", async () => {
    $("error-banner").classList.add("hidden");
    const first_name = $("first_name").value.trim();
    const highlight_2026 = $("highlight_2026").value.trim();
    const wish_2027 = $("wish_2027").value.trim();
    if (!first_name || highlight_2026.length < 2 || wish_2027.length < 2) {
      showError("Please fill in your first name, 2026 highlight, and 2027 wish.");
      return;
    }

    showSection("loading-section");
    try {
      const res = await fetch("/api/generate-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_name,
          highlight_2026,
          wish_2027,
          vibe: state.vibe,
          style: state.style,
          session_id: state.sessionId,
          require_confirmation: $("require_confirmation").checked,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await handleResponse(await res.json());
    } catch (err) {
      showSection("form-section");
      showError(`Could not generate card: ${err.message}`);
    }
  });

  $("confirm-btn").addEventListener("click", async () => {
    showSection("loading-section");
    try {
      const res = await fetch("/api/confirm-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          invocation_id: state.invocationId,
          confirmed: true,
          edited_greeting: $("edited-greeting").value.trim(),
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await handleResponse(await res.json());
    } catch (err) {
      showSection("form-section");
      showError(`Confirmation failed: ${err.message}`);
    }
  });

  $("remix-btn").addEventListener("click", async () => {
    const instruction = $("remix-input").value.trim();
    if (instruction.length < 2 || !state.sessionId) return;
    showSection("loading-section");
    try {
      const res = await fetch("/api/remix-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          instruction,
          style: state.style,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      $("remix-input").value = "";
      await handleResponse(await res.json());
    } catch (err) {
      showSection("result-section");
      showError(`Remix failed: ${err.message}`);
    }
  });

  $("share-btn").addEventListener("click", async () => {
    const canvas = $("card-canvas");
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], "holiday-card-2026.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "My 2026 Holiday Card" });
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "holiday-card-2026.png";
        a.click();
        URL.revokeObjectURL(url);
      }
    }, "image/png");
  });

  $("reset-btn").addEventListener("click", () => {
    state.sessionId = null;
    state.invocationId = null;
    showSection("form-section");
  });

  initConfig();
})();
