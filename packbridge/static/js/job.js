(() => {
  const context = window.PACKBRIDGE_JOB;
  const shell = document.getElementById("job-shell");
  if (!context || !shell) return;

  const editor = document.getElementById("field-editor");
  const editorForm = document.getElementById("field-editor-form");
  const editorTitle = document.getElementById("field-editor-title");
  const editorPath = document.getElementById("field-editor-path");
  const editorValue = document.getElementById("field-editor-value");
  const editorUnit = document.getElementById("field-editor-unit");
  const editorReason = document.getElementById("field-editor-reason");
  const editorSource = document.getElementById("field-editor-source");
  const editorLocator = document.getElementById("field-editor-locator");
  const editorRaw = document.getElementById("field-editor-raw");
  const sourceJump = document.getElementById("field-editor-source-jump");
  const sourceDialog = document.getElementById("source-evidence-dialog");
  const sourceTitle = document.getElementById("source-evidence-title");
  const sourceSubtitle = document.getElementById("source-evidence-subtitle");
  const sourceResults = document.getElementById("source-evidence-results");
  const sourceOpenTab = document.getElementById("source-evidence-jump");
  const editorError = document.getElementById("field-editor-error");
  const revertButton = document.getElementById("field-editor-revert");
  const resizeHandle = document.getElementById("assistant-resize-handle");

  const savedWidth = Number(window.localStorage.getItem("packbridge-assistant-width"));
  if (savedWidth >= 300 && savedWidth <= 700 && window.innerWidth > 1050) {
    shell.style.setProperty("--assistant-width", savedWidth + "px");
  }

  resizeHandle?.addEventListener("pointerdown", (event) => {
    if (window.innerWidth <= 1050) return;
    event.preventDefault();
    resizeHandle.setPointerCapture(event.pointerId);
    document.body.classList.add("resizing-assistant");

    const move = (moveEvent) => {
      const width = Math.min(700, Math.max(300, window.innerWidth - moveEvent.clientX));
      shell.style.setProperty("--assistant-width", width + "px");
      window.localStorage.setItem("packbridge-assistant-width", String(width));
    };

    const finish = () => {
      document.body.classList.remove("resizing-assistant");
      resizeHandle.removeEventListener("pointermove", move);
      resizeHandle.removeEventListener("pointerup", finish);
      resizeHandle.removeEventListener("pointercancel", finish);
    };

    resizeHandle.addEventListener("pointermove", move);
    resizeHandle.addEventListener("pointerup", finish);
    resizeHandle.addEventListener("pointercancel", finish);
  });

  function showError(message) {
    editorError.textContent = message;
    editorError.hidden = false;
  }

  function clearError() {
    editorError.textContent = "";
    editorError.hidden = true;
  }

  function openEditor(button) {
    clearError();
    editorTitle.textContent = button.dataset.label || "Edit field";
    editorPath.value = button.dataset.path || "";
    editorValue.value = button.dataset.current || "";
    editorUnit.value = button.dataset.unit || "";
    editorReason.value = "";
    const source = button.dataset.source || "";
    const sourceUnit = button.dataset.sourceUnit || "";
    editorSource.textContent = source ? source + (sourceUnit ? " " + sourceUnit : "") : "—";
    const locator = button.dataset.locator || "";
    const raw = button.dataset.raw || "";
    editorLocator.textContent = locator ? "Source: " + locator : "No source locator recorded";
    editorRaw.textContent = raw;
    editorRaw.hidden = !raw;
    sourceJump.hidden = !locator;
    sourceJump.dataset.locator = locator;
    if (typeof editor.showModal === "function") {
      editor.showModal();
      editorValue.focus();
      editorValue.select();
    }
  }

  document.querySelectorAll("[data-field-edit]").forEach((button) => {
    button.addEventListener("click", () => openEditor(button));
  });

  document.querySelectorAll("[data-close-editor]").forEach((button) => {
    button.addEventListener("click", () => editor.close());
  });

  function renderSourceEvidence(locator, matches) {
    sourceTitle.textContent = locator || "Source section";
    sourceSubtitle.textContent = matches.length
      ? matches.length + " retained source section" + (matches.length === 1 ? "" : "s") + " matched."
      : "No retained source section matched this locator.";
    sourceResults.innerHTML = "";

    matches.forEach((match) => {
      const article = document.createElement("article");
      article.className = "source-evidence-result";

      const header = document.createElement("div");
      header.className = "source-evidence-result-header";
      const label = document.createElement("strong");
      label.textContent = match.locator || locator;
      const documentName = document.createElement("span");
      documentName.textContent = match.document || "Source document";
      header.append(label, documentName);

      const pre = document.createElement("pre");
      pre.textContent = match.text || "";

      article.append(header, pre);
      sourceResults.appendChild(article);
    });
  }

  async function openSourceEvidence(locator) {
    if (!locator || !sourceDialog) return;
    sourceTitle.textContent = locator;
    sourceSubtitle.textContent = "Loading retained source evidence…";
    sourceResults.innerHTML = "";
    try {
      const response = await fetch(
        "/jobs/" + context.id + "/source-evidence?locator=" + encodeURIComponent(locator)
      );
      const payload = await response.json().catch(() => ({}));
      renderSourceEvidence(locator, payload.matches || []);
      sourceOpenTab.href = "#source";
      if (typeof sourceDialog.showModal === "function") {
        sourceDialog.showModal();
      }
    } catch (error) {
      renderSourceEvidence(locator, []);
      sourceSubtitle.textContent = "Source evidence could not be loaded: " + error;
      if (typeof sourceDialog.showModal === "function") {
        sourceDialog.showModal();
      }
    }
  }

  sourceJump?.addEventListener("click", async () => {
    const locator = sourceJump.dataset.locator || "";
    if (!locator) return;
    editor.close();
    await openSourceEvidence(locator);
  });

  document.querySelectorAll("[data-close-source-evidence]").forEach((button) => {
    button.addEventListener("click", () => sourceDialog?.close());
  });

  sourceOpenTab?.addEventListener("click", () => {
    sourceDialog?.close();
    const locator = sourceTitle.textContent || "";
    const target = Array.from(document.querySelectorAll("[data-source-locator]"))
      .find((node) => {
        const candidate = node.dataset.sourceLocator || "";
        return candidate === locator || candidate.startsWith(locator + ",") || locator.startsWith(candidate + ",");
      });
    if (target) {
      window.setTimeout(() => {
        target.scrollIntoView({behavior: "smooth", block: "center"});
        target.classList.add("source-highlight");
        window.setTimeout(() => target.classList.remove("source-highlight"), 2200);
      }, 80);
    }
  });

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload || {})
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "The request failed.");
    }
    return data;
  }

  editorForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    const submit = editorForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    const original = submit.textContent;
    submit.textContent = "Saving…";
    try {
      await postJson("/jobs/" + context.id + "/field", {
        path: editorPath.value,
        value: editorValue.value,
        unit: editorUnit.value || null,
        reason: editorReason.value
      });
      editor.close();
      window.location.reload();
    } catch (error) {
      showError(error.message);
    } finally {
      submit.disabled = false;
      submit.textContent = original;
    }
  });

  revertButton?.addEventListener("click", async () => {
    clearError();
    revertButton.disabled = true;
    const original = revertButton.textContent;
    revertButton.textContent = "Reverting…";
    try {
      await postJson("/jobs/" + context.id + "/field/revert", {
        path: editorPath.value
      });
      editor.close();
      window.location.reload();
    } catch (error) {
      showError(error.message);
    } finally {
      revertButton.disabled = false;
      revertButton.textContent = original;
    }
  });

  document.querySelectorAll("[data-revert-package]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.dataset.packageIndex);
      if (!Number.isInteger(index)) return;
      if (!window.confirm("Revert every edited value in this case back to the mapped source values?")) return;
      button.disabled = true;
      try {
        await postJson("/jobs/" + context.id + "/packages/" + index + "/revert", {});
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-revert-job]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("Revert all edited values in this job back to their mapped source values?")) return;
      button.disabled = true;
      try {
        await postJson("/jobs/" + context.id + "/revert-all", {});
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });
})();