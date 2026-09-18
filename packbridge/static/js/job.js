(() => {
  const context = window.PACKBRIDGE_JOB;
  if (!context) return;

  const editor = document.getElementById("field-editor");
  const editorForm = document.getElementById("field-editor-form");
  const editorTitle = document.getElementById("field-editor-title");
  const editorPath = document.getElementById("field-editor-path");
  const editorValue = document.getElementById("field-editor-value");
  const editorUnit = document.getElementById("field-editor-unit");
  const editorReason = document.getElementById("field-editor-reason");
  const editorSource = document.getElementById("field-editor-source");
  const editorLocator = document.getElementById("field-editor-locator");
  const editorError = document.getElementById("field-editor-error");
  const revertButton = document.getElementById("field-editor-revert");

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
    editorLocator.textContent = button.dataset.locator ? "Source: " + button.dataset.locator : "No source locator recorded";
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