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
  const sourcePagePane = document.getElementById("source-evidence-page-pane");
  const sourcePageImage = document.getElementById("source-evidence-page-image");
  const sourcePageLabel = document.getElementById("source-evidence-page-label");
  const sourceOpenTab = document.getElementById("source-evidence-jump");
  const editorError = document.getElementById("field-editor-error");
  const reprocessButton = document.getElementById("field-editor-reprocess");
  const revertButton = document.getElementById("field-editor-revert");
  const learnButton = document.getElementById("field-editor-learn");
  const resizeHandle = document.getElementById("assistant-resize-handle");
  const processForm = document.getElementById("process-form");
  const progressPanel = document.getElementById("processing-progress");
  const progressTitle = document.getElementById("processing-progress-title");
  const progressBar = document.getElementById("processing-progress-bar");
  const progressEvents = document.getElementById("processing-progress-events");

  function processingPercent(event, status) {
    if (status === "mapped") return 100;
    if (status === "mapping_failed" || status === "failed") return 100;
    if (!event) return status === "processing" ? 8 : 0;

    const payload = event.payload || {};
    if (event.type === "profile_matched" || event.type === "profile_not_matched") return 5;
    if (event.type === "mapping_started") return 8;
    if (event.type === "mapping_progress") {
      if (payload.stage === "mapping") {
        const total = Math.max(1, Number(payload.total) || 1);
        const current = Math.max(0, Math.min(total, Number(payload.current) || 0));
        return Math.round(10 + (current / total) * 65);
      }
      if (payload.stage === "merging") return 82;
      if (payload.stage === "validating") return 92;
    }
    if (event.type === "mapping_completed") return 100;
    if (event.type === "mapping_failed") return 100;
    return 8;
  }

  function renderProcessingStatus(payload) {
    if (!progressPanel) return;
    const events = payload.events || [];
    const latest = events.length ? events[events.length - 1] : null;
    const percent = processingPercent(latest, payload.status);

    progressPanel.hidden = false;
    if (progressBar) progressBar.style.width = Math.max(3, percent) + "%";

    if (progressTitle) {
      if (payload.status === "mapped") {
        progressTitle.textContent = "Virtual SSD mapping complete";
      } else if (payload.status === "mapping_failed" || payload.status === "failed") {
        progressTitle.textContent = payload.error || "Mapping failed";
      } else if (latest?.summary) {
        progressTitle.textContent = latest.summary;
      } else {
        progressTitle.textContent = "Preparing local document mapper…";
      }
    }

    if (progressEvents) {
      progressEvents.innerHTML = "";
      events.slice(-5).forEach((item) => {
        const row = document.createElement("div");
        row.className = "processing-event " + (item.type === "mapping_failed" ? "failed" : "");
        const marker = document.createElement("span");
        marker.className = "processing-event-marker";
        marker.textContent = item.type === "mapping_failed" ? "!" : "✓";
        const label = document.createElement("span");
        label.textContent = item.summary || item.type.replaceAll("_", " ");
        row.append(marker, label);
        progressEvents.appendChild(row);
      });
    }
  }

  processForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = processForm.querySelector('button[type="submit"]');
    const original = submit?.textContent || "Run Local Mapper";
    if (submit) {
      submit.disabled = true;
      submit.textContent = "Processing…";
    }
    if (progressPanel) progressPanel.hidden = false;
    if (progressBar) progressBar.style.width = "4%";
    if (progressTitle) progressTitle.textContent = "Starting local document mapper…";
    if (progressEvents) progressEvents.innerHTML = "";

    let polling = true;
    const poll = async () => {
      while (polling) {
        try {
          const response = await fetch("/jobs/" + context.id + "/processing-status", {
            cache: "no-store"
          });
          if (response.ok) {
            renderProcessingStatus(await response.json());
          }
        } catch (_) {
          // Processing request remains authoritative; a missed poll is harmless.
        }
        await new Promise((resolve) => window.setTimeout(resolve, 900));
      }
    };
    const pollPromise = poll();

    try {
      const response = await fetch(processForm.action, {
        method: "POST",
        headers: {"X-PackBridge-Async": "1"},
        body: new FormData(processForm)
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Local document mapping failed.");
      }
      renderProcessingStatus({
        status: "mapped",
        events: [{
          type: "mapping_completed",
          summary: payload.message || "Virtual SSD mapping complete",
          payload: {}
        }]
      });
      window.setTimeout(() => {
        window.location.href = payload.redirect || ("/jobs/" + context.id);
      }, 350);
    } catch (error) {
      if (progressTitle) progressTitle.textContent = error.message || String(error);
      progressPanel?.classList.add("processing-failed");
      if (submit) {
        submit.disabled = false;
        submit.textContent = original;
      }
    } finally {
      polling = false;
      await pollPromise;
    }
  });

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
    editorReason.value = button.dataset.reason || "";
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
    if (learnButton) {
      learnButton.hidden = !(
        button.dataset.modified === "1" &&
        context.profileKnowledgePath
      );
      learnButton.dataset.path = button.dataset.path || "";
      learnButton.dataset.note = button.dataset.reason || "";
    }
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

    const rendered = matches.find((match) => match.page_image_url);
    if (sourcePagePane && sourcePageImage && sourcePageLabel) {
      if (rendered) {
        sourcePagePane.hidden = false;
        sourcePageImage.src = rendered.page_image_url;
        sourcePageImage.alt =
          (rendered.document || "Source PDF") +
          " — page " +
          String(rendered.page_number || "");
        sourcePageLabel.textContent =
          (rendered.document || "Source PDF") +
          " · Page " +
          String(rendered.page_number || "");
      } else {
        sourcePagePane.hidden = true;
        sourcePageImage.removeAttribute("src");
        sourcePageLabel.textContent = "";
      }
    }

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

  reprocessButton?.addEventListener("click", async () => {
    clearError();
    const path = editorPath.value || "";
    if (!path) return;

    reprocessButton.disabled = true;
    const original = reprocessButton.textContent;
    reprocessButton.textContent = "Reprocessing…";

    async function run(discardEdit) {
      return postJson("/jobs/" + context.id + "/field/reprocess", {
        path: path,
        discard_edit: discardEdit
      });
    }

    try {
      await run(false);
      editor.close();
      window.location.reload();
    } catch (error) {
      if (
        error.message.includes("manual working-data change") &&
        window.confirm("This field has a manual edit. Discard that edit and reprocess the field from its retained source evidence?")
      ) {
        try {
          await run(true);
          editor.close();
          window.location.reload();
          return;
        } catch (retryError) {
          showError(retryError.message);
        }
      } else {
        showError(error.message);
      }
    } finally {
      reprocessButton.disabled = false;
      reprocessButton.textContent = original;
    }
  });

  learnButton?.addEventListener("click", async () => {
    const fieldPath = learnButton.dataset.path || editorPath.value || "";
    if (!fieldPath) return;

    const note = window.prompt(
      "What should PackBridge learn from this correction? This creates a reviewable Knowledge proposal only.",
      learnButton.dataset.note || editorReason.value || ""
    );
    if (note === null) return;

    learnButton.disabled = true;
    const original = learnButton.textContent;
    learnButton.textContent = "Creating proposal…";
    try {
      const payload = await postJson(
        "/jobs/" + context.id + "/learning/propose-field",
        {
          path: fieldPath,
          note: note
        }
      );
      editor.close();
      if (window.confirm("Knowledge proposal created. Open Learning to review the diff?")) {
        window.location.href = payload.learning_url;
      } else {
        window.location.reload();
      }
    } catch (error) {
      showError(error.message);
    } finally {
      learnButton.disabled = false;
      learnButton.textContent = original;
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

  document.querySelectorAll("[data-reprocess-package]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.dataset.packageIndex);
      if (!Number.isInteger(index)) return;
      button.disabled = true;
      const original = button.textContent;
      button.textContent = "Reprocessing…";

      async function run(discardEdits) {
        return postJson(
          "/jobs/" + context.id + "/packages/" + index + "/reprocess",
          {discard_edits: discardEdits}
        );
      }

      try {
        await run(false);
        window.location.reload();
      } catch (error) {
        if (
          error.message.includes("manual working-data changes") &&
          window.confirm("This case contains manual edits. Discard those edits and remap the case from retained source evidence?")
        ) {
          try {
            await run(true);
            window.location.reload();
            return;
          } catch (retryError) {
            window.alert(retryError.message);
          }
        } else {
          window.alert(error.message);
        }
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
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

  document.querySelectorAll("[data-ack-warning]").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = button.dataset.code || "warning";
      const reason = window.prompt(
        "Acknowledge " + code + ". Add a reason or verification note:",
        ""
      );
      if (reason === null) return;
      button.disabled = true;
      try {
        await postJson("/jobs/" + context.id + "/issues/acknowledge", {
          fingerprint: button.dataset.fingerprint,
          reason: reason
        });
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-reopen-warning]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("Reopen this acknowledged warning?")) return;
      button.disabled = true;
      try {
        await postJson("/jobs/" + context.id + "/issues/reopen", {
          fingerprint: button.dataset.fingerprint
        });
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });
})();