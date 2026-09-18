(() => {
  const shell = document.getElementById("job-shell");
  if (!shell || !window.PACKBRIDGE_JOB) return;

  const panel = document.getElementById("assistant-panel");
  const collapse = document.getElementById("assistant-collapse");
  const reopen = document.getElementById("assistant-reopen");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-message");
  const history = document.getElementById("chat-history");

  function append(role, content) {
    const node = document.createElement("div");
    node.className = "chat-message " + role;
    node.textContent = content;
    history.appendChild(node);
    history.scrollTop = history.scrollHeight;
  }

  collapse?.addEventListener("click", () => {
    shell.classList.add("assistant-collapsed");
    reopen.hidden = false;
  });

  reopen?.addEventListener("click", () => {
    shell.classList.remove("assistant-collapsed");
    reopen.hidden = true;
  });

  async function loadHistory() {
    try {
      const response = await fetch("/jobs/" + window.PACKBRIDGE_JOB.id + "/chat/history");
      if (!response.ok) return;
      const payload = await response.json();
      if (!payload.messages?.length) return;
      history.innerHTML = "";
      payload.messages.forEach((message) => append(message.role, message.content));
    } catch (_) {
      // Initial chat history is optional; keep the welcome message on failure.
    }
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    append("user", message);
    input.value = "";
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const original = button.textContent;
    button.textContent = "Working…";

    try {
      const response = await fetch("/jobs/" + window.PACKBRIDGE_JOB.id + "/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          message,
          context: {
            selected_case: window.PACKBRIDGE_JOB.selectedCase || null
          }
        })
      });
      const payload = await response.json();
      append("assistant", payload.message || payload.error || "No response.");
    } catch (error) {
      append("assistant", "The local assistant request failed: " + error);
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  });

  loadHistory();
})();
