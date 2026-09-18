(() => {
  const shell = document.getElementById("job-shell");
  if (!shell || !window.PACKBRIDGE_JOB) return;

  const collapse = document.getElementById("assistant-collapse");
  const reopen = document.getElementById("assistant-reopen");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-message");
  const history = document.getElementById("chat-history");

  async function postJson(url) {
    const response = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: "{}"
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "The request failed.");
    return payload;
  }

  function renderProposal(proposal) {
    if (!proposal?.changes?.length) return null;

    const card = document.createElement("div");
    card.className = "assistant-proposal";
    card.dataset.proposalId = proposal.id;

    const heading = document.createElement("div");
    heading.className = "assistant-proposal-heading";
    const title = document.createElement("strong");
    title.textContent = "Proposed working-data change";
    const status = document.createElement("span");
    status.className = "assistant-proposal-status status-" + proposal.status;
    status.textContent = proposal.status;
    heading.append(title, status);
    card.appendChild(heading);

    const list = document.createElement("div");
    list.className = "assistant-proposal-list";
    proposal.changes.forEach((change) => {
      const row = document.createElement("div");
      row.className = "assistant-proposal-change";

      const path = document.createElement("code");
      path.textContent = change.path;

      const values = document.createElement("div");
      values.className = "assistant-proposal-values";
      const beforeValue = change.before?.value ?? "blank";
      const afterValue = change.value ?? "blank";
      values.textContent =
        String(beforeValue) + " → " + String(afterValue) +
        (change.unit ? " " + change.unit : "");

      const reason = document.createElement("small");
      reason.textContent = change.reason || "";

      row.append(path, values, reason);
      list.appendChild(row);
    });
    card.appendChild(list);

    if (proposal.status === "pending") {
      const actions = document.createElement("div");
      actions.className = "assistant-proposal-actions";

      const reject = document.createElement("button");
      reject.type = "button";
      reject.className = "btn btn-secondary";
      reject.textContent = "Cancel";

      const apply = document.createElement("button");
      apply.type = "button";
      apply.className = "btn btn-primary";
      apply.textContent = "Apply";

      reject.addEventListener("click", async () => {
        reject.disabled = true;
        apply.disabled = true;
        try {
          const payload = await postJson(
            "/jobs/" + window.PACKBRIDGE_JOB.id + "/proposals/" + proposal.id + "/reject"
          );
          status.textContent = payload.proposal?.status || "rejected";
          status.className = "assistant-proposal-status status-rejected";
          actions.remove();
        } catch (error) {
          reject.disabled = false;
          apply.disabled = false;
          window.alert(error.message);
        }
      });

      apply.addEventListener("click", async () => {
        reject.disabled = true;
        apply.disabled = true;
        apply.textContent = "Applying…";
        try {
          await postJson(
            "/jobs/" + window.PACKBRIDGE_JOB.id + "/proposals/" + proposal.id + "/apply"
          );
          status.textContent = "applied";
          status.className = "assistant-proposal-status status-applied";
          window.setTimeout(() => window.location.reload(), 250);
        } catch (error) {
          reject.disabled = false;
          apply.disabled = false;
          apply.textContent = "Apply";
          window.alert(error.message);
        }
      });

      actions.append(reject, apply);
      card.appendChild(actions);
    }

    return card;
  }

  function append(role, content, proposal = null) {
    const wrapper = document.createElement("div");
    wrapper.className = "chat-entry " + role;

    const node = document.createElement("div");
    node.className = "chat-message " + role;
    node.textContent = content;
    wrapper.appendChild(node);

    const proposalCard = renderProposal(proposal);
    if (proposalCard) wrapper.appendChild(proposalCard);

    history.appendChild(wrapper);
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
      payload.messages.forEach((message) =>
        append(message.role, message.content, message.proposal)
      );
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
      append(
        "assistant",
        payload.message || payload.error || "No response.",
        payload.proposal || null
      );
    } catch (error) {
      append("assistant", "The local assistant request failed: " + error);
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  });

  loadHistory();
})();
